from main import (
    clip,
    extract_json,
    format_llm_error,
    grade,
    llm_model,
    parse_level,
    skill_response,
    split_answers,
)


def test_format_llm_error_redacts_key():
    class E(Exception):
        status_code = 401

    msg = format_llm_error(E("Incorrect API key sk-abc123xyz"))
    assert "401" in msg
    assert "sk-abc123xyz" not in msg
    assert "[redacted]" in msg


BLANK = {"ko": "회사", "jp": "会社", "reading": "かいしゃ"}


def test_t08_grade_jp_and_reading_and_normalize():
    left, wrong = grade(["会社"], [BLANK])
    assert left == []
    assert wrong == []

    left, wrong = grade(["かいしゃ"], [dict(BLANK)])
    assert left == []

    left, wrong = grade([" 会社 "], [dict(BLANK)])
    assert left == []

    left, wrong = grade(split_answers("会社, とんかつ"), [dict(BLANK)])
    assert left == []
    assert wrong == ["とんかつ"]

    left, wrong = grade(split_answers("学校"), [dict(BLANK)])
    assert len(left) == 1
    assert wrong == ["学校"]


def test_t09_clip_and_skill_limits():
    assert len(clip("a" * 1000)) == 1000
    clipped = clip("a" * 1001)
    assert len(clipped) == 1000
    assert clipped.endswith("…")

    body = skill_response(["one", "two", "three", "four"], ["c"] * 12)
    assert body["version"] == "2.0"
    assert len(body["template"]["outputs"]) == 3
    assert len(body["template"]["quickReplies"]) == 10
    for o in body["template"]["outputs"]:
        assert len(o["simpleText"]["text"]) <= 1000


def test_t08_parse_level_and_extract_json():
    assert parse_level("Lv.2") == 2
    assert parse_level("레벨 3") == 3
    assert parse_level("일기") is None
    data = extract_json('```json\n{"level": 1}\n```')
    assert data["level"] == 1
    data = extract_json('prefix {"cloze": "x"} suffix')
    assert data["cloze"] == "x"


def test_llm_model_empty_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "")
    assert llm_model() == "gpt-4o-mini"
    monkeypatch.setenv("LLM_MODEL", "  ")
    assert llm_model() == "gpt-4o-mini"
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    assert llm_model() == "gpt-4o"
