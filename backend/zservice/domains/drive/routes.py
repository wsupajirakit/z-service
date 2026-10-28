"""/api/drive/{files,folder} (moved unchanged from main.py)."""

from fastapi import APIRouter
from pydantic import BaseModel

from zservice.core.errors import ApiError
from zservice.integrations.drive import drive_create_subfolder, drive_list

router = APIRouter()


class DriveFolderRequest(BaseModel):
    name: str
    parent_id: str | None = None


@router.get("/api/drive/files")
def drive_files(folder_id: str | None = None):
    return {"files": drive_list(folder_id)}


@router.post("/api/drive/folder")
def drive_new_folder(req: DriveFolderRequest):
    name = req.name.strip()
    if not name:
        raise ApiError(400, "drive.name_required", "Folder name is required.")
    return drive_create_subfolder(name, req.parent_id)
