from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from backend.tests.adversarial.conftest import JWT_ALG_NONE_PAYLOAD, JWT_WRONG_SECRET


class TestJWTSecurity:
    def _make_alg_none_token(self):
        return JWT_ALG_NONE_PAYLOAD

    def _make_rs256_token(self):
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {
            "sub": str(uuid.uuid4()),
            "level": 0,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(payload, "any_public_key", algorithm="HS256")
        encoded_header = jwt.utils.base64url_encode(
            jwt.utils.force_bytes(str(header))
        ).decode("utf-8")
        parts = token.split(".")
        return f"{encoded_header}.{parts[1]}.{parts[2]}"

    def _make_expired_token(self):
        payload = {
            "sub": str(uuid.uuid4()),
            "level": 5,
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        }
        return jwt.encode(payload, "test_secret_key_12345", algorithm="HS256")

    def _make_wrong_secret_token(self):
        return JWT_WRONG_SECRET

    def _make_forged_level_zero_token(self):
        payload = {
            "sub": str(uuid.uuid4()),
            "level": 0,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        return jwt.encode(payload, "wrong_secret_key", algorithm="HS256")

    async def _check_token_rejected(self, client, token):
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401, (
            f"Forged JWT was accepted: status {resp.status_code}"
        )
        data = resp.json()
        assert data["code"] in ("auth_error", "token_expired", "invalid_token")

    async def _check_admin_access_rejected(self, client, token):
        resp = await client.get(
            "/api/auth/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401, (
            f"Forged admin JWT was accepted: status {resp.status_code}"
        )

    async def test_alg_none_jwt_rejected(self, client):
        token = self._make_alg_none_token()
        await self._check_token_rejected(client, token)

    async def test_rs256_hs256_confusion_rejected(self, client):
        token = self._make_rs256_token()
        await self._check_token_rejected(client, token)

    async def test_expired_jwt_rejected(self, client):
        token = self._make_expired_token()
        await self._check_token_rejected(client, token)

    async def test_wrong_secret_jwt_rejected(self, client):
        token = self._make_wrong_secret_token()
        await self._check_token_rejected(client, token)

    async def test_forged_level_zero_jwt_rejected(self, client):
        token = self._make_forged_level_zero_token()
        await self._check_admin_access_rejected(client, token)
