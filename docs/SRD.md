# SRD — 시스템 요구사항

## 구조

단일 [`main.py`](../main.py): FastAPI, 목업 HTML, LLM, 메모리 세션(빈칸 채점).

## 웹 목업

- `GET /` → `HTMLResponse` (인라인 CSS/JS)
- 카카오톡 채팅방: 헤더 `#FEE500`, 봇 왼쪽, 사용자 오른쪽, 하단 입력
- JS가 Skill Payload로 `POST /api/chat`

## 통신 (카카오 Skill)

요청에서 읽는 필드: `userRequest.utterance`, 있으면 `userRequest.user.id` (세션 키).

응답: `version: "2.0"`, `template.outputs[].simpleText.text` (1~3개, 각 1000자), `quickReplies` (10개 이하).

- 퍼즐 말풍선: 레벨 + 빈칸 한국어 (정답 일본어는 본문에 넣지 않음)
- 힌트 말풍선: 빈칸 개수, 입력 방법
- 칩: 일본어 선택지, `정답 보기`, `다른 일기`, `Lv.1` … `Lv.5`

## 대화 상태 (프로세스 메모리)

사용자 id별로 `{level, remaining, reveal, options}`를 둔다. 재시작되면 사라진다. DB 없음.

- 한글 일기가 길면 → 새 퍼즐 생성, 세션 갱신
- 세션에 남은 빈칸이 있고 입력이 일본어·선택지·쉼표 나열이면 → 채점
- 모두 맞히면 혼합 문장 공개 후 remaining 비움

## LLM

OpenAI SDK. `OPENAI_API_KEY`, 선택 `OPENAI_BASE_URL`, `LLM_MODEL`(기본 `gpt-4o-mini`).

모델은 **JSON만** 반환한다: `level`, `cloze`, `blanks[{ko,jp,reading}]`, `reveal`, `distractors[]`. 원문을 통번역하지 않는다.
