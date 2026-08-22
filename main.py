import json
import os
import re
from copy import deepcopy
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from openai import OpenAI

load_dotenv(override=True)

TEXT_LIMIT = 1000
DEFAULT_MODEL = "gpt-4o-mini"

LEVEL_HELP = {
    1: "명사만 일본어로 채웁니다. 한국어는 그대로 둡니다.",
    2: "동사·형용사 활용을 빈칸에 넣습니다.",
    3: "짧은 일본어 구를 넣습니다.",
    4: "문장 일부를 일본어로 바꿉니다.",
    5: "문장 전체를 일본어로 적어 보세요.",
}

# 키 없이 PRD 예시만 돌릴 때 쓰는 고정 퍼즐 (통번역 아님)
DEMO_PUZZLE = {
    "cloze": (
        "오늘 [　　]에서 일이 별로 없었다.\n"
        "점심으로 [　　]를 먹었다.\n"
        "집에 와서 [　　]을 했다."
    ),
    "remaining": [
        {"ko": "회사", "jp": "会社", "reading": "かいしゃ"},
        {"ko": "돈까스", "jp": "とんかつ", "reading": "とんかつ"},
        {"ko": "게임", "jp": "ゲーム", "reading": "ゲーム"},
    ],
    "reveal": (
        "오늘 会社(かいしゃ)에서 일이 별로 없었다.\n"
        "점심으로 とんかつ를 먹었다.\n"
        "집에 와서 ゲーム을 했다."
    ),
    "options": ["会社", "とんかつ", "ゲーム", "学校", "ラーメン"],
}

DEMO_DIARY = (
    "오늘 회사에서 일이 별로 없었다.\n"
    "점심으로 돈까스를 먹었다.\n"
    "집에 와서 게임을 했다."
)

SYSTEM_PROMPT = """당신은 통역가가 아닙니다. 한국어 일기를 전부 일본어로 바꾸지 마세요.
목표는 한국어 문장 속에 일본어를 조금씩 침투시키는 빈칸 학습입니다.

사용자 메시지 첫 줄: LEVEL=n (1~5)
나머지: 한국어 일기/할 일.

레벨:
1 명사만 빈칸. 예: 오늘 [　　]에서 일이 별로 없었다.
2 동사/형용사. 예: 오늘 회사에서 일이 별로 [　　].
3 짧은 표현. 예: 오늘 회사에서 [　　].
4 문장 일부. 예: [　　] 일이 별로 없었다.
5 빈칸 없이 cloze에 원문을 두고, reveal에 초급 일본어 전체 번역. blanks는 모범 문장 1개.

규칙:
- 원문 문장 순서를 유지한다.
- 빈칸은 [　　] 만 쓴다. 한 문장에 빈칸은 가급적 1개.
- blanks는 빈칸 등장 순서와 같게 2~5개 (Lv.5는 1개).
- reveal는 원문 한국어를 유지하고 빈칸 자리에 일본어를 넣는다. 한자면 바로 뒤에 (읽기).
- distractors는 오답 일본어 2~4개 (정답과 겹치지 않음).
- JSON만 출력. 설명 금지.

스키마:
{"level":1,"cloze":"...","blanks":[{"ko":"회사","jp":"会社","reading":"かいしゃ"}],"reveal":"...","distractors":["学校"]}
"""

