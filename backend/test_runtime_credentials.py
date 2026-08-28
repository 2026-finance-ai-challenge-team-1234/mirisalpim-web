"""Offline tests using fake credentials only; no GCP or database access."""

import contextlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from runtime_credentials import CredentialSetupError, main, prepare_credentials


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name) / "credentials.json"
        self.data = {
            "type": "service_account", "project_id": "test-project",
            "client_email": "test@example.invalid",
            "token_uri": "https://oauth2.googleapis.com/token",
            "private_key": "-----BEGIN PRIVATE KEY-----\nFAKE-TEST-ONLY\n-----END PRIVATE KEY-----\n",
        }

    def environment(self, raw):
        return patch.dict(os.environ, {
            "GCP_CREDENTIALS_JSON": raw,
            "GOOGLE_APPLICATION_CREDENTIALS": str(self.target),
        }, clear=True)

    def test_write_and_replace_without_logging_secret(self):
        self.target.write_text("old", encoding="utf-8")
        output = io.StringIO()
        with self.environment(json.dumps(self.data)), contextlib.redirect_stdout(output):
            prepare_credentials()
            self.assertNotIn("GCP_CREDENTIALS_JSON", os.environ)
            self.assertEqual(os.environ["GOOGLE_APPLICATION_CREDENTIALS"], str(self.target))
        self.assertEqual(json.loads(self.target.read_text()), self.data)
        self.assertNotIn("FAKE-TEST-ONLY", output.getvalue())
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o600)

    def test_unconfigured_is_optional(self):
        with patch.dict(os.environ, {}, clear=True):
            prepare_credentials()
        self.assertFalse(self.target.exists())

    def test_declared_but_empty_is_treated_as_unset(self):
        self.target.write_text("existing", encoding="utf-8")
        with self.environment("   "):
            prepare_credentials()
        self.assertEqual(self.target.read_text(), "existing")

    def test_existing_file_supported(self):
        self.target.write_text("existing", encoding="utf-8")
        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": str(self.target)}, clear=True):
            prepare_credentials()
        self.assertEqual(self.target.read_text(), "existing")

    def test_missing_file_fails(self):
        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": str(self.target)}, clear=True):
            with self.assertRaises(CredentialSetupError):
                prepare_credentials()

    def test_invalid_json_does_not_leak_input(self):
        with self.environment("PRIVATE-SECRET-INVALID"), self.assertRaises(CredentialSetupError) as result:
            prepare_credentials()
        self.assertNotIn("PRIVATE-SECRET", str(result.exception))
        self.assertFalse(self.target.exists())

    def test_invalid_fields_rejected(self):
        for field, value in [("project_id", ""), ("type", "other"),
                             ("token_uri", "[https://example](https://example)"),
                             ("private_key", "broken")]:
            with self.subTest(field=field):
                data = dict(self.data, **{field: value})
                with self.environment(json.dumps(data)), self.assertRaises(CredentialSetupError):
                    prepare_credentials()
                self.assertFalse(self.target.exists())


class StartupTests(unittest.TestCase):
    """인증 실패가 기동을 막지 않는지 확인한다."""

    def test_bad_credentials_still_start_the_application(self):
        errors = io.StringIO()
        argv = ["runtime_credentials.py", "/bin/sh", "-c", "true"]
        with patch.dict(os.environ, {"GCP_CREDENTIALS_JSON": "PRIVATE-SECRET-INVALID"}, clear=True), \
                patch("sys.argv", argv), \
                patch("runtime_credentials.os.execvp") as execvp, \
                contextlib.redirect_stderr(errors):
            main()
        execvp.assert_called_once_with("/bin/sh", ["/bin/sh", "-c", "true"])
        self.assertIn("WARNING", errors.getvalue())
        self.assertNotIn("PRIVATE-SECRET", errors.getvalue())

    def test_startup_command_is_required(self):
        errors = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), \
                patch("sys.argv", ["runtime_credentials.py"]), \
                contextlib.redirect_stderr(errors):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
