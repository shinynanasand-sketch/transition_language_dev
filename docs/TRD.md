# TRD — 기술 요구사항

## 환경변수

| 이름 | 필수 | 설명 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 예 | API 키 |
| `OPENAI_BASE_URL` | 아니오 | 호환 게이트웨이 |
| `LLM_MODEL` | 아니오 | 기본 `gpt-4o-mini` |

## GET `/`

카카오톡 목업. Skill Payload POST, `simpleText` 말풍선, `quickReplies` 칩.

## POST `/api/chat`

1. `utterance` 없음 → 안내 (일기를 보내 빈칸을 채우라는 컨셉)
2. `다른 일기` → 세션 퍼즐만 지우고 안내
3. `Lv.1`~`Lv.5` / `레벨 n` → 레벨 저장 후 안내
4. `정답 보기` → 세션 `reveal` 공개
5. 활성 세션 + 답 후보 → 정규화 후 remaining과 대조. 맞으면 제거. 비면 reveal 말풍선
6. 그 외(일기) → LLM으로 퍼즐 JSON 생성, 빈칸 말풍선 + 선택지 칩
7. LLM 실패여도 Skill JSON, HTTP 200

## 레벨별 빈칸 지시

- 1: 명사만. 한국어 골격 유지
- 2: 동사·형용사 활용형
- 3: 짧은 일본어 구
- 4: 문장 앞/뒤 일부
- 5: 빈칸 없이 “일본어로 전체를 쓰세요” + 모범 답 `reveal`

## LLM JSON

```json
{
  "level": 1,
  "cloze": "오늘 [　　]에서 일이 별로 없었다.",
  "blanks": [{"ko": "회사", "jp": "会社", "reading": "かいしゃ"}],
  "reveal": "오늘 会社(かいしゃ)에서 일이 별로 없었다.",
  "distractors": ["学校"]
}
```

파싱 실패 시 원문을 한 말풍선으로 보여 주되, 가능하면 JSON 블록만 추출한다.

## 채점

공백·쉼표·슬래시로 여러 답을 나눈다. `jp` 또는 `reading`이 같으면 정답. 대소문자 무시.

## 실행

```bash
uv sync
uv run uvicorn main:app --reload --port 8000
```
