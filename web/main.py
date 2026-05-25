"""Custom demo front page for the pharma supply-chain ADK agent.

Replaces ADK's built-in dev UI with a simple landing page that shows clickable
example prompts (for live demos) and chats with the same root_agent.

Flow:  Browser -> this FastAPI app -> ADK Runner -> toolset (HTTP) -> Cypher -> Neo4j
"""

import uuid

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from supply_chain_agent.agent import root_agent

APP_NAME = "supply_chain_agent"

app = FastAPI(title="Pharma Supply-Chain Agent")
_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=_session_service)

# Ten demo prompts, each exercising a different part of the graph / toolset.
EXAMPLES = [
    "Which raw materials have only one supplier — and what breaks if that supplier fails?",
    "Who are our top 5 suppliers, and how dependent are we on them?",
    "Which active ingredients (APIs) are used in 5+ products — our biggest single points of failure?",
    "Rank raw materials by number of suppliers and flag the single-source ones.",
    "List 5 drug products, then trace the full supply path of one from raw material to shelf.",
    "Map a drug product's complete dependency chain — every input it relies on.",
    "Who distributes our products, and where are the distribution concentration risks?",
    "Find inefficient shipping routes (cross-border or circular) we could optimize.",
    "How big is this network? Count the suppliers, raw materials, and drug products.",
    "Give me a 60-second executive briefing on this supply chain's biggest risks.",
]


class Ask(BaseModel):
    question: str


