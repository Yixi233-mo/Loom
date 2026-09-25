"""OAuth 风格 token 签发 / 校验 / 续期（标准库 HS256 风格）。

接入后可替换 WS 注册的临时 HMAC 方案：
  未授权设备无法注册；access 过期可用 refresh 续期。

Token 形态：base64url(claims_json) + "." + base64url(hmac_sha256)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

DEFAULT_SECRET_ENV = "LOOM_AUTH_SECRET"


class AuthError(Exception):
    """鉴权失败。"""


class TokenExpired(AuthError):
    """access/refresh 已过期，可尝试 refresh。"""


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


class OAuthService:
    """最小 OAuth2 client_credentials 语义（设备端拿 token）。"""

    def __init__(
        self,
        secret: Optional[str] = None,
        access_ttl: int = 3600,
        refresh_ttl: int = 7 * 24 * 3600,
    ) -> None:
        self.secret = (secret or os.environ.get(DEFAULT_SECRET_ENV) or "loom-auth-dev").encode()
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl
        # 已吊销 refresh jti
        self._revoked: set[str] = set()

    # ---- 签发 ----

    def _sign(self, claims: Dict[str, Any]) -> str:
        payload = _b64u(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
        sig = _b64u(hmac.new(self.secret, payload.encode(), hashlib.sha256).digest())
        return payload + "." + sig

    def _verify_sig(self, token: str) -> Dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 2:
            raise AuthError("token 格式错误")
        payload, sig = parts
        expect = _b64u(hmac.new(self.secret, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expect, sig):
            raise AuthError("token 签名无效")
        try:
            claims = json.loads(_b64u_decode(payload))
        except Exception as e:  # noqa: BLE001
            raise AuthError(f"token claims 无法解析: {e}") from e
        if not isinstance(claims, dict):
            raise AuthError("token claims 非法")
        return claims

    def _issue(
        self,
        typ: str,
        device_id: str,
        device_type: str,
        ttl: int,
        scopes: Optional[list] = None,
    ) -> str:
        now = int(time.time())
        claims = {
            "typ": typ,
            "sub": device_id,
            "device_type": device_type,
            "scopes": scopes or ["device.register"],
            "iat": now,
            "exp": now + ttl,
            "jti": secrets.token_hex(8),
        }
        return self._sign(claims)

    def issue_tokens(
        self,
        device_id: str,
        device_type: str = "pc",
        scopes: Optional[list] = None,
    ) -> TokenPair:
        """client_credentials：按设备签发 access + refresh。"""
        if not device_id:
            raise AuthError("device_id 不能为空")
        access = self._issue("access", device_id, device_type, self.access_ttl, scopes)
        refresh = self._issue("refresh", device_id, device_type, self.refresh_ttl, scopes)
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.access_ttl,
        )

    # ---- 校验 ----

    def verify_access(self, token: str) -> Dict[str, Any]:
        """校验 access token；过期抛 TokenExpired，非法抛 AuthError。"""
        claims = self._verify_sig(token)
        if claims.get("typ") != "access":
            raise AuthError("非 access token")
        exp = int(claims.get("exp") or 0)
        if int(time.time()) >= exp:
            raise TokenExpired("access token 已过期")
        return claims

    def verify_refresh(self, token: str) -> Dict[str, Any]:
        claims = self._verify_sig(token)
        if claims.get("typ") != "refresh":
            raise AuthError("非 refresh token")
        jti = claims.get("jti")
        if jti in self._revoked:
            raise AuthError("refresh token 已吊销")
        exp = int(claims.get("exp") or 0)
        if int(time.time()) >= exp:
            raise TokenExpired("refresh token 已过期")
        return claims

    def refresh(self, refresh_token: str) -> TokenPair:
        """token 过期可续期：用 refresh 换新 access（并轮换 refresh）。"""
        claims = self.verify_refresh(refresh_token)
        # 轮换：旧 refresh 吊销
        if claims.get("jti"):
            self._revoked.add(str(claims["jti"]))
        return self.issue_tokens(
            device_id=str(claims.get("sub") or ""),
            device_type=str(claims.get("device_type") or "pc"),
            scopes=list(claims.get("scopes") or []),
        )

    def revoke(self, refresh_token: str) -> None:
        try:
            claims = self._verify_sig(refresh_token)
        except AuthError:
            return
        if claims.get("jti"):
            self._revoked.add(str(claims["jti"]))

    def allow_register(self, token: Optional[str]) -> Dict[str, Any]:
        """设备注册用：无 token / 无效 / 过期 → AuthError（未授权设备无法注册）。"""
        if not token:
            raise AuthError("缺少 access token")
        return self.verify_access(token)


def extract_bearer(header_value: Optional[str]) -> Optional[str]:
    if not header_value:
        return None
    parts = header_value.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return header_value.strip() or None
