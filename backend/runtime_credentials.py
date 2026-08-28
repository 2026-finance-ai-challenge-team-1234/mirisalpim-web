"""Prepare runtime-only Google credentials before starting the application."""

import json
import os
from pathlib import Path
import sys
import tempfile


class CredentialSetupError(Exception):
    pass


def prepare_credentials():
    raw = os.environ.pop("GCP_CREDENTIALS_JSON", None)
    configured_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if raw is not None and not raw.strip():
        raw = None  # 선언만 하고 비워둔 변수는 미설정과 같게 본다.
    if raw is None:
        if configured_path and not Path(configured_path).is_file():
            raise CredentialSetupError("Configured Google credential file is missing.")
        return

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        raise CredentialSetupError("GCP_CREDENTIALS_JSON must contain valid JSON.") from None
    required = ("project_id", "private_key", "client_email", "token_uri")
    if not isinstance(data, dict) or data.get("type") != "service_account":
        raise CredentialSetupError("Google credentials must be a service_account object.")
    if any(not isinstance(data.get(key), str) or not data[key].strip() for key in required):
        raise CredentialSetupError("Google credentials have missing or empty required fields.")
    if data["token_uri"] != "https://oauth2.googleapis.com/token":
        raise CredentialSetupError("Google credentials must use the official OAuth token endpoint.")
    key = data["private_key"].strip()
    if not (key.startswith("-----BEGIN PRIVATE KEY-----\n")
            and key.endswith("\n-----END PRIVATE KEY-----")):
        raise CredentialSetupError("Google private key must retain its original PEM line breaks.")

    target = Path(configured_path or "/tmp/gcp-credentials.json")
    if not target.is_absolute():
        raise CredentialSetupError("Google credential file path must be absolute.")
    temporary = None
    try:
        # mkstemp creates the file with mode 0600 on Linux. Atomic replacement
        # avoids following a pre-existing symlink at the destination.
        descriptor, temporary = tempfile.mkstemp(prefix=".gcp-", dir=target.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        os.replace(temporary, target)
        temporary = None
    except OSError:
        raise CredentialSetupError("Cannot create the Google credential file; check its parent directory and permissions.") from None
    finally:
        if temporary is not None:
            os.unlink(temporary)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(target)
    print("GCP credential file prepared (contents hidden).", flush=True)


def main():
    # ⚠️ 인증 준비 실패가 기동을 막지 않게 한다. GCP 자격증명은 음성(STT/TTS)에만
    # 쓰이는 선택적 의존이라, 값 하나가 잘못됐다고 서비스 전체가 안 뜨는 것보다
    # 음성 없이 뜨는 편이 낫다. Dockerfile 의 seed_scenarios 와 같은 방침이다.
    try:
        prepare_credentials()
    except CredentialSetupError as error:
        print(f"WARNING: GCP 인증 준비 실패 - 음성 기능 없이 기동합니다: {error}",
              file=sys.stderr, flush=True)
    if len(sys.argv) < 2:
        print("A startup command is required.", file=sys.stderr)
        return 1
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
