# TDD — 오류·시나리오 테스트 명세

PRD/SRD/TRD를 자동 테스트로 고정한다. LLM은 모킹한다. 실행: `uv run pytest -q`

모든 API 응답 공통 계약: HTTP 200, `version == "2.0"`, `template.outputs` 길이 1~3, 각 `simpleText.text` ≤ 1000자, `quickReplies` ≤ 10.

| ID | 출처 | 입력 | 기대 | 통과 기준 |
| --- | --- | --- | --- | --- |
| T01 | TRD | `utterance` 없음 또는 `""` | 안내 말풍선 | Skill 계약, 본문에 빈칸 채우기/일기 안내 |
| T02 | TRD | 세션에 remaining 있음 → `다른 일기` | 퍼즐 초기화 | `SESSIONS[uid].remaining == []` |
| T03 | TRD | `Lv.2`, `레벨 3` | 레벨 저장 | 본문에 `Lv.2`/`Lv.3`, `sess.level` 일치 |
| T04 | TRD | reveal 있는 세션 → `정답 보기` | 혼합 문장 공개 | outputs에 reveal 문자열 |
| T05 | PRD | 긴 한글 일기 + mock 퍼즐 | 빈칸 한국어, 칩에 일본어 | cloze에 `会社` 없음, 칩에 `会社`·`学校` |
| T06 | PRD | T05 다음 `会社` | 정답 처리 | 본문에 reveal `会社(かいしゃ)` |
| T07 | TRD | T05 다음 `学校` | 오답 | `남은 빈칸`, remaining 길이 유지 |
| T08 | TRD | `grade`: `会社`, `かいしゃ`, 공백 무시 | 정답 | remaining 비움 |
| T09 | SRD | `clip` 1001자, texts 4개, chips 12개 | 제한 준수 | 1000자, outputs 3, replies 10 |
| T10 | TRD | mock `puzzle_from_llm` 예외 | 폴백 말풍선 | 200 + Skill JSON |
| T11 | SRD | `GET /` | 목업 HTML | `text/html`, `#FEE500` |
| T12 | SRD | POST 본문이 JSON 아님 | Skill 폴백 | 200 + `version` 2.0 |
| T13 | PRD | `OPENAI_API_KEY` 없음 + 일기 | 고정 데모 퍼즐 | cloze 빈칸, 칩 `会社`, 본문에 데모 안내 |

임의 일기에서 빈칸을 새로 뽑을 때만 LLM(키)이 필요하다. 예시 명사 빈칸만이면 키 없이 `DEMO_PUZZLE`을 쓴다.

## 고정 퍼즐 (T05–T07)

```json
{
  "cloze": "오늘 [　　]에서 일이 별로 없었다.",
  "remaining": [{"ko": "회사", "jp": "会社", "reading": "かいしゃ"}],
  "reveal": "오늘 会社(かいしゃ)에서 일이 별로 없었다.",
  "options": ["会社", "学校"]
}
```

## 실행 기록

- 명령: `uv run pytest -q`
- 결과: `13 passed in 1.34s` (T01–T12)
- 일자: 2026-08-22
