
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models import User
from backend.app.security.deps import require_admin

def test_register_creates_driver_account(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "Test Driver",
            "email": "driver@example.com",
            "password": "TestPassword123!",
            "preferred_language": "en",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "driver@example.com"
    assert data["role"] == "driver"
    assert "password_hash" not in data

def test_register_rejects_duplicate_email(client):
    payload = {
        "name": "Test Driver",
        "email": "duplicate@example.com",
        "password": "TestPassword123!",
        "preferred_language": "en",
    }

    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409

def test_register_rejects_weak_password(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "Weak Password User",
            "email": "weak@example.com",
            "password": "short",
            "preferred_language": "en",
        },
    )

    assert response.status_code == 422

def test_login_returns_access_token(client):
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Login Driver",
            "email": "login@example.com",
            "password": "TestPassword123!",
            "preferred_language": "en",
        },
    )
    assert register_response.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]

def test_login_rejects_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "name": "Wrong Password Driver",
            "email": "wrong-password@example.com",
            "password": "CorrectPassword123!",
            "preferred_language": "en",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "wrong-password@example.com",
            "password": "IncorrectPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

def test_blocked_user_cannot_login(client, db_session):
    client.post(
        "/auth/register",
        json={
            "name": "Blocked Driver",
            "email": "blocked@example.com",
            "password": "TestPassword123!",
            "preferred_language": "en",
        },
    )

    user = db_session.scalar(
        select(User).where(User.email == "blocked@example.com")
    )
    assert user is not None

    user.is_blocked = True
    db_session.flush()

    response = client.post(
        "/auth/login",
        json={
            "email": "blocked@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is blocked"

def test_expired_token_is_rejected(client):
    expired_token = jwt.encode(
        {
            "sub": "1",
            "role": "driver",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = client.put(
        "/user/profile",
        json={
            "name": "Test Driver",
            "preferred_language": "en",
        },
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401

def test_tampered_token_is_rejected(client):
    tampered_token = jwt.encode(
        {
            "sub": "1",
            "role": "driver",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "definitely-not-the-real-secret",
        algorithm=settings.jwt_algorithm,
    )

    response = client.put(
        "/user/profile",
        json={
            "name": "Test Driver",
            "preferred_language": "en",
        },
        headers={"Authorization": f"Bearer {tampered_token}"},
    )

    assert response.status_code == 401


def test_driver_is_rejected_by_require_admin(db_session):
    driver = User(
        name="Authorization Driver",
        email="authorization-driver@example.com",
        password_hash="test-hash",
        role="driver",
        preferred_language="en",
        is_blocked=False,
    )
    db_session.add(driver)
    db_session.flush()

    try:
        require_admin(driver)
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Admin access required"
    else:
        raise AssertionError("A driver must not pass admin authorization")

def test_profile_update_succeeds_for_authenticated_user(client):
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Original Name",
            "email": "profile-update@example.com",
            "password": "TestPassword123!",
            "preferred_language": "en",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": "profile-update@example.com",
            "password": "TestPassword123!",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.put(
        "/user/profile",
        json={
            "name": "Updated Name",
            "preferred_language": "kn",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["preferred_language"] == "kn"
    assert data["email"] == "profile-update@example.com"
    assert data["role"] == "driver"
    assert "password_hash" not in data

def test_profile_update_rejects_invalid_language(client):
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Language Test Driver",
            "email": "language-test@example.com",
            "password": "TestPassword123!",
            "preferred_language": "en",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": "language-test@example.com",
            "password": "TestPassword123!",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.put(
        "/user/profile",
        json={
            "name": "Updated Name",
            "preferred_language": "fr",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422

def test_profile_update_requires_authentication(client):
    response = client.put(
        "/user/profile",
        json={
            "name": "Updated Name",
            "preferred_language": "hi",
        },
    )

    assert response.status_code in (401, 403)

def test_driver_gets_403_on_admin_protected_http_route(client, db_session):
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from backend.app.database import get_db
    from backend.app.security.deps import get_current_user, require_admin

    # Use an isolated test app; do not add a temporary route to production.
    test_app = FastAPI()

    def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    @test_app.get("/test-admin", dependencies=[Depends(require_admin)])
    def test_admin_route():
        return {"message": "admin access granted"}

    driver = User(
        name="HTTP Authorization Driver",
        email="http-authorization-driver@example.com",
        password_hash="test-hash",
        role="driver",
        preferred_language="en",
        is_blocked=False,
    )
    db_session.add(driver)
    db_session.flush()

    from backend.app.security.jwt import create_token

    token = create_token(driver.id, driver.role)

    with TestClient(test_app) as test_client:
        response = test_client.get(
            "/test-admin",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"
