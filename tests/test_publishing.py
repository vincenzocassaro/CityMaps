import hashlib
import json

from citymaps.publishing import BufferClient, CloudinaryClient


class FakeTransport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return next(self.responses)


def test_list_channels_can_select_tiktok_across_organizations():
    transport = FakeTransport(
        [
            json.dumps(
                {"data": {"account": {"organizations": [{"id": "org-1"}]}}}
            ).encode(),
            json.dumps(
                {
                    "data": {
                        "channels": [
                            {
                                "id": "channel-1",
                                "name": "citymaps",
                                "displayName": "Funny Cities",
                                "service": "tiktok",
                            },
                            {
                                "id": "channel-2",
                                "name": "citymaps",
                                "displayName": "CityMaps",
                                "service": "youtube",
                            },
                        ]
                    }
                }
            ).encode(),
        ]
    )

    channels = BufferClient("secret", transport=transport).list_channels("tiktok")

    assert [(channel.id, channel.name) for channel in channels] == [
        ("channel-1", "Funny Cities")
    ]
    request, timeout = transport.requests[0]
    assert request.full_url == "https://api.buffer.com"
    assert request.get_header("Authorization") == "Bearer secret"
    assert timeout == 30


def test_create_video_draft_uses_public_url_and_stays_a_draft():
    transport = FakeTransport(
        [
            json.dumps(
                {
                    "data": {
                        "createPost": {
                            "post": {"id": "post-123", "status": "draft"}
                        }
                    }
                }
            ).encode()
        ]
    )

    post = BufferClient("secret", transport=transport).create_video_draft(
        "https://res.cloudinary.com/demo/video/upload/venezia.mp4",
        'Venezia "disegnata" #citymaps',
        "channel-1",
    )

    assert post.id == "post-123"
    assert post.status == "draft"
    request, _ = transport.requests[0]
    query = json.loads(request.data)["query"]
    assert "saveToDraft: true" in query
    assert "https://res.cloudinary.com/demo/video/upload/venezia.mp4" in query
    assert 'Venezia \\"disegnata\\" #citymaps' in query


def test_cloudinary_url_uploads_a_signed_video():
    transport = FakeTransport(
        [
            json.dumps(
                {
                    "secure_url": (
                        "https://res.cloudinary.com/citymaps/video/upload/venezia.mp4"
                    )
                }
            ).encode()
        ]
    )
    client = CloudinaryClient.from_url(
        "cloudinary://key:very-secret@citymaps",
        transport=transport,
        clock=lambda: 1_700_000_000,
    )

    video_url = client.upload_video(b"video-data", "Venezia, Italy")

    assert video_url.endswith("/venezia.mp4")
    request, timeout = transport.requests[0]
    assert request.full_url.endswith("/citymaps/video/upload")
    assert timeout == 120
    body = request.data
    assert b"video-data" in body
    assert b'name="timestamp"\r\n\r\n1700000000' in body
    public_id = body.split(b'name="public_id"\r\n\r\n', 1)[1].split(b"\r\n", 1)[0]
    signature_source = (
        b"folder=citymaps&public_id=" + public_id + b"&timestamp=1700000000very-secret"
    )
    expected_signature = hashlib.sha1(signature_source).hexdigest().encode()
    assert expected_signature in body
