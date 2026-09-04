"""Free-tier adapters for hosting a CityMaps video and drafting a TikTok post."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen


BUFFER_API = "https://api.buffer.com"
Transport = Callable[[Request, float], bytes]


class PublishingError(RuntimeError):
    """A publishing failure that can be displayed directly in the studio."""


@dataclass(frozen=True)
class BufferChannel:
    id: str
    name: str
    service: str


@dataclass(frozen=True)
class BufferPost:
    id: str
    status: str


def _read_response(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _error_detail(error: HTTPError) -> str:
    detail = error.read().decode("utf-8", errors="replace")
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        return detail or error.reason
    return str(payload.get("error", {}).get("message") or payload.get("message") or detail)


class BufferClient:
    """Small interface over the Buffer GraphQL operations CityMaps needs."""

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = BUFFER_API,
        timeout: float = 30,
        transport: Transport = _read_response,
    ) -> None:
        if not api_key.strip():
            raise ValueError("A Buffer API key is required.")
        self._api_key = api_key.strip()
        self._endpoint = endpoint
        self._timeout = timeout
        self._transport = transport

    def list_channels(self, service: str | None = None) -> tuple[BufferChannel, ...]:
        account = self._graphql(
            "query GetOrganizations { account { organizations { id } } }"
        )
        organizations = account.get("account", {}).get("organizations", [])
        channels: list[BufferChannel] = []
        for organization in organizations:
            organization_id = _graphql_string(str(organization["id"]))
            data = self._graphql(
                "query GetChannels { channels(input: { organizationId: "
                f"{organization_id}"
                " }) { id name displayName service } }"
            )
            channels.extend(
                BufferChannel(
                    id=str(item["id"]),
                    name=str(item.get("displayName") or item.get("name") or item["id"]),
                    service=str(item["service"]),
                )
                for item in data.get("channels", [])
            )
        if service is None:
            return tuple(channels)
        return tuple(channel for channel in channels if channel.service == service)

    def create_video_draft(
        self,
        video_url: str,
        caption: str,
        channel_id: str,
    ) -> BufferPost:
        """Create a Buffer draft that cannot publish until explicitly scheduled."""
        parsed_url = urlparse(video_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("The hosted video must have a public HTTPS URL.")
        if not caption.strip():
            raise ValueError("The TikTok caption cannot be empty.")
        if not channel_id.strip():
            raise ValueError("A TikTok channel is required.")

        data = self._graphql(
            "mutation CreateVideoDraft { createPost(input: { "
            f"text: {_graphql_string(caption.strip())}, "
            f"channelId: {_graphql_string(channel_id.strip())}, "
            "schedulingType: automatic, mode: addToQueue, saveToDraft: true, "
            "assets: [{ video: { "
            f"url: {_graphql_string(video_url)}, "
            "metadata: { thumbnailOffset: 0 } } }] "
            "}) { ... on PostActionSuccess { post { id status } } "
            "... on MutationError { message } } }"
        )
        result = data.get("createPost", {})
        if result.get("message"):
            raise PublishingError(f"Buffer could not create the draft: {result['message']}")
        post = result.get("post")
        if not post:
            raise PublishingError("Buffer returned no draft after creating the post.")
        return BufferPost(id=str(post["id"]), status=str(post["status"]))

    def _graphql(self, query: str) -> dict[str, object]:
        request = Request(
            self._endpoint,
            data=json.dumps({"query": query}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        payload = _send_json(request, self._timeout, self._transport, "Buffer")
        errors = payload.get("errors", [])
        if errors:
            message = "; ".join(str(error.get("message", error)) for error in errors)
            raise PublishingError(f"Buffer rejected the request: {message}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise PublishingError("Buffer returned an invalid GraphQL response.")
        return data


class CloudinaryClient:
    """Upload MP4 bytes to a stable public Cloudinary URL."""

    def __init__(
        self,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        *,
        timeout: float = 120,
        transport: Transport = _read_response,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not all(value.strip() for value in (cloud_name, api_key, api_secret)):
            raise ValueError("A complete Cloudinary URL is required.")
        self._cloud_name = cloud_name.strip()
        self._api_key = api_key.strip()
        self._api_secret = api_secret.strip()
        self._timeout = timeout
        self._transport = transport
        self._clock = clock

    @classmethod
    def from_url(
        cls,
        cloudinary_url: str,
        **kwargs: object,
    ) -> CloudinaryClient:
        parsed = urlparse(cloudinary_url.strip())
        if (
            parsed.scheme != "cloudinary"
            or not parsed.username
            or not parsed.password
            or not parsed.hostname
        ):
            raise ValueError(
                "Cloudinary URL must look like cloudinary://API_KEY:API_SECRET@CLOUD_NAME."
            )
        return cls(
            parsed.hostname,
            unquote(parsed.username),
            unquote(parsed.password),
            **kwargs,
        )

    def upload_video(self, video: bytes, name: str) -> str:
        if not video:
            raise ValueError("The generated video is empty.")
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-") or "citymap"
        timestamp = str(int(self._clock()))
        public_id = f"{safe_name}-{uuid.uuid4().hex[:10]}"
        signed_parameters = {
            "folder": "citymaps",
            "public_id": public_id,
            "timestamp": timestamp,
        }
        signature_source = "&".join(
            f"{key}={value}" for key, value in sorted(signed_parameters.items())
        )
        signature = hashlib.sha1(
            f"{signature_source}{self._api_secret}".encode("utf-8")
        ).hexdigest()
        fields = {
            **signed_parameters,
            "api_key": self._api_key,
            "signature": signature,
        }
        boundary = f"citymaps-{uuid.uuid4().hex}"
        body = _multipart_body(fields, "file", f"{safe_name}.mp4", video, boundary)
        request = Request(
            f"https://api.cloudinary.com/v1_1/{quote(self._cloud_name)}/video/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        payload = _send_json(request, self._timeout, self._transport, "Cloudinary")
        video_url = payload.get("secure_url")
        if not isinstance(video_url, str) or not video_url.startswith("https://"):
            raise PublishingError("Cloudinary returned no public video URL.")
        return video_url


def _graphql_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _multipart_body(
    fields: dict[str, str],
    file_field: str,
    filename: str,
    file_data: bytes,
    boundary: str,
) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{filename}"\r\n'
            ).encode(),
            b"Content-Type: video/mp4\r\n\r\n",
            file_data,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks)


def _send_json(
    request: Request,
    timeout: float,
    transport: Transport,
    service_name: str,
) -> dict[str, object]:
    try:
        response = transport(request, timeout)
    except HTTPError as error:
        raise PublishingError(
            f"{service_name} rejected the request ({error.code}): {_error_detail(error)}"
        ) from error
    except URLError as error:
        raise PublishingError(f"Could not reach {service_name}: {error.reason}") from error
    try:
        payload = json.loads(response or b"{}")
    except json.JSONDecodeError as error:
        raise PublishingError(f"{service_name} returned an invalid response.") from error
    if not isinstance(payload, dict):
        raise PublishingError(f"{service_name} returned an invalid response.")
    return payload
