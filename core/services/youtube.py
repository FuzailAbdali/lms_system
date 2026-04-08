from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _get_google_modules():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImproperlyConfigured(
            "Google API dependencies are missing. Install the packages in requirements.txt first."
        ) from exc

    return Request, Credentials, Flow, build


def _get_token_file():
    return Path(settings.YOUTUBE_TOKEN_FILE)


def _get_client_secret_file():
    client_secret_file = Path(settings.YOUTUBE_CLIENT_SECRET_FILE)
    if not client_secret_file.exists():
        raise ImproperlyConfigured(
            f"YouTube client secret file not found at '{client_secret_file}'."
        )
    return client_secret_file


def get_stored_youtube_credentials():
    """
    Load cached user credentials when available and refresh them if possible.
    """
    Request, Credentials, _, _ = _get_google_modules()
    token_file = _get_token_file()

    credentials = None
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(
            str(token_file),
            settings.YOUTUBE_API_SCOPES,
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_file.write_text(credentials.to_json())

    if credentials and credentials.valid:
        return credentials

    return None


def has_valid_youtube_credentials():
    return get_stored_youtube_credentials() is not None


def _build_web_flow(redirect_uri, state=None):
    _, _, Flow, _ = _get_google_modules()
    client_secret_file = _get_client_secret_file()

    return Flow.from_client_secrets_file(
        str(client_secret_file),
        scopes=settings.YOUTUBE_API_SCOPES,
        state=state,
        redirect_uri=redirect_uri,
    )


def get_youtube_authorization_url():
    flow = _build_web_flow(settings.YOUTUBE_REDIRECT_URI)
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return {
        "authorization_url": authorization_url,
        "state": state,
        "code_verifier": getattr(flow, "code_verifier", None),
    }


def complete_youtube_authorization(authorization_response, state, code_verifier=None):
    flow = _build_web_flow(settings.YOUTUBE_REDIRECT_URI, state=state)
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    token_file = _get_token_file()
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json())
    return credentials


def get_youtube_service():
    """
    Return an authenticated YouTube Data API service instance.
    """
    credentials = get_stored_youtube_credentials()
    if not credentials:
        raise ImproperlyConfigured(
            "YouTube authorization is required. Connect your YouTube account first."
        )

    _, _, _, build = _get_google_modules()
    return build(
        settings.YOUTUBE_API_SERVICE_NAME,
        settings.YOUTUBE_API_VERSION,
        credentials=credentials,
        cache_discovery=False,
    )


def create_youtube_live_stream(title, description="", service=None, is_reusable=True):
    """
    Create a YouTube Live stream with RTMP ingestion and return connection data.

    Returns a dictionary containing:
    - stream_id
    - stream_key
    - ingestion_address
    - stream_url
    """
    if not title or not title.strip():
        raise ValueError("A stream title is required.")

    youtube = service or get_youtube_service()
    response = (
        youtube.liveStreams()
        .insert(
            part="snippet,cdn,contentDetails",
            body={
                "snippet": {
                    "title": title.strip(),
                    "description": description.strip(),
                },
                "cdn": {
                    "ingestionType": "rtmp",
                    "resolution": "variable",
                    "frameRate": "variable",
                },
                "contentDetails": {
                    "isReusable": is_reusable,
                },
            },
        )
        .execute()
    )

    ingestion_info = response.get("cdn", {}).get("ingestionInfo", {})
    stream_key = ingestion_info.get("streamName")
    ingestion_address = ingestion_info.get("ingestionAddress")

    if not stream_key or not ingestion_address:
        raise ImproperlyConfigured("YouTube API did not return RTMP ingestion details for the created stream.")

    return {
        "stream_id": response.get("id"),
        "stream_key": stream_key,
        "ingestion_address": ingestion_address,
        "stream_url": f"{ingestion_address}/{stream_key}",
    }


def create_youtube_live_broadcast(title, start_time, stream_id, service=None, description=""):
    """
    Create an unlisted YouTube Live broadcast and bind it to an existing stream.

    Returns a dictionary containing:
    - broadcast_id
    - watch_url
    """
    if not title or not title.strip():
        raise ValueError("A broadcast title is required.")
    if not stream_id or not str(stream_id).strip():
        raise ValueError("A valid stream_id is required.")

    scheduled_start_time = _normalize_youtube_datetime(start_time)
    youtube = service or get_youtube_service()

    broadcast_response = (
        youtube.liveBroadcasts()
        .insert(
            part="snippet,status,contentDetails",
            body={
                "snippet": {
                    "title": title.strip(),
                    "description": description.strip(),
                    "scheduledStartTime": scheduled_start_time,
                },
                "status": {
                    "privacyStatus": "unlisted",
                },
                "contentDetails": {
                    "enableAutoStart": True,
                    "enableAutoStop": True,
                },
            },
        )
        .execute()
    )

    broadcast_id = broadcast_response.get("id")
    if not broadcast_id:
        raise ImproperlyConfigured("YouTube API did not return a broadcast ID for the created broadcast.")

    youtube.liveBroadcasts().bind(
        part="id,snippet,contentDetails,status",
        id=broadcast_id,
        streamId=str(stream_id).strip(),
    ).execute()

    return {
        "broadcast_id": broadcast_id,
        "watch_url": f"https://www.youtube.com/watch?v={broadcast_id}",
    }


def _normalize_youtube_datetime(value):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("start_time must be a valid ISO 8601 datetime string.") from exc
    else:
        raise ValueError("start_time must be a datetime object or ISO 8601 string.")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.isoformat().replace("+00:00", "Z")
