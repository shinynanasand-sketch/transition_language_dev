# transition_language_dev

한국어 일기에 일본어를 조금씩 넣는 빈칸 학습 챗봇 MVP입니다. 카카오톡 목업 UI로 브라우저에서 시험합니다.

## GitHub에서 테스트

1. **Actions (자동)**  
   푸시마다 [Actions](https://github.com/shinynanasand-sketch/transition_language_dev/actions)에서 `pytest`가 돌아갑니다. **Actions → CI → Run workflow**로 수동 실행도 됩니다. OpenAI 키 없이 데모 경로를 검증합니다.

2. **Codespaces (화면 목업)**  
   **Code → Codespaces → Create codespace** 후 터미널:

   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

   포트 8000을 열면 목업이 보입니다. 키가 없으면 예시 일기가 자동 전송됩니다.

## 로컬 실행

```bash
uv sync --dev
uv run pytest -q
uv run uvicorn main:app --reload --port 8000
```

브라우저: http://127.0.0.1:8000

임의 일기에서 빈칸을 새로 만들려면 `.env`에 `OPENAI_API_KEY`를 넣습니다. 키는 커밋하지 마세요.
