"""Async Fleet API client - the bot's only tool layer (Fleet API is the sole DB writer).

Mirrors the n8n header convention: X-Internal-Token + X-Caller-Context. Most bot
calls run as admin (the bot is a trusted internal caller); driver-scoped reads pass a
driver caller-context so Fleet API's ownership filter returns just that driver's rows.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings


def admin_ctx(company_id: str | None = None, impersonator: str | None = None) -> dict[str, str]:
    ctx = {"role": "admin"}
    if company_id:
        ctx["company_id"] = str(company_id)
    if impersonator:
        ctx["impersonator"] = str(impersonator)
    return ctx


def driver_ctx(
    driver_id: str, company_id: str | None = None, impersonator: str | None = None
) -> dict[str, str]:
    ctx = {"role": "driver", "driver_id": str(driver_id)}
    if company_id:
        ctx["company_id"] = str(company_id)
    if impersonator:
        ctx["impersonator"] = str(impersonator)
    return ctx


class FleetClient:
    def __init__(
        self, base_url: str | None = None, token: str | None = None,
        company_id: str | None = None, impersonator: str | None = None,
    ) -> None:
        self._base = (base_url or settings.fleet_api_url).rstrip("/")
        self._token = token or settings.internal_service_token
        # Bound tenant: every default caller-context (admin/driver) carries it so all
        # downstream flow calls are company-scoped. whoami/enroll stay company-less.
        self._company_id = company_id
        # System-admin impersonation (Feature 6): the operator app_user id, stamped on
        # every default caller-context so Customer-Live writes are auditable.
        self._impersonator = impersonator

    def for_company(self, company_id: str | None) -> FleetClient:
        """A shallow copy bound to ``company_id`` (per-update tenant scoping)."""
        return FleetClient(self._base, self._token, company_id, self._impersonator)

    def as_impersonator(self, impersonator: str | None) -> FleetClient:
        """A shallow copy whose default caller-contexts carry the operator id."""
        return FleetClient(self._base, self._token, self._company_id, impersonator)

    def _headers(self, caller: dict[str, Any] | None) -> dict[str, str]:
        headers = {"X-Internal-Token": self._token}
        if caller is not None:
            headers["X-Caller-Context"] = json.dumps(caller)
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        caller: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(base_url=self._base, timeout=30) as client:
            return await client.request(
                method, path, headers=self._headers(caller), params=params, json=json_body
            )

    # --- Identity ---
    async def whoami(self, chat_id: int) -> dict[str, Any] | None:
        """Resolve a chat to a bot user. None when unknown (404)."""
        r = await self._request("GET", "/whoami", params={"chat_id": chat_id})
        return r.json() if r.status_code == 200 else None

    async def enroll(self, chat_id: int, phone_number: str) -> httpx.Response:
        """Enroll by phone match (active driver or authorization).

        200 -> granted; 404 -> not authorized.
        """
        return await self._request(
            "POST",
            "/bot-enroll",
            json_body={"telegram_chat_id": chat_id, "phone_number": phone_number},
        )

    # --- Generic verbs (caller defaults to admin) ---
    def _admin(self) -> dict[str, str]:
        return admin_ctx(self._company_id, self._impersonator)

    async def get(
        self, path: str, *, caller: dict | None = None, params: dict | None = None
    ) -> httpx.Response:
        return await self._request(
            "GET", path, caller=caller or self._admin(), params=params
        )

    async def post(
        self, path: str, json_body: dict, *, caller: dict | None = None
    ) -> httpx.Response:
        return await self._request(
            "POST", path, caller=caller or self._admin(), json_body=json_body
        )

    async def patch(
        self, path: str, json_body: dict, *, caller: dict | None = None
    ) -> httpx.Response:
        return await self._request(
            "PATCH", path, caller=caller or self._admin(), json_body=json_body
        )

    # --- Convenience ---
    async def driver_vehicle(self, driver_id: str) -> dict[str, Any] | None:
        """The driver's assigned vehicle (Fleet API ownership-filters by caller context)."""
        r = await self.get(
            "/vehicles", caller=driver_ctx(driver_id, self._company_id, self._impersonator)
        )
        items = r.json() if r.status_code == 200 else []
        return items[0] if items else None
