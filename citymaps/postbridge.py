"""Upload CityMaps videos to Post Bridge without exposing its HTTP workflow."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


POST_BRIDGE_API = "https://api.post-bridge.com/v1"
Transport = Callable[[Request, float], bytes]


class PostBridgeError(RuntimeError):
    """A Post Bridge failure that can be shown directly to the user."""


@dataclass(frozen=True)
class SocialAccount:
    id: int
    platform: str
    username: str
    needs_reconnect: bool = False


@dataclass(frozen=True)
class PostBridgePost:
    id: str
    status: str
    is_draft: bool


def _read_response(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return response.read()


class PostBridgeClient:
    """Small interface over account lookup, media upload, and draft creation."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = POST_BRIDGE_API,
        timeout: float = 90,
        transport: Transport = _read_response,
    ) -> None:
        if not api_key.strip():
            raise ValueError("A Post Bridge API key is required.")
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    def list_accounts(self, platform: str | None = None) -> tuple[SocialAccount, ...]:
        payload = self._request_json("GET", "/social-accounts")
        accounts = tuple(
            SocialAccount(
                id=int(item["id"]),
                platform=str(item["platform"]),
                username=str(item["username"]),
                needs_reconnect=bool(item.get("needs_reconnect", False)),
            )
            for item in payload.get("data", [])
        )
        if platform is None:
            return accounts
        return tuple(account for account in accounts if account.platform == platform)

    def create_video_draft(
        self,
        video_path: Path | str,
        caption: str,
        account_id: int,
    ) -> PostBridgePost:
        """Upload one MP4 and save a private, non-publishing Post Bridge draft."""
        video_path = Path(video_path)
        if not video_path.is_file():
            raise ValueError(f"Video not found: {video_path}")
        if video_path.suffix.lower() != ".mp4":
            raise ValueError("Post Bridge publishing currently expects an MP4 video.")
        if not caption.strip():
            raise ValueError("The TikTok caption cannot be empty.")

        upload = self._request_json(
            "POST",
            "/media/create-upload-url",
            {
                "mime_type": "video/mp4",
                "size_bytes": video_path.stat().st_size,
                "name": video_path.name,
            },
        )
        self._upload_video(upload["upload_url"], video_path)
        payload = self._request_json(
            "POST",
            "/posts",
            {
                "caption": caption.strip(),
                "social_accounts": [account_id],
                "media": [upload["media_id"]],
                "is_draft": True,
                "platform_configurations": {
                    "tiktok": {
                        "draft": True,
                        "privacy_status": "private",
                        "allow_comment": False,
                        "allow_duet": False,
                        "allow_stitch": False,
                    }
                },
            },
        )
        return PostBridgePost(
            id=str(payload["id"]),
            status=str(payload["status"]),
            is_draft=bool(payload["is_draft"]),
        )

    def _upload_video(self, upload_url: str, video_path: Path) -> None:
        request = Request(
            upload_url,
            data=video_path.read_bytes(),
            headers={"Content-Type": "video/mp4"},
            method="PUT",
        )
        self._send(request)

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self._base_url}{path}",
            data=data,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        response = self._send(request)
        try:
            return json.loads(response or b"{}")
        except json.JSONDecodeError as error:
            raise PostBridgeError("Post Bridge returned an invalid response.") from error

    def _send(self, request: Request) -> bytes:
        try:
            return self._transport(request, self._timeout)
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            try:
                message = json.loads(detail).get("message", detail)
            except json.JSONDecodeError:
                message = detail
            raise PostBridgeError(
                f"Post Bridge rejected the request ({error.code}): {message}"
            ) from error
        except URLError as error:
            raise PostBridgeError(f"Could not reach Post Bridge: {error.reason}") from error
