import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_jwt_secret_is_required(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "secret",
    [
        "change-me",
        "changeme",
        "replace-with-a-long-random-secret",
        "your-secret",
        "secret",
    ],
)
def test_jwt_secret_rejects_placeholders(secret):
    with pytest.raises(ValidationError):
        Settings(jwt_secret=secret, _env_file=None)


def test_jwt_secret_rejects_values_shorter_than_32_bytes():
    with pytest.raises(ValidationError):
        Settings(jwt_secret="short-secret", _env_file=None)


def test_jwt_secret_accepts_valid_secret():
    secret = "pharos-production-secret-with-more-than-32-bytes"

    config = Settings(jwt_secret=secret, _env_file=None)

    assert config.jwt_secret == secret


@pytest.mark.parametrize("algorithm", ["none", "RS256", "HS512", ""])
def test_jwt_algorithm_rejects_unsupported_values(algorithm):
    with pytest.raises(ValidationError):
        Settings(
            jwt_secret="pharos-valid-test-secret-with-more-than-32-bytes",
            jwt_algorithm=algorithm,
            _env_file=None,
        )


def test_jwt_algorithm_accepts_hs256():
    config = Settings(
        jwt_secret="pharos-valid-test-secret-with-more-than-32-bytes",
        jwt_algorithm="HS256",
        _env_file=None,
    )

    assert config.jwt_algorithm == "HS256"


@pytest.mark.parametrize("expiry", [0, -1, -60])
def test_jwt_expiry_rejects_non_positive_values(expiry):
    with pytest.raises(ValidationError):
        Settings(
            jwt_secret="pharos-valid-test-secret-with-more-than-32-bytes",
            jwt_expire_minutes=expiry,
            _env_file=None,
        )


def test_jwt_expiry_accepts_positive_value():
    config = Settings(
        jwt_secret="pharos-valid-test-secret-with-more-than-32-bytes",
        jwt_expire_minutes=60,
        _env_file=None,
    )

    assert config.jwt_expire_minutes == 60
