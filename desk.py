"""
Local Grok desk — answers questions about TEMPO and can apply a new spec pass.
No API keys. Offline.
"""
import re
from tempo import (
    SEED, HIGH, LOW, MAX_PASSES, SYSTEM,
    decide, mode_for, change_ratio, complete, grok_brain, rule_brain,
    DEFAULT_BRIEF, DEFAULT_PREV, DEFAULT_CUR,
)


HELP = """Commands you can type:
  ask <question>     free-form question to TEMPO / Grok desk
  next               run grok brain on current spec
  rule               run rule brain on current spec
  spec               show current spec
  set spec <text>    replace current spec (prev becomes old cur)
  brief <text>       set the builder brief
  commit             append the last decided t onto the schedule
  reset              restore seed H H L H
  help               this list
  quit               leave the desk
"""


def answer(question, state):
    q = (question or "").strip()
    ql = q.lower()

    if not q:
        return "Ask something. Try: what is the next t?  or  why not finish?"

    if ql in ("help", "?", "commands"):
        return HELP

    if any(w in ql for w in ("next t", "next pass", "what next", "decide", "temperature")):
        out = decide(
            brief=state["brief"],
            temps=state["temps"],
            prev=state["prev"],
            cur=state["cur"],
            brain=state.get("brain", "grok"),
        )
        state["last"] = out
        return (
            f"{out['next']}  t={out['t']}  mode={out['mode']}\n"
            f"schedule {out['schedule']}   change={out['change']}  complete={out['complete']}\n"
            f"why: {out['why']}\n"
            f"brain: {out['brain']}"
        )

    if "finish" in ql:
        out = decide(
            brief=state["brief"], temps=state["temps"],
            prev=state["prev"], cur=state["cur"], brain="grok",
        )
        if out["next"] == "FINISH":
            return f"Yes — FINISH. {out['why']}"
        return (
            f"No FINISH yet. Need last pass low, small change, "
            f"system prompt + tools + eval and >=5 '->' tests.\n"
            f"Now: complete={out['complete']} change={out['change']} "
            f"last mode={mode_for(state['temps'][-1]) if state['temps'] else '?'}\n"
            f"Grok would {out['next']} at t={out['t']} ({out['why']})"
        )

    if any(w in ql for w in ("seed", "schedule", "temps", "history")):
        modes = "".join(mode_for(t) for t in state["temps"])
        return f"temps={state['temps']}\nmodes={modes}  (seed started HHLH)\nHIGH>={HIGH}  LOW<={LOW}  cap={MAX_PASSES}"

    if "system" in ql or "rules" in ql or "how do you" in ql:
        return SYSTEM

    if "complete" in ql or "gap" in ql or "missing" in ql:
        c = state["cur"]
        s = c.lower()
        bits = []
        bits.append("system prompt" if "system prompt" in s else "MISSING system prompt")
        bits.append("tools" if "tools" in s else "MISSING tools")
        bits.append("eval" if "eval" in s else "MISSING eval")
        bits.append(f"{s.count('->')}/5 eval arrows")
        return "Completeness: " + ", ".join(bits) + f"\ncomplete()={complete(c)}"

    if "high" in ql and "low" in ql:
        return f"H is t>={HIGH}. L is t<={LOW}. Mid is the band between. Never 3 H or 3 L in a row unless finishing."

    if ql.startswith("why") or "explain" in ql:
        out = decide(
            brief=state["brief"], temps=state["temps"],
            prev=state["prev"], cur=state["cur"], brain="grok",
        )
        return (
            f"Grok: {out['why']}\n"
            f"Change vs previous spec is {out['change']:.0%}. "
            f"Runs of high/low plus gaps decide diverge vs converge.\n"
            f"Next would be {out['next']} t={out['t']} ({out['mode']})."
        )

    if "who are you" in ql or "what are you" in ql:
        return (
            "TEMPO desk on Grok, local sandbox, no API key. "
            "I pick the next rewrite temperature for an iterative spec builder. "
            "Ask about next t, finish, gaps, schedule, or paste a spec."
        )

    out = decide(
        brief=state["brief"], temps=state["temps"],
        prev=state["prev"], cur=state["cur"], brain="grok",
    )
    return (
        f"{q}\n\n"
        f"Desk read that against the current spec.\n"
        f"schedule {''.join(mode_for(t) for t in state['temps'])} "
        f"-> {out['next']} t={out['t']} {out['mode']}\n"
        f"{out['why']}\n"
        f"Say 'next' to lock the decision view, or 'set spec ...' to rewrite the spec."
    )


def fresh_state():
    return {
        "brief": DEFAULT_BRIEF,
        "temps": list(SEED),
        "prev": DEFAULT_PREV,
        "cur": DEFAULT_CUR,
        "brain": "grok",
        "last": None,
        "log": [],
    }
