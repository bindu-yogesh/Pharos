
from datetime import datetime, timedelta, timezone
from typing import Annotated
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models import Report, ReportVote, User
from ..schemas.report import (
    ReportCreate,
    ReportListResponse,
    ReportResponse,
)
from ..security.deps import get_current_user


router = APIRouter(prefix="/reports", tags=["Hazard Reports"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report(
    data: ReportCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ReportResponse:
    """Create a hazard report for the authenticated user."""

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Enforce the configured per-user hourly report limit.
    hour_ago = now - timedelta(hours=1)

    recent_report_count = db.scalar(
        select(func.count(Report.id)).where(
            Report.user_id == current_user.id,
            Report.created_at >= hour_ago,
        )
    )

    if recent_report_count >= settings.reports_per_hour_limit:
        raise HTTPException(
            status_code=429,
            detail="Report submission limit exceeded. Try again later.",
        )

    report = Report(
        user_id=current_user.id,
        type=data.type,
        severity=data.severity,
        description=data.description,
        photo_url=data.photo_url,
        geom=WKTElement(
            f"POINT({data.longitude} {data.latitude})",
            srid=4326,
        ),
        status="active",
        created_at=now,
        expires_at=now + timedelta(hours=settings.report_expiry_hours),
    )

    db.add(report)
    db.flush()

    latitude, longitude = db.execute(
        select(
            func.ST_Y(Report.geom),
            func.ST_X(Report.geom),
        ).where(Report.id == report.id)
    ).one()

    response = ReportResponse(
        id=report.id,
        user_id=report.user_id,
        type=report.type,
        severity=report.severity,
        description=report.description,
        photo_url=report.photo_url,
        latitude=latitude,
        longitude=longitude,
        status=report.status,
        created_at=report.created_at,
        expires_at=report.expires_at,
    )

    db.commit()
    return response


@router.get("", response_model=list[ReportListResponse])
def list_reports(
    db: DbSession,
    bbox: str | None = None,
    since: datetime | None = None,
    type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ReportListResponse]:
    """List active, unexpired reports with optional filters."""

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    confirm_count = (
        select(func.count(ReportVote.id))
        .where(
            ReportVote.report_id == Report.id,
            ReportVote.vote == "confirm",
        )
        .correlate(Report)
        .scalar_subquery()
    )

    clear_count = (
        select(func.count(ReportVote.id))
        .where(
            ReportVote.report_id == Report.id,
            ReportVote.vote == "clear",
        )
        .correlate(Report)
        .scalar_subquery()
    )

    query = (
        select(
            Report,
            func.ST_Y(Report.geom).label("latitude"),
            func.ST_X(Report.geom).label("longitude"),
            confirm_count.label("confirm_votes"),
            clear_count.label("clear_votes"),
        )
        .where(
            Report.status == "active",
            Report.expires_at > now,
        )
    )

    if bbox is not None:
        try:
            values = [float(value.strip()) for value in bbox.split(",")]
            if len(values) != 4:
                raise ValueError

            min_lon, min_lat, max_lon, max_lat = values

        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="bbox must contain minLon,minLat,maxLon,maxLat",
            )

        # Reject NaN and infinity before validating coordinate ranges.
        if not all(
            math.isfinite(value)
            for value in (min_lon, min_lat, max_lon, max_lat)
        ):
            raise HTTPException(
                status_code=422,
                detail="Invalid bounding box coordinates",
            )

        # Validate coordinate ranges and bounding-box order.
        if not (
            -180 <= min_lon <= 180
            and -180 <= max_lon <= 180
            and -90 <= min_lat <= 90
            and -90 <= max_lat <= 90
            and min_lon <= max_lon
            and min_lat <= max_lat
        ):
            raise HTTPException(
                status_code=422,
                detail="Invalid bounding box coordinates",
            )

        query = query.where(
            func.ST_Intersects(
                Report.geom,
                func.ST_MakeEnvelope(
                    min_lon,
                    min_lat,
                    max_lon,
                    max_lat,
                    4326,
                ),
            )
        )

    if since is not None:
        if since.tzinfo is not None:
            since = since.astimezone(timezone.utc).replace(tzinfo=None)

        query = query.where(Report.created_at >= since)

    if type is not None:
        if type not in {"landslide", "falling_rock", "blockage"}:
            raise HTTPException(
                status_code=422,
                detail="Invalid report type",
            )

        query = query.where(Report.type == type)

    query = (
        query
        .order_by(Report.created_at.desc(), Report.id.desc())
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(query).all()

    return [
        ReportListResponse(
            id=row.Report.id,
            user_id=row.Report.user_id,
            type=row.Report.type,
            severity=row.Report.severity,
            description=row.Report.description,
            photo_url=row.Report.photo_url,
            latitude=row.latitude,
            longitude=row.longitude,
            status=row.Report.status,
            created_at=row.Report.created_at,
            expires_at=row.Report.expires_at,
            confirm_votes=row.confirm_votes,
            clear_votes=row.clear_votes,
        )
        for row in rows
    ]


@router.post("/{report_id}/confirm")
def confirm_report(
    report_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Confirm an active hazard report."""

    return cast_vote(
        report_id=report_id,
        vote="confirm",
        db=db,
        current_user=current_user,
    )


@router.post("/{report_id}/clear")
def clear_report(
    report_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Vote that an active hazard report has been cleared."""

    return cast_vote(
        report_id=report_id,
        vote="clear",
        db=db,
        current_user=current_user,
    )


def cast_vote(
    report_id: int,
    vote: str,
    db: Session,
    current_user: User,
) -> dict:
    """Validate and record one vote per user for a report."""

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    report = db.execute(
        select(Report)
        .where(Report.id == report_id)
        .with_for_update()
    ).scalar_one_or_none()

    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if (
        report.status != "active"
        or report.expires_at is None
        or report.expires_at <= now
    ):
        raise HTTPException(
            status_code=400,
            detail="Report is expired or inactive",
        )

    if report.user_id == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Cannot vote on your own report",
        )

    existing_vote = db.execute(
        select(ReportVote).where(
            ReportVote.report_id == report_id,
            ReportVote.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if existing_vote is not None:
        raise HTTPException(
            status_code=409,
            detail="You have already voted on this report",
        )

    db.add(
        ReportVote(
            report_id=report_id,
            user_id=current_user.id,
            vote=vote,
        )
    )

    try:
        db.flush()

        if vote == "confirm":
            report.expires_at = now + timedelta(
                hours=settings.report_expiry_hours
            )

        elif vote == "clear":
            clear_count = db.scalar(
                select(func.count(ReportVote.id)).where(
                    ReportVote.report_id == report_id,
                    ReportVote.vote == "clear",
                )
            )

            if clear_count >= settings.clear_votes_threshold:
                report.status = "cleared"

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="You have already voted on this report",
        )

    return {
        "message": "Vote recorded successfully",
        "report_id": report_id,
        "vote": vote,
        "status": report.status,
    }

def is_suspicious_report(db: Session, report: Report) -> bool:
    """Flag reports with many clear votes or repeated author rejections."""

    clear_vote_count = db.scalar(
        select(func.count(ReportVote.id)).where(
            ReportVote.report_id == report.id,
            ReportVote.vote == "clear",
        )
    )

    rejected_reports = db.scalar(
        select(func.count(Report.id)).where(
            Report.user_id == report.user_id,
            Report.status == "rejected",
        )
    )

    return (
        clear_vote_count >= settings.clear_votes_threshold
        or rejected_reports >= 3
    )