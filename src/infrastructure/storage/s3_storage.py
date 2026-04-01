"""S3-compatible object storage helpers (MinIO / AWS S3)."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass

from src.core.config import settings


def _client():
    if not (settings.s3_endpoint and settings.s3_bucket and settings.s3_access_key and settings.s3_secret_key):
        raise RuntimeError("s3_not_configured")
    try:
        import boto3
        from botocore.config import Config
    except ModuleNotFoundError as e:
        raise RuntimeError("s3_sdk_missing") from e
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        use_ssl=bool(settings.s3_use_ssl),
        config=Config(signature_version="s3v4"),
    )


@dataclass(frozen=True)
class S3ObjectRef:
    bucket: str
    key: str


@dataclass(frozen=True)
class S3GetObjectStream:
    body: object
    status_code: int
    content_type: str
    content_length: int | None
    content_range: str | None
    accept_ranges: str | None


class MedicalFilesStorage:
    """S3 storage for patient medical files (metadata in DB; content in S3)."""

    def __init__(self) -> None:
        self.bucket = settings.s3_bucket

    def _prefix(self) -> str:
        p = (settings.s3_medical_prefix or "medical").strip().strip("/")
        return p

    def build_key(self, *, clinic_id: str, patient_id: str, file_id: str, filename: str | None) -> str:
        safe_name = (filename or "file").strip().replace("\\", "/").split("/")[-1]
        return f"{self._prefix()}/clinics/{clinic_id}/patients/{patient_id}/{file_id}/{safe_name}"

    def put_bytes(self, *, key: str, content: bytes, content_type: str | None = None) -> None:
        ct = content_type or mimetypes.guess_type(key)[0] or "application/octet-stream"
        c = _client()
        c.put_object(Bucket=self.bucket, Key=key, Body=content, ContentType=ct)

    def put_fileobj(self, *, key: str, fileobj, content_type: str | None = None) -> None:
        ct = content_type or mimetypes.guess_type(key)[0] or "application/octet-stream"
        c = _client()
        c.put_object(Bucket=self.bucket, Key=key, Body=fileobj, ContentType=ct)

    def presign_get(
        self,
        *,
        key: str,
        exp_seconds: int | None = None,
        response_content_type: str | None = None,
        response_content_disposition: str | None = None,
    ) -> str:
        c = _client()
        exp = int(exp_seconds or settings.s3_presign_exp_seconds or 900)
        params = {"Bucket": self.bucket, "Key": key}
        if response_content_type:
            params["ResponseContentType"] = response_content_type
        if response_content_disposition:
            params["ResponseContentDisposition"] = response_content_disposition
        return c.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=exp,
        )

    def delete(self, *, key: str) -> None:
        c = _client()
        c.delete_object(Bucket=self.bucket, Key=key)

    def get_object_stream(self, *, key: str, range_header: str | None = None) -> S3GetObjectStream:
        c = _client()
        params: dict[str, object] = {"Bucket": self.bucket, "Key": key}
        if range_header:
            # Range syntax: bytes=start-end
            params["Range"] = range_header
        res = c.get_object(**params)
        # boto3 returns a StreamingBody in res["Body"]
        headers = res.get("ResponseMetadata", {}).get("HTTPHeaders", {}) or {}
        return S3GetObjectStream(
            body=res["Body"],
            status_code=int(res.get("ResponseMetadata", {}).get("HTTPStatusCode", 200) or 200),
            content_type=str(res.get("ContentType") or headers.get("content-type") or "application/octet-stream"),
            content_length=int(res["ContentLength"]) if res.get("ContentLength") is not None else None,
            content_range=str(headers.get("content-range")) if headers.get("content-range") else None,
            accept_ranges=str(headers.get("accept-ranges")) if headers.get("accept-ranges") else None,
        )

    def health_check(self) -> dict:
        """Non-sensitive probe for readiness checks."""
        try:
            c = _client()
            c.head_bucket(Bucket=self.bucket)
            return {"configured": True, "reachable": True}
        except RuntimeError:
            return {"configured": False, "reachable": False}
        except Exception as e:
            return {"configured": True, "reachable": False, "error": str(e)}


class StaffAvatarsStorage:
    """S3 storage for staff avatars (content in S3; ref in staff_profiles)."""

    def __init__(self) -> None:
        self.bucket = settings.s3_bucket

    def _prefix(self) -> str:
        p = (settings.s3_staff_avatars_prefix or "staff-avatars").strip().strip("/")
        return p

    def build_key(self, *, clinic_id: str, admin_id: str, filename: str | None) -> str:
        safe_name = (filename or "avatar").strip().replace("\\", "/").split("/")[-1]
        return f"{self._prefix()}/clinics/{clinic_id}/admins/{admin_id}/{safe_name}"

    def put_bytes(self, *, key: str, content: bytes, content_type: str | None = None) -> None:
        ct = content_type or mimetypes.guess_type(key)[0] or "application/octet-stream"
        c = _client()
        c.put_object(Bucket=self.bucket, Key=key, Body=content, ContentType=ct)

    def presign_get(
        self,
        *,
        key: str,
        exp_seconds: int | None = None,
        response_content_type: str | None = None,
        response_content_disposition: str | None = None,
    ) -> str:
        c = _client()
        exp = int(exp_seconds or settings.s3_staff_avatars_presign_exp_seconds or 900)
        params = {"Bucket": self.bucket, "Key": key}
        if response_content_type:
            params["ResponseContentType"] = response_content_type
        if response_content_disposition:
            params["ResponseContentDisposition"] = response_content_disposition
        return c.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=exp,
        )


