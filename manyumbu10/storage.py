import os
import uuid

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class CloudinaryMediaStorage(Storage):
    """Django storage backend for durable Manyumbu media on Cloudinary."""

    def __init__(self, folder=None):
        self.folder = (folder or os.getenv("CLOUDINARY_FOLDER") or "manyumbu").strip("/")
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
            secure=True,
        )

    def _save(self, name, content):
        clean_name = self.get_valid_name(os.path.basename(name or "upload"))
        stem, _ = os.path.splitext(clean_name)
        public_id = f"{self.folder}/{stem[:40]}-{uuid.uuid4().hex}"
        result = cloudinary.uploader.upload(
            content,
            public_id=public_id,
            resource_type="auto",
            overwrite=False,
            use_filename=False,
            unique_filename=False,
        )
        resource_type = result.get("resource_type") or self._resource_type_from_content(content)
        return f"{resource_type}:{public_id}"

    def delete(self, name):
        resource_type, public_id = self._split_name(name)
        if public_id:
            cloudinary.uploader.destroy(public_id, resource_type=resource_type or "image", invalidate=True)

    def exists(self, name):
        return False

    def url(self, name):
        if not name:
            return ""
        if str(name).startswith("http://") or str(name).startswith("https://"):
            return str(name)
        resource_type, public_id = self._split_name(name)
        if not public_id:
            return ""
        url, _ = cloudinary_url(public_id, resource_type=resource_type or "image", secure=True)
        return url

    def size(self, name):
        return 0

    def _split_name(self, name):
        raw = str(name or "")
        if ":" in raw:
            resource_type, public_id = raw.split(":", 1)
            return resource_type, public_id
        return "image", raw

    def _resource_type_from_content(self, content):
        content_type = getattr(content, "content_type", "")
        if content_type.startswith("video/"):
            return "video"
        if content_type.startswith("audio/") or content_type.startswith("application/") or content_type.startswith("text/"):
            return "raw"
        return "image"


def absolute_media_url(value):
    if not value:
        return None
    try:
        url = value.url
    except Exception:
        url = str(value or "")
    if not url:
        return None
    if url.startswith("https://"):
        return url
    if url.startswith("http://"):
        return "https://" + url.removeprefix("http://")
    api_url = getattr(settings, "MANYUMBU_API_URL", "").rstrip("/")
    public_url = getattr(settings, "MANYUMBU_PUBLIC_APP_URL", "").rstrip("/")
    base = api_url or public_url
    if base.endswith("/api/v1"):
        base = base[: -len("/api/v1")]
    if base and url.startswith("/"):
        return f"{base}{url}"
    return url

