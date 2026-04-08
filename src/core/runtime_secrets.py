"""Bootstrap environment from AWS Secrets Manager before pydantic Settings loads (PRC-A3).

Set ``AWS_SECRETS_MANAGER_SECRET_ID`` to a secret whose **SecretString** is a JSON object
``{"ENV_VAR_NAME": "value", ...}``. Keys are merged into ``os.environ`` only where the
target variable is unset or empty (non-destructive; K8s/compose can still override).

Skipped when ``TESTING=1`` or when ``AWS_SECRETS_MANAGER_SECRET_ID`` is empty.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

_BOOTSTRAP_DONE = False


def reset_runtime_secrets_bootstrap_for_tests() -> None:
    """Allow a second bootstrap in the same interpreter (unit tests only)."""
    global _BOOTSTRAP_DONE
    _BOOTSTRAP_DONE = False


def apply_runtime_secrets_to_environ() -> None:
    """Fetch one JSON secret from AWS Secrets Manager and merge into the environment."""
    global _BOOTSTRAP_DONE
    if _BOOTSTRAP_DONE:
        return
    _BOOTSTRAP_DONE = True

    if os.environ.get("TESTING") == "1":
        return

    secret_id = (os.environ.get("AWS_SECRETS_MANAGER_SECRET_ID") or "").strip()
    if not secret_id:
        return

    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        logger.warning("boto3 unavailable: cannot load AWS_SECRETS_MANAGER_SECRET_ID=%s", secret_id)
        return

    region = (os.environ.get("AWS_SECRETS_MANAGER_REGION") or os.environ.get("AWS_REGION") or "").strip() or None
    client = boto3.client("secretsmanager", region_name=region) if region else boto3.client("secretsmanager")

    try:
        resp = client.get_secret_value(SecretId=secret_id)
    except ClientError:
        logger.exception("Secrets Manager get_secret_value failed for %s", secret_id)
        raise RuntimeError(
            f"AWS Secrets Manager bootstrap failed for {secret_id!r}. "
            "Fix IAM/network or unset AWS_SECRETS_MANAGER_SECRET_ID for local boot."
        ) from None

    raw = resp.get("SecretString") or ""
    if not str(raw).strip():
        logger.warning("Secrets Manager %s: empty SecretString", secret_id)
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Secret {secret_id!r} must be a JSON object (string keys).") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"Secret {secret_id!r} JSON root must be an object, not {type(data).__name__}.")

    injected = 0
    for key, val in data.items():
        if not isinstance(key, str) or not key.strip():
            continue
        existing = os.environ.get(key)
        if existing is not None and str(existing).strip():
            continue
        if val is None:
            continue
        os.environ[key] = val if isinstance(val, str) else str(val)
        injected += 1

    logger.info(
        "runtime_secrets: merged %s keys from AWS Secrets Manager %s (skipped non-empty env)",
        injected,
        secret_id,
    )
