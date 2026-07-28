"""S3-compatible artifact store (AWS S3 or MinIO)."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from continuity_forge_ir import content_hash
from continuity_forge_providers import ArtifactCandidate


class ObjectClient(Protocol):
    def put_object(self, *, bucket: str, key: str, body: bytes, content_type: str) -> None: ...

    def get_object(self, *, bucket: str, key: str) -> bytes | None: ...

    def list_keys(self, *, bucket: str, prefix: str) -> list[str]: ...


class Boto3ObjectClient:
    def __init__(self) -> None:
        try:
            import boto3  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("boto3 not installed. pip install 'continuity-forge[s3]'") from exc
        endpoint = os.environ.get("CF_S3_ENDPOINT") or os.environ.get("AWS_ENDPOINT_URL")
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID")
            or os.environ.get("CF_S3_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
            or os.environ.get("CF_S3_SECRET_KEY"),
            region_name=os.environ.get("AWS_REGION")
            or os.environ.get("CF_S3_REGION")
            or "us-east-1",
        )

    def put_object(self, *, bucket: str, key: str, body: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)

    def get_object(self, *, bucket: str, key: str) -> bytes | None:
        try:
            obj = self._client.get_object(Bucket=bucket, Key=key)
        except Exception:  # noqa: BLE001
            return None
        raw = obj["Body"].read()
        return bytes(raw)

    def list_keys(self, *, bucket: str, prefix: str) -> list[str]:
        response = self._client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return [item["Key"] for item in response.get("Contents") or []]


class S3ArtifactStore:
    """Content-addressed artifact store over S3/MinIO."""

    def __init__(
        self,
        *,
        bucket: str | None = None,
        prefix: str = "artifacts/",
        client: ObjectClient | None = None,
    ) -> None:
        self.bucket = bucket or os.environ.get("CF_S3_BUCKET") or "continuity-forge"
        self.prefix = prefix
        self.client = client or Boto3ObjectClient()

    def put(self, candidate: ArtifactCandidate) -> str:
        body = candidate.model_dump(mode="json")
        digest = candidate.content_hash or content_hash(json.dumps(body, sort_keys=True))
        key = f"{self.prefix}{digest}.json"
        self.client.put_object(
            bucket=self.bucket,
            key=key,
            body=json.dumps(body, indent=2).encode("utf-8"),
            content_type="application/json",
        )
        return digest

    def get(self, content_hash_value: str) -> dict[str, Any] | None:
        key = f"{self.prefix}{content_hash_value}.json"
        raw = self.client.get_object(bucket=self.bucket, key=key)
        if raw is None:
            return None
        loaded = json.loads(raw.decode("utf-8"))
        if not isinstance(loaded, dict):
            return None
        return {str(k): v for k, v in loaded.items()}

    def list_hashes(self) -> list[str]:
        keys = self.client.list_keys(bucket=self.bucket, prefix=self.prefix)
        out: list[str] = []
        for key in keys:
            name = key.rsplit("/", 1)[-1]
            if name.endswith(".json"):
                out.append(name[: -len(".json")])
        return sorted(out)
