"""文件预览路由"""

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/preview")
async def preview_file(path: str = Query(..., description="本地文件绝对路径")):
    """通过 HTTP 提供本地文件预览（解决浏览器 file:/// 限制）"""
    file_path = Path(path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    return FileResponse(file_path, media_type=content_type)
