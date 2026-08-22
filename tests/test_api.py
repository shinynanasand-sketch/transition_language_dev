from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from main import SESSIONS, app

PUZZLE = {
    "cloze": "오늘 [　　]에서 일이 별로 없었다.",
    "remaining": [{"ko": "회사", "jp": "会社", "reading": "かいしゃ"}],
    "reveal": "오늘 会社(かいしゃ)에서 일이 별로 없었다.",
    "options": ["会社", "学校"],
}


@pytest.fixture
def client(monkeypatch):
    SESSIONS.clear()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    return TestClient(app)


def payload(utterance: str, uid: str = "u1") -> dict:
    return {
        "userRequest": {
            "utterance": utterance,
            "user": {"id": uid, "type": "botUserKey"},
        }
    }


def assert_skill(resp):
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "2.0"
    outputs = data["template"]["outputs"]
    assert 1 <= len(outputs) <= 3
    for o in outputs:
        assert len(o["simpleText"]["text"]) <= 1000
    replies = data["template"].get("quickReplies") or []
    assert len(replies) <= 10
    return data


def texts(data: dict) -> str:
    return "\n".join(o["simpleText"]["text"] for o in data["template"]["outputs"])


def labels(data: dict) -> list[str]:
    return [r["label"] for r in data["template"].get("quickReplies") or []]


def test_t01_empty_utterance(client):
    data = assert_skill(client.post("/api/chat", json=payload("")))
    body = texts(data)
    assert "일기" in body or "빈칸" in body or "한국어" in body


def test_t02_clear_diary_resets_remaining(client):
    SESSIONS["u1"] = {
        "level": 1,
        "remaining": [{"ko": "회사", "jp": "会社", "reading": "かいしゃ"}],
        "reveal": "x",
        "options": ["会社"],
    }
    assert_skill(client.post("/api/chat", json=payload("다른 일기")))
    assert SESSIONS["u1"]["remaining"] == []


def test_t03_level_commands(client):
    data = assert_skill(client.post("/api/chat", json=payload("Lv.2")))
    assert "Lv.2" in texts(data)
    assert SESSIONS["u1"]["level"] == 2
    data = assert_skill(client.post("/api/chat", json=payload("레벨 3")))
    assert "Lv.3" in texts(data)
    assert SESSIONS["u1"]["level"] == 3


def test_t04_show_answer(client):
    SESSIONS["u1"] = {
        "level": 1,
        "remaining": [{"jp": "会社", "reading": "かいしゃ", "ko": "회사"}],
        "reveal": "오늘 会社(かいしゃ)에서 일이 별로 없었다.",
        "options": ["会社"],
    }
    data = assert_skill(client.post("/api/chat", json=payload("정답 보기")))
    assert "会社(かいしゃ)" in texts(data)


def test_t10_llm_failure_still_skill(client):
    with patch.object(main, "puzzle_from_llm", side_effect=RuntimeError("401 invalid_api_key")):
        data = assert_skill(
            client.post("/api/chat", json=payload("오늘 회사에서 일이 별로 없었다. 점심을 먹었다."))
        )
    body = texts(data)
    assert "빈칸을 만들지 못했습니다" in body
    assert "401" in body
    assert "데모" not in body
    assert "sk-" not in body


def test_blank_api_key_uses_demo(monkeypatch):
    SESSIONS.clear()
    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    client = TestClient(app)
    data = assert_skill(
        client.post("/api/chat", json=payload("오늘 회사에서 일이 별로 없었다. 점심으로 돈까스를 먹었다."))
    )
    assert "데모" in texts(data)
    assert "[　　]" in texts(data)


def test_t11_mockup_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "#FEE500" in resp.text
    assert '"demo": false' in resp.text


def test_mockup_autosends_demo_diary_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert '"demo": true' in resp.text
    assert "오늘 회사에서 일이 별로 없었다" in resp.text
    assert "cfg.diary" in resp.text


def test_t12_invalid_json_body(client):
    data = assert_skill(
        client.post("/api/chat", content=b"not-json", headers={"content-type": "application/json"})
    )
    assert data["version"] == "2.0"


def test_t05_diary_mock_puzzle_no_answer_in_cloze(client):
    with patch.object(main, "puzzle_from_llm", return_value=deepcopy(PUZZLE)):
        data = assert_skill(
            client.post("/api/chat", json=payload("오늘 회사에서 일이 별로 없었다. 점심으로 돈까스를 먹었다."))
        )
    body = texts(data)
    assert "[　　]" in body
    # cloze bubble should not contain the answer kanji before user grades
    first = data["template"]["outputs"][0]["simpleText"]["text"]
    assert "会社" not in first
    assert "会社" in labels(data)
    assert "学校" in labels(data)


def test_t06_correct_answer_reveals_mix(client):
    with patch.object(main, "puzzle_from_llm", return_value=deepcopy(PUZZLE)):
        assert_skill(
            client.post("/api/chat", json=payload("오늘 회사에서 일이 별로 없었다. 점심으로 돈까스를 먹었다."))
        )
    data = assert_skill(client.post("/api/chat", json=payload("会社")))
    assert "会社(かいしゃ)" in texts(data)


def test_t07_wrong_answer_keeps_remaining(client):
    with patch.object(main, "puzzle_from_llm", return_value=deepcopy(PUZZLE)):
        assert_skill(
            client.post("/api/chat", json=payload("오늘 회사에서 일이 별로 없었다. 점심으로 돈까스를 먹었다."))
        )
    data = assert_skill(client.post("/api/chat", json=payload("学校")))
    assert "남은 빈칸" in texts(data)
    assert len(SESSIONS["u1"]["remaining"]) == 1


def test_demo_puzzle_without_api_key(monkeypatch):
    SESSIONS.clear()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)
    data = assert_skill(
        client.post("/api/chat", json=payload("오늘 회사에서 일이 별로 없었다. 점심으로 돈까스를 먹었다."))
    )
    assert "[　　]" in texts(data)
    assert "会社" in labels(data)
    assert "데모" in texts(data)

