import json

from citymaps.postbridge import PostBridgeClient


class FakeTransport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return next(self.responses)


def test_list_accounts_can_select_tiktok_accounts():
    transport = FakeTransport(
        [
            json.dumps(
                {
                    "data": [
                        {
                            "id": 12,
                            "platform": "tiktok",
                            "username": "citymaps",
                            "needs_reconnect": False,
                        },
                        {
                            "id": 13,
                            "platform": "youtube",
                            "username": "citymaps",
                            "needs_reconnect": False,
                        },
                    ]
                }
            ).encode()
        ]
    )

    accounts = PostBridgeClient("secret", transport=transport).list_accounts("tiktok")

    assert [(account.id, account.username) for account in accounts] == [(12, "citymaps")]
    request, timeout = transport.requests[0]
    assert request.full_url.endswith("/v1/social-accounts")
    assert request.get_header("Authorization") == "Bearer secret"
    assert timeout == 90


def test_create_video_draft_uploads_media_before_creating_post(tmp_path):
    video_path = tmp_path / "venezia.mp4"
    video_path.write_bytes(b"video-data")
    transport = FakeTransport(
        [
            json.dumps(
                {
                    "media_id": "media-123",
                    "upload_url": "https://uploads.example/video",
                    "name": "venezia.mp4",
                }
            ).encode(),
            b"",
            json.dumps(
                {"id": "post-456", "status": "scheduled", "is_draft": True}
            ).encode(),
        ]
    )
    client = PostBridgeClient("secret", transport=transport)

    post = client.create_video_draft(video_path, "Venezia #citymaps", 12)

    assert post.id == "post-456"
    assert post.is_draft is True
    upload_request, _ = transport.requests[1]
    assert upload_request.method == "PUT"
    assert upload_request.data == b"video-data"
    post_request, _ = transport.requests[2]
    assert post_request.method == "POST"
    payload = json.loads(post_request.data)
    assert payload["media"] == ["media-123"]
    assert payload["social_accounts"] == [12]
    assert payload["is_draft"] is True
    assert payload["platform_configurations"]["tiktok"]["privacy_status"] == "private"
