"""JWT secret hardening: no insecure default may ever be used."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestSecretRequired:
    def test_missing_secret_refuses_settings(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        with pytest.raises(ValidationError) as exc:
            Settings(_env_file=None)
        assert "JWT_SECRET_KEY" in str(exc.value)

    def test_blank_secret_refuses_settings(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "   ")
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_short_secret_ok_in_dev_but_not_production(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "short-but-present")
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings(_env_file=None)
        assert settings.jwt_secret == "short-but-present"  # dev: warn-level ok

        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(ValidationError) as exc:
            Settings(_env_file=None)
        assert "too short" in str(exc.value)

    def test_strong_secret_accepted_in_production(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "x" * 43)
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings(_env_file=None)
        assert settings.environment == "production"

    def test_secret_never_leaks_via_repr(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "x" * 43)
        settings = Settings(_env_file=None)
        dumped = repr(settings) + str(settings.model_dump())
        assert "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" not in dumped

    def test_legacy_alias_still_readable(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.setenv("JWT_SECRET", "legacy-secret-for-backwards-compat-000")
        settings = Settings(_env_file=None)
        assert settings.jwt_secret == "legacy-secret-for-backwards-compat-000"


class TestTokenMechanics:
    def test_tampered_token_rejected(self, client, auth_headers):
        headers, _ = auth_headers(email="tamper@example.com")
        token = headers["Authorization"].split()[1]
        tampered = token[:-4] + ("AAAA" if token[-4:] != "AAAA" else "BBBB")
        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {tampered}"}
        )
        assert response.status_code == 401

    def test_wrong_auth_scheme_rejected(self, client, auth_headers):
        headers, _ = auth_headers(email="scheme@example.com")
        token = headers["Authorization"].split()[1]
        assert (
            client.get(
                "/api/auth/me", headers={"Authorization": f"Basic {token}"}
            ).status_code
            == 401
        )
