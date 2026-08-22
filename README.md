# transition_language_dev

**바로 열어보기:** [https://shinynanasand-sketch.github.io/transition_language_dev/](https://shinynanasand-sketch.github.io/transition_language_dev/)

키 없이 카카오톡 목업 + 예시 일기 빈칸을 브라우저에서 보여 줍니다. (GitHub Pages 정적 데모)

한국어 일기에 일본어를 조금씩 넣는 빈칸 학습 챗봇 MVP입니다.

## GitHub에서 테스트

1. **공개 URL (화면)**  
   https://shinynanasand-sketch.github.io/transition_language_dev/

2. **Actions (자동 pytest)**  
   [Actions](https://github.com/shinynanasand-sketch/transition_language_dev/actions)

3. **Codespaces (FastAPI 전체)**  
   **Code → Codespaces** 후 `uv run uvicorn main:app --host 0.0.0.0 --port 8000`

## 로컬 실행

```bash
uv sync --dev
uv run pytest -q
uv run uvicorn main:app --reload --port 8000
```

브라우저: http://127.0.0.1:8000

임의 일기에서 빈칸을 새로 만들려면 `.env`에 `OPENAI_API_KEY`를 넣습니다. 키는 커밋하지 마세요.