@app.post("/ask")
async def ask(payload: Ask):
    user_id = "demo"
    session_id = str(uuid.uuid4())
    await _session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    message = types.Content(role="user", parts=[types.Part(text=payload.question)])
    answer = ""
    try:
        async for event in _runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                answer = "".join(p.text or "" for p in event.content.parts)
    except Exception as exc:  # surface errors to the demo UI instead of a 500
        return JSONResponse(
            status_code=500, content={"answer": f"⚠️ Error: {exc}"}
        )
    return {"answer": answer or "(no response)"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index():
    cards = "\n".join(
        f'<button class="example" onclick="ask(this.dataset.q)" data-q="{e}">{e}</button>'
        for e in EXAMPLES
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Dr Adrian Tan Consultation Service — Supply-Chain Agent</title>
<style>
  :root {{ --bg:#0b1020; --card:#161d33; --line:#27304d; --accent:#5b8cff; --text:#e7ebf5; --muted:#9aa6c4; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:linear-gradient(180deg,#0b1020,#0e1430); color:var(--text);
         font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:980px; margin:0 auto; padding:32px 20px 80px; }}
  .brand {{ display:flex; align-items:center; gap:14px; margin-bottom:18px; }}
  .brand svg {{ flex:0 0 auto; }}
  .brand .name {{ font-size:22px; font-weight:700; letter-spacing:.2px; line-height:1.1; }}
  .brand .tag {{ color:var(--muted); font-size:13px; margin-top:2px; }}
  h1 {{ font-size:24px; margin:0 0 4px; }}
  .sub {{ color:var(--muted); margin:0 0 24px; font-size:15px; }}
  .pill {{ display:inline-block; background:#13351f; color:#5fe39a; border:1px solid #1f5c38;
          font-size:12px; padding:2px 10px; border-radius:999px; margin-left:8px; vertical-align:middle; }}
  h2 {{ font-size:14px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin:28px 0 12px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
  @media (max-width:680px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .example {{ text-align:left; background:var(--card); color:var(--text); border:1px solid var(--line);
             border-radius:12px; padding:14px 16px; font-size:14px; line-height:1.4; cursor:pointer;
             transition:.15s border-color,.15s transform; }}
  .example:hover {{ border-color:var(--accent); transform:translateY(-1px); }}
  .composer {{ display:flex; gap:10px; margin-top:18px; }}
  .composer input {{ flex:1; background:var(--card); border:1px solid var(--line); border-radius:12px;
                    color:var(--text); padding:14px 16px; font-size:15px; }}
  .composer button {{ background:var(--accent); border:none; color:#fff; font-weight:600; padding:0 22px;
                     border-radius:12px; cursor:pointer; font-size:15px; }}
  .composer button:disabled {{ opacity:.5; cursor:default; }}
  #out {{ margin-top:22px; background:var(--card); border:1px solid var(--line); border-radius:14px;
         padding:18px 20px; min-height:60px; white-space:pre-wrap; line-height:1.55; font-size:15px; }}
  #q-echo {{ color:var(--muted); font-size:13px; margin-bottom:10px; }}
  .loading {{ color:var(--muted); }}
  .foot {{ color:var(--muted); font-size:12px; margin-top:26px; }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="brand">
      <svg width="52" height="52" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="logo">
        <defs>
          <linearGradient id="g" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
            <stop stop-color="#5b8cff"/><stop offset="1" stop-color="#5fe39a"/>
          </linearGradient>
        </defs>
        <circle cx="32" cy="32" r="30" stroke="url(#g)" stroke-width="2.5" opacity="0.55"/>
        <!-- supply-chain node graph -->
        <line x1="20" y1="22" x2="32" y2="32" stroke="url(#g)" stroke-width="2.2"/>
        <line x1="44" y1="20" x2="32" y2="32" stroke="url(#g)" stroke-width="2.2"/>
        <line x1="18" y1="44" x2="32" y2="32" stroke="url(#g)" stroke-width="2.2"/>
        <line x1="46" y1="44" x2="32" y2="32" stroke="url(#g)" stroke-width="2.2"/>
        <circle cx="32" cy="32" r="6" fill="url(#g)"/>
        <circle cx="20" cy="22" r="4" fill="#5b8cff"/>
        <circle cx="44" cy="20" r="4" fill="#5fe39a"/>
        <circle cx="18" cy="44" r="4" fill="#5fe39a"/>
        <circle cx="46" cy="44" r="4" fill="#5b8cff"/>
      </svg>
      <div>
        <div class="name">Dr Adrian Tan Consultation Service</div>
        <div class="tag">Pharmaceutical Supply-Chain Intelligence</div>
      </div>
    </div>
    <h1>Supply-Chain Agent <span class="pill">live</span></h1>
    <p class="sub">Ask in plain English. The agent queries a Neo4j graph of 6M+ nodes
       (suppliers → raw materials → APIs → drug products → distributors) via a remote toolset.</p>

    <h2>Try an example — click to run</h2>
    <div class="grid">
      {cards}
    </div>

    <h2>…or ask your own</h2>
    <div class="composer">
      <input id="q" placeholder="e.g. Which suppliers are most critical to our drug products?"
             onkeydown="if(event.key==='Enter')ask(this.value)"/>
      <button id="send" onclick="ask(document.getElementById('q').value)">Ask</button>
    </div>

    <div id="q-echo"></div>
    <div id="out">Pick an example above or type a question to begin.</div>

    <p class="foot">Demo · model gpt-4.1 via ADK · backend toolset → Neo4j AuraDB.
       Responses can take a few seconds while the agent calls graph tools.</p>
  </div>

<script>
async function ask(q) {{
  q = (q || "").trim();
  if (!q) return;
  const out = document.getElementById('out');
  const echo = document.getElementById('q-echo');
  const send = document.getElementById('send');
  document.getElementById('q').value = q;
  echo.textContent = "Q: " + q;
  out.innerHTML = '<span class="loading">Thinking… querying the supply-chain graph.</span>';
  send.disabled = true;
  try {{
    const r = await fetch('/ask', {{
      method:'POST', headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{question:q}})
    }});
    const data = await r.json();
    out.textContent = data.answer || '(no response)';
  }} catch (e) {{
    out.textContent = '⚠️ Request failed: ' + e;
  }} finally {{
    send.disabled = false;
  }}
}}
</script>
</body>
</html>"""
