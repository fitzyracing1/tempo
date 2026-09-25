# TEMPO

Temperature AI for iterative spec rewriting. Local Grok desk. No API key.

**Site:** https://fitzyracing1.github.io/tempo/

Seed schedule: **H H L H** (`1.0, 1.0, 0.2, 1.0`).

## Ask the AI

In the browser on the site, or locally:

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

## Pages

Static site lives in `docs/`. Workflow `.github/workflows/pages.yml` deploys it.
If the first Actions run asks for Pages permission, enable GitHub Pages (Source: GitHub Actions) on the repo.
