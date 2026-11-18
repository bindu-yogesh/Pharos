from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2 import WKTElement
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import IncidentHistory, Report, ReportVote, User
from ..schemas.admin import (
    AdminStatsResponse,
    IncidentUpdateRequest,
    UserBlockRequest,
)
from ..security.deps import require_admin
from .reports import is_suspicious_report

router = APIRouter(prefix="/admin", tags=["Admin"])

DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.put("/users/{user_id}/block")
def set_user_block_status(
    user_id: int,
    payload: UserBlockRequest,
    db: DbSession,
    admin: AdminUser,
):
    if user_id == admin.id and payload.is_blocked:
        raise HTTPException(
            status_code=400,
            detail="Admins cannot block or unblock their own account",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_blocked = payload.is_blocked
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "is_blocked": user.is_blocked,
    }


@router.get("/reports/suspicious")
def get_suspicious_reports(
    db: DbSession,
    admin: AdminUser,
):
    reports = db.scalars(
        select(Report)
        .options(joinedload(Report.user))
        .order_by(Report.created_at.desc(), Report.id.desc())
    ).unique().all()

    results = []

    for report in reports:
        if not is_suspicious_report(db, report):
            continue

        vote_rows = db.execute(
            select(ReportVote.vote, func.count(ReportVote.id))
            .where(ReportVote.report_id == report.id)
            .group_by(ReportVote.vote)
        ).all()

        vote_counts = {vote: count for vote, count in vote_rows}

        latitude = None
        longitude = None

        if report.geom is not None:
            latitude, longitude = db.execute(
                select(
                    func.ST_Y(Report.geom),
                    func.ST_X(Report.geom),
                ).where(Report.id == report.id)
            ).one()

        results.append(
            {
                "id": report.id,
                "user_id": report.user_id,
                "author": report.user.name if report.user else None,
                "type": report.type,
                "severity": report.severity,
                "description": report.description,
                "status": report.status,
                "created_at": report.created_at,
                "expires_at": report.expires_at,
                "latitude": latitude,
                "longitude": longitude,
                "confirm_votes": vote_counts.get("confirm", 0),
                "clear_votes": vote_counts.get("clear", 0),
            }
        )

    return results


@router.delete("/reports/{report_id}")
def reject_report(
    report_id: int,
    db: DbSession,
    admin: AdminUser,
):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = "rejected"
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "status": report.status,
        "message": "Report rejected successfully",
    }


@router.put("/incidents/{incident_id}")
def update_incident(
    incident_id: int,
    payload: IncidentUpdateRequest,
    db: DbSession,
    admin: AdminUser,
):
    incident = db.get(IncidentHistory, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    changes = payload.model_dump(exclude_unset=True)

    latitude = changes.pop("latitude", None)
    longitude = changes.pop("longitude", None)

    required_fields = {
        "type",
        "incident_date",
        "location_name",
        "source",
    }

    for field in required_fields:
        if field in changes and changes[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    if latitude is not None and longitude is not None:
        changes["geom"] = WKTElement(
            f"POINT({longitude} {latitude})",
            srid=4326,
        )

    for field, value in changes.items():
        setattr(incident, field, value)

    db.commit()
    db.refresh(incident)

    latitude = None
    longitude = None

    if incident.geom is not None:
        latitude, longitude = db.execute(
            select(
                func.ST_Y(IncidentHistory.geom),
                func.ST_X(IncidentHistory.geom),
            ).where(IncidentHistory.id == incident.id)
        ).one()

    return {
        "id": incident.id,
        "type": incident.type,
        "incident_date": incident.incident_date,
        "location_name": incident.location_name,
        "source": incident.source,
        "notes": incident.notes,
        "latitude": latitude,
        "longitude": longitude,
    }


@router.get("/hazards")
def get_active_hazards(
    db: DbSession,
    admin: AdminUser,
):
    now = datetime.now(timezone.utc)

    rows = db.execute(
        select(
            Report.id,
            Report.user_id,
            Report.type,
            Report.severity,
            Report.description,
            Report.status,
            Report.created_at,
            Report.expires_at,
            func.ST_Y(Report.geom).label("latitude"),
            func.ST_X(Report.geom).label("longitude"),
        )
        .where(
            Report.status == "active",
            Report.geom.is_not(None),
            or_(
                Report.expires_at.is_(None),
                Report.expires_at > now,
            ),
        )
        .order_by(Report.created_at.desc())
    ).all()

    return [dict(row._mapping) for row in rows]


@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(
    db: DbSession,
    admin: AdminUser,
):
    now = datetime.now(timezone.utc)

    total_users = db.scalar(
        select(func.count(User.id))
    ) or 0

    blocked_users = db.scalar(
        select(func.count(User.id)).where(User.is_blocked.is_(True))
    ) or 0

    total_reports = db.scalar(
        select(func.count(Report.id))
    ) or 0

    active_reports = db.scalar(
        select(func.count(Report.id)).where(
            Report.status == "active",
            or_(
                Report.expires_at.is_(None),
                Report.expires_at > now,
            ),
        )
    ) or 0

    # Active hazards must have coordinates, matching GET /admin/hazards.
    active_hazards = db.scalar(
        select(func.count(Report.id)).where(
            Report.status == "active",
            Report.geom.is_not(None),
            or_(
                Report.expires_at.is_(None),
                Report.expires_at > now,
            ),
        )
    ) or 0

    status_rows = db.execute(
        select(Report.status, func.count(Report.id))
        .group_by(Report.status)
    ).all()

    type_rows = db.execute(
        select(Report.type, func.count(Report.id))
        .group_by(Report.type)
    ).all()

    day_rows = db.execute(
        select(
            func.date(Report.created_at),
            func.count(Report.id),
        )
        .group_by(func.date(Report.created_at))
        .order_by(func.date(Report.created_at))
    ).all()

    reports_by_status = {
        report_status: count
        for report_status, count in status_rows
    }

    reports_by_type = {
        report_type: count
        for report_type, count in type_rows
    }

    reports_by_day = {
        str(day): count
        for day, count in day_rows
    }

    return AdminStatsResponse(
        total_users=total_users,
        blocked_users=blocked_users,
        total_reports=total_reports,
        active_reports=active_reports,
        cleared_reports=reports_by_status.get("cleared", 0),
        rejected_reports=reports_by_status.get("rejected", 0),
        active_hazards=active_hazards,
        reports_by_type=reports_by_type,
        reports_by_status=reports_by_status,
        reports_by_day=reports_by_day,
    )
