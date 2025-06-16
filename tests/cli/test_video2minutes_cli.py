import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

# Dynamically load the CLI module located outside of package directories
MODULE_PATH = Path(__file__).resolve().parents[2] / "src/cli/video2minutes.py"
spec = importlib.util.spec_from_file_location("video2minutes_cli", MODULE_PATH)
video2minutes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(video2minutes)


class TestCliUtilities:
    def test_sanitize_filename(self):
        assert video2minutes.sanitize_filename("Test File?!") == "Test_File__"
        assert video2minutes.sanitize_filename("  ") == "output"

    def test_derive_name(self):
        original = Path("some/dir/input.mp4")
        result = video2minutes.derive_name(original, "audio", ".mp3")
        assert result == original.with_stem("input_audio").with_suffix(".mp3")

    def test_ensure_dir(self, tmp_path):
        target = tmp_path / "created"
        assert not target.exists()
        video2minutes.ensure_dir(target)
        assert target.exists() and target.is_dir()

    def test_run_invokes_subprocess(self, monkeypatch):
        calls = []

        def fake_run(cmd, check=True):
            calls.append((cmd, check))

        monkeypatch.setattr(subprocess, "run", fake_run)
        video2minutes.run(["echo", "hi"], check=False)
        assert calls == [(["echo", "hi"], False)]


class TestCliParseArgs:
    def test_parse_args_success(self, monkeypatch):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "-i",
                "video.mp4",
                "--date",
                "2024-01-01",
                "--attendees",
                "A,B",
            ],
        )
        args = video2minutes.parse_args()
        assert args.input == Path("video.mp4")
        assert args.date == "2024-01-01"
        assert args.attendees == "A,B"

    def test_parse_args_missing_required(self, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["prog", "-i", "video.mp4", "--attendees", "A,B"]
        )
        with pytest.raises(SystemExit):
            video2minutes.parse_args()


def test_strip_code_fence():
    text = "```markdown\nhello\n```\n"
    assert video2minutes.strip_code_fence(text) == "hello"
