"""Unit tests for the version checker service."""

import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from backend.services.version_checker import (
    get_all_npm_versions,
    get_latest_npm_version,
    get_npm_metadata,
    install_claude_code_version,
)


class TestGetAllNpmVersions(unittest.TestCase):
    """Tests for get_all_npm_versions."""

    @patch("backend.services.version_checker.subprocess.run")
    def test_returns_sorted_versions(self, mock_run: MagicMock) -> None:
        versions = ["0.1.0", "1.0.0", "0.2.0", "1.1.0"]
        mock_run.return_value = MagicMock(
            stdout=json.dumps(versions),
            returncode=0,
        )
        mock_run.return_value.check_returncode = MagicMock()

        result = get_all_npm_versions()

        self.assertEqual(result, ["0.1.0", "0.2.0", "1.0.0", "1.1.0"])
        mock_run.assert_called_once_with(
            ["npm", "view", "@anthropic-ai/claude-code", "versions", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

    @patch("backend.services.version_checker.subprocess.run")
    def test_handles_single_version_string(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout=json.dumps("1.0.0"),
            returncode=0,
        )
        mock_run.return_value.check_returncode = MagicMock()

        result = get_all_npm_versions()

        self.assertEqual(result, ["1.0.0"])

    @patch("backend.services.version_checker.subprocess.run")
    def test_prerelease_sorts_before_release(self, mock_run: MagicMock) -> None:
        versions = ["1.0.0", "1.0.0-beta.1", "0.9.0"]
        mock_run.return_value = MagicMock(
            stdout=json.dumps(versions),
            returncode=0,
        )
        mock_run.return_value.check_returncode = MagicMock()

        result = get_all_npm_versions()

        self.assertEqual(result, ["0.9.0", "1.0.0-beta.1", "1.0.0"])

    @patch("backend.services.version_checker.subprocess.run")
    def test_raises_on_npm_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1)
        mock_run.return_value.check_returncode = MagicMock(
            side_effect=subprocess.CalledProcessError(1, "npm")
        )

        with self.assertRaises(subprocess.CalledProcessError):
            get_all_npm_versions()


class TestGetLatestNpmVersion(unittest.TestCase):
    """Tests for get_latest_npm_version."""

    @patch("backend.services.version_checker.get_all_npm_versions")
    def test_returns_last_version(self, mock_get_all: MagicMock) -> None:
        mock_get_all.return_value = ["0.1.0", "0.2.0", "1.0.0"]

        result = get_latest_npm_version()

        self.assertEqual(result, "1.0.0")


class TestGetNpmMetadata(unittest.TestCase):
    """Tests for get_npm_metadata."""

    @patch("backend.services.version_checker.subprocess.run")
    def test_returns_parsed_metadata(self, mock_run: MagicMock) -> None:
        metadata = {"name": "@anthropic-ai/claude-code", "version": "1.0.0"}
        mock_run.return_value = MagicMock(
            stdout=json.dumps(metadata),
            returncode=0,
        )
        mock_run.return_value.check_returncode = MagicMock()

        result = get_npm_metadata("1.0.0")

        self.assertEqual(result, metadata)
        mock_run.assert_called_once_with(
            ["npm", "view", "@anthropic-ai/claude-code@1.0.0", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

    @patch("backend.services.version_checker.subprocess.run")
    def test_raises_on_npm_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1)
        mock_run.return_value.check_returncode = MagicMock(
            side_effect=subprocess.CalledProcessError(1, "npm")
        )

        with self.assertRaises(subprocess.CalledProcessError):
            get_npm_metadata("99.99.99")


class TestInstallClaudeCodeVersion(unittest.TestCase):
    """Tests for install_claude_code_version."""

    @patch("backend.services.version_checker.subprocess.run")
    def test_returns_cli_js_path(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        mock_run.return_value.check_returncode = MagicMock()

        result = install_claude_code_version("1.0.0", "/tmp/cc")

        self.assertEqual(
            result,
            "/tmp/cc/node_modules/@anthropic-ai/claude-code/cli.js",
        )
        mock_run.assert_called_once_with(
            [
                "npm",
                "install",
                "@anthropic-ai/claude-code@1.0.0",
                "--prefix",
                "/tmp/cc",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

    @patch("backend.services.version_checker.subprocess.run")
    def test_raises_on_install_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1)
        mock_run.return_value.check_returncode = MagicMock(
            side_effect=subprocess.CalledProcessError(1, "npm")
        )

        with self.assertRaises(subprocess.CalledProcessError):
            install_claude_code_version("1.0.0", "/tmp/cc")


if __name__ == "__main__":
    unittest.main()
