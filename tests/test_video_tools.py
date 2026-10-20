from pathlib import Path
from unittest.mock import patch
import pytest

from dropwheel.actions import load_all_actions
from dropwheel.actions.registry import applicable_actions
from dropwheel.actions.video_tools import extract_audio, make_gif, mute_video
from dropwheel.utils import _get_tick_wav, play_tick_sound


@pytest.fixture(autouse=True)
def init_actions():
    load_all_actions()


def test_video_actions_applicable(tmp_path: Path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"dummy mp4 data")

    actions = applicable_actions([video])
    action_ids = [a.id for a in actions]
    assert "mute_video" in action_ids
    assert "extract_audio" in action_ids
    assert "make_gif" in action_ids
    assert "file_properties" in action_ids


def test_tick_sound():
    wav = _get_tick_wav()
    assert isinstance(wav, bytes)
    assert len(wav) > 44  # Valid WAV header + samples
    # Ensure play_tick_sound executes safely without error
    play_tick_sound()


@patch("dropwheel.actions.video_tools.run_ffmpeg")
def test_mute_video_calls_ffmpeg(mock_run, tmp_path: Path):
    vid = tmp_path / "recording.mp4"
    vid.write_bytes(b"123")

    out = mute_video([vid])
    assert out.name == "recording_muted.mp4"
    mock_run.assert_called_once()
    args = mock_run.call_args[0]
    assert args[0] == vid
    assert args[1] == out
    assert args[2] == ["-c:v", "copy", "-an"]


@patch("dropwheel.actions.video_tools.run_ffmpeg")
def test_extract_audio_calls_ffmpeg(mock_run, tmp_path: Path):
    vid = tmp_path / "recording.mp4"
    vid.write_bytes(b"123")

    out = extract_audio([vid])
    assert out.name == "recording.mp3"
    mock_run.assert_called_once()
    args = mock_run.call_args[0]
    assert args[2] == ["-vn", "-q:a", "2"]


@patch("dropwheel.actions.video_tools.run_ffmpeg")
def test_make_gif_calls_ffmpeg(mock_run, tmp_path: Path):
    vid = tmp_path / "recording.mp4"
    vid.write_bytes(b"123")

    out = make_gif([vid])
    assert out.name == "recording.gif"
    mock_run.assert_called_once()
    args = mock_run.call_args[0]
    assert "-vf" in args[2]
