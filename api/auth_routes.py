"""REST /api/auth/* — 签发与续期 token。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from auth.oauth import AuthError, OAuthService, TokenExpired, extract_bearer


class TokenIn(BaseModel):
    deviceId: str = Field(alias="deviceId")
    deviceType: str = Field(default="pc", alias="deviceType")
    scopes: Optional[list] = None

    model_config = {"populate_by_name": True}


class RefreshIn(BaseModel):
    refreshToken: str = Field(alias="refreshToken")

    model_config = {"populate_by_name": True}


def create_auth_router(oauth: OAuthService) -> APIRouter:
    router = APIRouter(prefix="/api/auth")

    @router.post("/token")
    def issue_token(body: TokenIn) -> Dict[str, Any]:
        try:
            pair = oauth.issue_tokens(
                device_id=body.deviceId,
                device_type=body.deviceType or "pc",
                scopes=body.scopes,
            )
        except AuthError as e:
            raise HTTPException(400, str(e)) from e
        return pair.to_dict()

    @router.post("/refresh")
    def refresh_token(body: RefreshIn) -> Dict[str, Any]:
        try:
            pair = oauth.refresh(body.refreshToken)
        except TokenExpired as e:
            raise HTTPException(401, str(e)) from e
        except AuthError as e:
            raise HTTPException(401, str(e)) from e
        return pair.to_dict()

    @router.post("/revoke")
    def revoke(body: RefreshIn) -> Dict[str, Any]:
        oauth.revoke(body.refreshToken)
        return {"ok": True}

    @router.get("/whoami")
    def whoami(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
        token = extract_bearer(authorization)
        try:
            claims = oauth.allow_register(token)
        except TokenExpired as e:
            raise HTTPException(401, str(e)) from e
        except AuthError as e:
            raise HTTPException(401, str(e)) from e
        return {
            "deviceId": claims.get("sub"),
            "deviceType": claims.get("device_type"),
            "scopes": claims.get("scopes"),
            "exp": claims.get("exp"),
        }

    return router


def mount_auth_api(app: Any, oauth: OAuthService) -> None:
    app.include_router(create_auth_router(oauth))
