"""Google Drive (OAuth, user-owned quota).

All writes are hard-locked to the folder tree under GDRIVE_ROOT_FOLDER_ID so the app can
never touch anything else in the connected Drive, even if a caller passes a stray folder id.

Auth: OAuth refresh token (service accounts have no Drive quota on a personal account).
The token was granted with the `drive.file` scope, so Google itself already restricts
visibility to files this app created — the parent guard below is the second layer.

Config: DriveSettings below (Coolify env).
"""

import re

from pydantic import SecretStr

from zservice.core.config import ZsSettings, env_field, settings_getter
from zservice.core.errors import ApiError


class DriveSettings(ZsSettings):
    root_folder_id: str = env_field(
        "GDRIVE_ROOT_FOLDER_ID",
        "",
        "google_drive_folder_id",
        doc="Every Drive read and write stays inside this folder tree.",
    )
    oauth_client_id: str = env_field("GOOGLE_OAUTH_CLIENT_ID", "", doc="OAuth client id.")
    oauth_client_secret: SecretStr = env_field(
        "GOOGLE_OAUTH_CLIENT_SECRET", SecretStr(""), doc="OAuth client secret."
    )
    oauth_refresh_token: SecretStr = env_field(
        "GOOGLE_OAUTH_REFRESH_TOKEN",
        SecretStr(""),
        doc="Refresh token granted with the drive.file scope.",
    )


get_settings = settings_getter(DriveSettings)


def root_folder_id() -> str:
    return get_settings().root_folder_id


def configured() -> bool:
    """All four values are set; a job skips its upload otherwise."""
    cfg = get_settings()
    secrets = (cfg.oauth_client_secret, cfg.oauth_refresh_token)
    return bool(cfg.root_folder_id and cfg.oauth_client_id) and all(
        s.get_secret_value() for s in secrets
    )


def _drive_service():
    """Build an authorized Drive client; access token auto-refreshes."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not configured():
        raise ApiError(503, "drive.not_configured", "Google Drive is not configured on the server.")
    cfg = get_settings()
    creds = Credentials(
        token=None,
        refresh_token=cfg.oauth_refresh_token.get_secret_value(),
        client_id=cfg.oauth_client_id,
        client_secret=cfg.oauth_client_secret.get_secret_value(),
        token_uri="https://oauth2.googleapis.com/token",  # noqa: S106 — a URL, not a secret
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# Drive ids are URL-safe base64-ish tokens. Checking the shape first keeps any other text
# out of the files().list `q` expression and out of API calls.
_DRIVE_ID = re.compile(r"[A-Za-z0-9_-]{10,200}")


def _check_id(file_id: str) -> None:
    if not _DRIVE_ID.fullmatch(file_id):
        raise ApiError(400, "drive.bad_id", "not a Google Drive id")


def _assert_under_root(svc, folder_id: str):
    """Raise unless folder_id is the ROOT folder or a descendant of it.

    Walks parents up to ROOT. This is what stops the app from ever writing into,
    or reading from, folders outside the configured root.
    """
    if not folder_id:
        raise ApiError(400, "drive.folder_required", "folder_id is required.")
    _check_id(folder_id)
    root = root_folder_id()
    seen = set()
    cur = folder_id
    while cur and cur not in seen:
        if cur == root:
            return
        seen.add(cur)
        try:
            meta = svc.files().get(fileId=cur, fields="id,parents").execute()
        except Exception:
            # Unreadable id (drive.file hides non-app files) => treat as outside root.
            raise _outside_root() from None
        parents = meta.get("parents") or []
        cur = parents[0] if parents else None
    raise _outside_root()


def _outside_root() -> ApiError:
    return ApiError(403, "drive.outside_root", "Target folder is outside the allowed Drive folder.")


def drive_create_subfolder(name: str, parent_id: str | None = None) -> dict:
    svc = _drive_service()
    parent_id = parent_id or root_folder_id()
    _assert_under_root(svc, parent_id)
    return (
        svc.files()
        .create(
            body={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            },
            fields="id,name",
        )
        .execute()
    )


def drive_upload_bytes(
    name: str, content: bytes, mime_type: str = "text/plain", folder_id: str | None = None
) -> dict:
    from googleapiclient.http import MediaInMemoryUpload

    svc = _drive_service()
    folder_id = folder_id or root_folder_id()
    _assert_under_root(svc, folder_id)
    return (
        svc.files()
        .create(
            body={"name": name, "parents": [folder_id]},
            media_body=MediaInMemoryUpload(content, mimetype=mime_type),
            fields="id,name,webViewLink",
        )
        .execute()
    )


def drive_list(folder_id: str | None = None) -> list[dict]:
    svc = _drive_service()
    folder_id = folder_id or root_folder_id()
    _assert_under_root(svc, folder_id)
    res = (
        svc.files()
        .list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id,name,mimeType,modifiedTime,size)",
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    return res.get("files", [])


def drive_delete(file_id: str):
    """Delete a file/folder — only if it lives under ROOT."""
    svc = _drive_service()
    _check_id(file_id)
    if file_id == root_folder_id():
        raise ApiError(403, "drive.root_delete", "Refusing to delete the root folder.")
    # An item is in-scope if its parent is under ROOT.
    try:
        meta = svc.files().get(fileId=file_id, fields="id,parents").execute()
    except Exception:
        raise ApiError(
            403, "drive.outside_root", "Target is outside the allowed Drive folder."
        ) from None
    parents = meta.get("parents") or []
    _assert_under_root(svc, parents[0] if parents else "")
    svc.files().delete(fileId=file_id).execute()


def drive_folder_link(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}"