MOCKUP_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>초급일본어</title>
  <style>
    :root { --kakao: #FEE500; --bg: #b2c7d9; --text: #191919; }
    * { box-sizing: border-box; }
    html, body { margin: 0; height: 100%; font-family: "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; }
    body { background: #3c3c3c; display: flex; align-items: center; justify-content: center; }
    .phone {
      width: 390px; max-width: 100%; height: 720px; max-height: 100vh;
      background: var(--bg); display: flex; flex-direction: column;
      border-radius: 12px; overflow: hidden; box-shadow: 0 12px 40px rgba(0,0,0,.35);
    }
    header {
      background: var(--kakao); color: var(--text); padding: 14px 16px;
      font-weight: 700; font-size: 16px; display: flex; align-items: center; gap: 8px;
    }
    header .dot { width: 8px; height: 8px; background: #3c1e1e; border-radius: 50%; }
    #log {
      flex: 1; overflow-y: auto; padding: 12px 10px; display: flex; flex-direction: column; gap: 8px;
    }
    .row { display: flex; }
    .row.me { justify-content: flex-end; }
    .row.bot { justify-content: flex-start; }
    .bubble {
      max-width: 78%; white-space: pre-wrap; word-break: break-word;
      padding: 10px 12px; border-radius: 16px; font-size: 14px; line-height: 1.45;
    }
    .me .bubble { background: var(--kakao); color: var(--text); border-top-right-radius: 4px; }
    .bot .bubble { background: #fff; color: var(--text); border-top-left-radius: 4px; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 10px 8px; }
    .chip {
      background: #fff; border: 1px solid #d4d4d4; border-radius: 16px;
      padding: 6px 12px; font-size: 12px; cursor: pointer;
    }
    .composer {
      background: #fff; display: flex; gap: 8px; padding: 10px;
      border-top: 1px solid #d0d0d0;
    }
    .composer input {
      flex: 1; border: none; outline: none; font-size: 14px; padding: 8px;
    }
    .composer button {
      background: var(--kakao); border: none; border-radius: 8px;
      padding: 8px 14px; font-weight: 700; cursor: pointer;
    }
    .hint { font-size: 12px; color: #4a5a68; text-align: center; padding: 4px 0 8px; }
  </style>
</head>
<body>
  <div class="phone">
    <header><span class="dot"></span> 초급일본어</header>
    <div id="log"></div>
    <div class="chips" id="chips"></div>
    <div class="hint">한국어 일기를 보내면 빈칸만 일본어로 채웁니다</div>
    <form class="composer" id="form">
      <input id="text" autocomplete="off" placeholder="일기 또는 일본어 답" />
      <button type="submit">전송</button>
    </form>
  </div>
  <script>
    const log = document.getElementById("log");
    const chips = document.getElementById("chips");
    const form = document.getElementById("form");
    const input = document.getElementById("text");

    function addBubble(text, who) {
      const row = document.createElement("div");
      row.className = "row " + who;
      const b = document.createElement("div");
      b.className = "bubble";
      b.textContent = text;
      row.appendChild(b);
      log.appendChild(row);
      log.scrollTop = log.scrollHeight;
    }

    function renderChips(replies) {
      chips.innerHTML = "";
      (replies || []).forEach((r) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "chip";
        const label = r.label || r.messageText || "";
        btn.textContent = label;
        btn.onclick = () => send(r.messageText || label);
        chips.appendChild(btn);
      });
    }

    async function send(utterance) {
      const text = (utterance || "").trim();
      if (!text) return;
      addBubble(text, "me");
      input.value = "";
      const payload = {
        intent: { id: "mock", name: "일기학습" },
        userRequest: {
          timezone: "Asia/Seoul",
          params: {},
          block: { id: "mock-block", name: "학습" },
          utterance: text,
          lang: "ko",
          user: { id: "mock-user", type: "botUserKey", properties: {} }
        },
        bot: { id: "kakao-language", name: "초급일본어" },
        action: { id: "chat", name: "chat", params: {}, detailParams: {}, clientExtra: {} }
      };
      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        const outputs = (data.template && data.template.outputs) || [];
        outputs.forEach((o) => {
          const t = o.simpleText && o.simpleText.text;
          if (t) addBubble(t, "bot");
        });
        renderChips(data.template && data.template.quickReplies);
      } catch (e) {
        addBubble("연결에 실패했습니다. 서버를 확인해 주세요.", "bot");
      }
    }

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      send(input.value);
    });

    addBubble("내 일상 한국어에 일본어를 조금씩 넣습니다.\\n\\n일기를 보내 주세요. 기본은 Lv.1 명사 빈칸입니다.", "bot");
    const cfg = __DEMO_CONFIG__;
    if (cfg.demo && cfg.diary) {
      send(cfg.diary);
    }
  </script>
</body>
</html>
"""

# user_id -> session
SESSIONS: dict[str, dict[str, Any]] = {}

app = FastAPI(title="Kakao Japanese MVP")


def env_str(name: str) -> str:
    return (os.getenv(name) or "").strip()


def api_key() -> str:
    return env_str("OPENAI_API_KEY")


def llm_model() -> str:
    return env_str("LLM_MODEL") or DEFAULT_MODEL


def base_url() -> str:
    return env_str("OPENAI_BASE_URL")


def format_llm_error(exc: BaseException) -> str:
    raw = str(exc)
    raw = re.sub(r"sk-[A-Za-z0-9_\-]+", "[redacted]", raw)
    raw = re.sub(r"Bearer \S+", "Bearer [redacted]", raw)
    snippet = re.sub(r"\s+", " ", raw).strip()[:180]
    status = getattr(exc, "status_code", None)
    if status:
        return f"빈칸을 만들지 못했습니다. OpenAI {status}: {snippet}"
    return f"빈칸을 만들지 못했습니다. {snippet}"


def clip(text: str) -> str:
    text = (text or "").strip()
    if len(text) <= TEXT_LIMIT:
        return text
    return text[: TEXT_LIMIT - 1] + "…"


def skill_response(texts: list[str], quick: list[str] | None = None) -> dict:
    outputs = [{"simpleText": {"text": clip(t)}} for t in texts if clip(t)][:3]
    if not outputs:
        outputs = [{"simpleText": {"text": "한국어 일기나 오늘 할 일을 보내 주세요."}}]
    body: dict = {"version": "2.0", "template": {"outputs": outputs}}
    labels = quick if quick is not None else ["다른 일기", "Lv.1", "Lv.2"]
    body["template"]["quickReplies"] = [
        {"label": label, "action": "message", "messageText": label} for label in labels[:10]
    ]
    return body


def make_client() -> OpenAI:
    kwargs: dict = {"api_key": api_key()}
    url = base_url()
    if url:
        kwargs["base_url"] = url
    return OpenAI(**kwargs)


def user_id_of(payload: dict) -> str:
    user = ((payload.get("userRequest") or {}).get("user") or {})
    return str(user.get("id") or "mock-user")


def session_of(uid: str) -> dict[str, Any]:
    if uid not in SESSIONS:
        SESSIONS[uid] = {"level": 1, "remaining": [], "reveal": "", "options": []}
    return SESSIONS[uid]


def parse_level(text: str) -> int | None:
    m = re.fullmatch(r"(?:lv\.?|레벨)\s*([1-5])", text.strip(), re.I)
    if m:
        return int(m.group(1))
    return None


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s).strip().lower()


def split_answers(text: str) -> list[str]:
    parts = re.split(r"[\s,，/·]+", text.strip())
    return [p for p in parts if p]


def hangul_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha() or "\uac00" <= c <= "\ud7a3"]
    if not letters:
        return 0.0
    hangul = [c for c in letters if "\uac00" <= c <= "\ud7a3"]
    return len(hangul) / len(letters)


def looks_like_diary(text: str, sess: dict) -> bool:
    if parse_level(text) or text in {"다른 일기", "정답 보기", "퀴즈만 다시"}:
        return False
    if len(text) >= 12 and hangul_ratio(text) >= 0.5:
        return True
    if not sess.get("remaining"):
        return hangul_ratio(text) >= 0.4 and len(text) >= 6
    return False


def extract_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("no json")
    data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise ValueError("not object")
    return data


def puzzle_from_llm(diary: str, level: int) -> dict:
    client = make_client()
    resp = client.chat.completions.create(
        model=llm_model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"LEVEL={level}\n{diary}"},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    data = extract_json(resp.choices[0].message.content or "")
    blanks = data.get("blanks") or []
    remaining = []
    for b in blanks:
        if not isinstance(b, dict):
            continue
        remaining.append(
            {
                "ko": str(b.get("ko") or ""),
                "jp": str(b.get("jp") or ""),
                "reading": str(b.get("reading") or ""),
            }
        )
    distractors = [str(x) for x in (data.get("distractors") or []) if str(x).strip()]
    options = [b["jp"] for b in remaining if b["jp"]] + distractors
    # unique, keep order
    seen: set[str] = set()
    uniq = []
    for o in options:
        if o not in seen:
            seen.add(o)
            uniq.append(o)
    return {
        "cloze": str(data.get("cloze") or "").strip(),
        "reveal": str(data.get("reveal") or "").strip(),
        "remaining": remaining,
        "options": uniq[:8],
    }


def match_blank(token: str, blank: dict) -> bool:
    t = norm(token)
    return t == norm(blank["jp"]) or (blank["reading"] and t == norm(blank["reading"]))


def grade(tokens: list[str], remaining: list[dict]) -> tuple[list[dict], list[str]]:
    left = list(remaining)
    wrong: list[str] = []
    for tok in tokens:
        hit = next((i for i, b in enumerate(left) if match_blank(tok, b)), None)
        if hit is None:
            wrong.append(tok)
        else:
            left.pop(hit)
    return left, wrong


def puzzle_chips(sess: dict) -> list[str]:
    chips = list(sess.get("options") or [])
    extra = ["정답 보기", "다른 일기", f"Lv.{sess.get('level', 1)}"]
    out = []
    for c in chips + extra:
        if c not in out:
            out.append(c)
    return out[:10]


def intro_text(level: int) -> str:
    return (
        "한국어는 그대로 두고, 빈칸만 일본어로 채우세요.\n"
        f"지금 Lv.{level} — {LEVEL_HELP[level]}"
    )


@app.get("/", response_class=HTMLResponse)
def mockup() -> str:
    config = json.dumps({"demo": not bool(api_key()), "diary": DEMO_DIARY}, ensure_ascii=False)
    return MOCKUP_HTML.replace("__DEMO_CONFIG__", config)


@app.post("/api/chat")
async def chat(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(skill_response(["요청을 읽지 못했습니다. 일기 텍스트를 다시 보내 주세요."]))
    if not isinstance(payload, dict):
        return JSONResponse(skill_response(["한국어 일기나 오늘 할 일을 보내 주세요."]))

    utterance = ((payload.get("userRequest") or {}).get("utterance") or "").strip()
    uid = user_id_of(payload)
    sess = session_of(uid)
    level = int(sess.get("level") or 1)

    if not utterance:
        return JSONResponse(skill_response([intro_text(level)]))

    if utterance in {"다른 일기", "다른 일기 보내기"}:
        sess["remaining"] = []
        sess["reveal"] = ""
        sess["options"] = []
        return JSONResponse(skill_response(["새 한국어 일기나 할 일을 보내 주세요.", intro_text(level)]))

    lv = parse_level(utterance)
    if lv is not None:
        sess["level"] = lv
        sess["remaining"] = []
        sess["reveal"] = ""
        return JSONResponse(
            skill_response(
                [f"Lv.{lv}로 바꿨습니다. {LEVEL_HELP[lv]}", "한국어 일기를 보내 주세요."],
                ["다른 일기", "Lv.1", "Lv.2", "Lv.3", "Lv.4", "Lv.5"],
            )
        )

    if utterance == "정답 보기":
        reveal = sess.get("reveal") or "아직 풀 문제가 없습니다. 일기를 먼저 보내 주세요."
        sess["remaining"] = []
        return JSONResponse(
            skill_response([reveal, "다음 일기를 보내거나 레벨을 바꿔 보세요."], puzzle_chips(sess))
        )

    if sess.get("remaining") and not looks_like_diary(utterance, sess):
        left, wrong = grade(split_answers(utterance), sess["remaining"])
        sess["remaining"] = left
        if not left:
            reveal = sess.get("reveal") or "정답입니다."
            return JSONResponse(
                skill_response(
                    ["맞았습니다. 한국어 속에 일본어가 섞였습니다.", reveal],
                    ["다른 일기", "Lv.1", "Lv.2", "Lv.3"],
                )
            )
        msg = f"남은 빈칸 {len(left)}개."
        if wrong:
            msg += f" 아닌 것: {', '.join(wrong)}"
        return JSONResponse(skill_response([msg], puzzle_chips(sess)))

    if not api_key():
        puzzle = deepcopy(DEMO_PUZZLE)
    else:
        try:
            puzzle = puzzle_from_llm(utterance, level)
        except Exception as exc:
            return JSONResponse(skill_response([format_llm_error(exc)]))

    sess["remaining"] = puzzle["remaining"]
    sess["reveal"] = puzzle["reveal"]
    sess["options"] = puzzle["options"]
    cloze = puzzle["cloze"] or utterance
    n = len(puzzle["remaining"])
    hint = (
        f"Lv.{level} 빈칸 {n}개. 칩을 누르거나 일본어를 적어 보내 주세요."
        if level < 5
        else "Lv.5 문장 전체를 일본어로 적어 보내 주세요."
    )
    if not api_key():
        hint += "\n(데모: API 키 없이 PRD 예시 명사 빈칸입니다. 임의 일기는 OPENAI_API_KEY가 필요합니다.)"
    return JSONResponse(skill_response([f"{intro_text(level)}\n\n{cloze}", hint], puzzle_chips(sess)))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
