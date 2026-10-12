"""The pilot event log (HLD section 11, pilot E5): opt-in, edge-only, never free text.

`main.PILOT_LOG_ENABLED` is read from the environment ONCE at import time, so these tests
monkeypatch the module attribute directly rather than `os.environ` -- changing the environment
after import would have no effect on behaviour the module already captured.
"""

import json

import pytest
from fastapi.testclient import TestClient
from src.api import main

ACT = "/api/act"
PARSE = "/api/parse"


@pytest.fixture
def client():
    with TestClient(main.app) as ready:
        yield ready


@pytest.fixture
def board(client) -> dict:
    facts = client.post("/api/next", json={}).json()["state"]
    answer = client.post(ACT, json={"state": facts, "action": {"type": "confirm_facts"}})
    return answer.json()["state"]


def test_logging_is_off_by_default(client, board, monkeypatch, tmp_path) -> None:
    # PILOT_LOG_ENABLED is left at whatever the module captured at import -- which must be False
    # in any environment that did not set PROOFPILOT_PILOT_LOG, including CI and a plain dev run.
    monkeypatch.setattr(main, "PILOT_LOG_DIR", tmp_path)
    client.post(
        ACT,
        json={"state": board, "action": {"type": "hint", "level": 1}},
        headers={"X-Pilot-Id": "P1"},
    )
    assert not (tmp_path / "pilot.jsonl").exists(), "PROOFPILOT_PILOT_LOG defaults to off"


def test_one_line_per_action_when_enabled(client, board, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main, "PILOT_LOG_ENABLED", True)
    monkeypatch.setattr(main, "PILOT_LOG_DIR", tmp_path)
    client.post(
        ACT,
        json={"state": board, "action": {"type": "hint", "level": 1}},
        headers={"X-Pilot-Id": "P7"},
    )
    lines = (tmp_path / "pilot.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["pilot_id"] == "P7"
    assert row["action"] == "hint"
    assert set(row) == {"pilot_id", "timestamp", "action", "code", "hint_level", "stage"}


def test_a_second_action_appends_a_second_line(client, board, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main, "PILOT_LOG_ENABLED", True)
    monkeypatch.setattr(main, "PILOT_LOG_DIR", tmp_path)
    headers = {"X-Pilot-Id": "P7"}
    client.post(ACT, json={"state": board, "action": {"type": "hint", "level": 1}}, headers=headers)
    client.post(ACT, json={"state": board, "action": {"type": "hint", "level": 1}}, headers=headers)
    lines = (tmp_path / "pilot.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_no_pilot_id_header_means_no_log_even_when_enabled(
    client, board, monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(main, "PILOT_LOG_ENABLED", True)
    monkeypatch.setattr(main, "PILOT_LOG_DIR", tmp_path)
    client.post(ACT, json={"state": board, "action": {"type": "hint", "level": 1}})
    assert not (tmp_path / "pilot.jsonl").exists()


def test_no_free_text_is_ever_recorded(client, board, monkeypatch, tmp_path) -> None:
    """The exact rule: no paragraph text, no names -- only the six named fields."""
    monkeypatch.setattr(main, "PILOT_LOG_ENABLED", True)
    monkeypatch.setattr(main, "PILOT_LOG_DIR", tmp_path)
    client.post(
        ACT,
        json={"state": board, "action": {"type": "hint", "level": 1}},
        headers={"X-Pilot-Id": "P3"},
    )
    line = (tmp_path / "pilot.jsonl").read_text(encoding="utf-8")
    assert board["paragraph"] not in line
    assert board["conclusion"] not in line


def test_parse_also_logs_when_enabled(client, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main, "PILOT_LOG_ENABLED", True)
    monkeypatch.setattr(main, "PILOT_LOG_DIR", tmp_path)
    client.post(
        PARSE,
        json={
            "paragraph": "If it rains then the match is cancelled. It rains.",
            "conclusion": "The match is cancelled.",
        },
        headers={"X-Pilot-Id": "P2"},
    )
    lines = (tmp_path / "pilot.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["action"] == "parse"
    assert row["code"] == "ENTAILED"
