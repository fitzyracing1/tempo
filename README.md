# TEMPO

Temperature AI for iterative spec rewriting. Local Grok desk. No API key.

Seed schedule: **H H L H** (`1.0, 1.0, 0.2, 1.0`).

## Ask the AI

```bash
python3 ask.py "what is the next t?"
python3 ask.py "why not finish?"
python3 ask.py
```

Interactive commands: `next`, `rule`, `spec`, `set spec <text>`, `brief <text>`, `commit`, `reset`, `help`, `quit`.

## HTTP chat

```bash
python3 mock_server.py --port 3000
```

Open http://127.0.0.1:3000

| method | path | body |
|---|---|---|
| GET | / | chat UI |
| GET | /state | temps + spec |
| GET | /help | routes |
| POST | /ask | `{"question":"what is the next t?"}` |
| POST | /decide | `{"brain":"grok"}` |
| POST | /spec | `{"cur":"..."}` |
| POST | /reset | `{}` |
| POST | /commit | append last t |

## Layout

- `tempo.py` — grok + rule brains
- `desk.py` — question router
- `ask.py` — CLI
- `mock_server.py` — stdlib HTTP desk
- `static/index.html` — chat UI
- `data/seed.json` — seed + sample questions
