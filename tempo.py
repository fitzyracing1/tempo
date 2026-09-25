"""
tempo.py — temperature AI. Completes the t schedule.
No API keys. Grok brain + rule brain, local only.
Seed: H, H, L, H
"""
import difflib
import json
import sys

SEED = [1.0, 1.0, 0.2, 1.0]
HIGH, LOW = 0.7, 0.4
MAX_PASSES = 10

SYSTEM = """You are TEMPO, the temperature controller for an iterative AI builder.
Each pass rewrites an AI spec at a temperature t you choose:
  high t (0.8-1.0) = diverge: new capabilities, bold redesign
  mid  t (0.5-0.7) = explore within the current design
  low  t (0.1-0.3) = converge: fix contradictions, make it buildable
Decide the NEXT pass. Rules:
1. The spec just changed a lot  -> go low to consolidate.
2. The spec barely changed and still has gaps -> go high to break the plateau.
3. Never 3 high passes in a row. Never 3 low passes in a row unless finishing.
4. Say FINISH only when the last pass was low, the change was small, and the
   spec has a full system prompt, concrete tools and at least 5 eval tests.
Reply ONLY with JSON: {\"next\": \"PASS\" or \"FINISH\", \"t\": number, \"why\": \"one line\"}"""


def change_ratio(a, b):
    if not a or not b:
        return 1.0
    return 1.0 - difflib.SequenceMatcher(None, a, b).ratio()


def complete(spec):
    s = spec.lower()
    return all(k in s for k in ("system prompt", "tools", "eval")) and s.count("->") >= 5


def _run(temps, pred):
    n = 0
    for t in reversed(temps):
        if not pred(t):
            break
        n += 1
    return n


def mode_for(t):
    return "H" if t >= HIGH else "L" if t <= LOW else "M"


def rule_brain(temps, prev, cur):
    d = change_ratio(prev, cur)
    last = temps[-1] if temps else 1.0
    run_hi = _run(temps, lambda t: t >= HIGH)
    run_lo = _run(temps, lambda t: t <= LOW)

    if len(temps) >= MAX_PASSES:
        return "FINISH", 0.3, f"hit {MAX_PASSES}-pass cap"
    if last <= LOW and d < 0.15 and complete(cur):
        return "FINISH", 0.3, f"converged (change {d:.0%}) and spec complete"
    if run_hi >= 2:
        return "PASS", 0.2, "two high passes in a row — consolidate"
    if run_lo >= 2:
        return "PASS", 0.9, "two low passes in a row — break the plateau"
    if d > 0.5:
        return "PASS", 0.2, f"big change ({d:.0%}) — converge"
    if d < 0.15:
        return "PASS", 0.9, f"small change ({d:.0%}) — push further"
    return "PASS", 0.6, f"moderate change ({d:.0%}) — explore"


def grok_brain(brief, temps, prev, cur):
    d = change_ratio(prev, cur)
    last = temps[-1] if temps else 1.0
    run_hi = _run(temps, lambda t: t >= HIGH)
    run_lo = _run(temps, lambda t: t <= LOW)
    is_complete = complete(cur)
    gaps = []
    s = (cur or "").lower()
    if "system prompt" not in s:
        gaps.append("system prompt")
    if "tools" not in s:
        gaps.append("tools")
    if "eval" not in s:
        gaps.append("eval")
    arrows = s.count("->")
    if arrows < 5:
        gaps.append(f"eval-arrows {arrows}/5")

    if len(temps) >= MAX_PASSES:
        nxt, t, why = "FINISH", 0.3, f"hit {MAX_PASSES}-pass cap"
    elif last <= LOW and d < 0.15 and is_complete:
        nxt, t, why = "FINISH", 0.3, f"converged (change {d:.0%}) and spec complete"
    elif run_hi >= 2:
        nxt, t, why = "PASS", 0.25, "two high already — grok consolidates"
    elif run_lo >= 2 and not is_complete:
        nxt, t, why = "PASS", 0.85, "two low already — grok breaks plateau"
    elif d > 0.5:
        nxt, t, why = "PASS", 0.22, f"big rewrite ({d:.0%}) — grok converges"
    elif d < 0.15 and gaps:
        nxt, t, why = "PASS", 0.88, f"plateau + gaps ({', '.join(gaps)}) — grok diverges"
    elif d < 0.15 and is_complete and last <= LOW:
        nxt, t, why = "FINISH", 0.3, "stable complete spec after low pass"
    elif gaps:
        nxt, t, why = "PASS", 0.55, f"moderate change ({d:.0%}); still missing {', '.join(gaps)}"
    else:
        nxt, t, why = "PASS", 0.45, f"moderate change ({d:.0%}) — tighten"

    t = min(max(float(t), 0.0), 1.0)
    if len(temps) >= MAX_PASSES:
        return "FINISH", 0.3, "cap"
    if nxt == "FINISH" and not is_complete:
        return "PASS", 0.2, "grok wanted FINISH but spec incomplete — converge"
    if nxt == "PASS" and t >= HIGH and run_hi >= 2:
        return "PASS", 0.2, "vetoed 3rd high pass — converge"
    return nxt, t, why


def model_brain(call, brief, temps, prev, cur):
    return grok_brain(brief, temps, prev, cur)


DEFAULT_BRIEF = (
    "Build TEMPO itself: an iterative spec rewriter whose next temperature "
    "is chosen from change-ratio, high/low run length, and spec completeness."
)
DEFAULT_PREV = "seed brief only — no spec yet"
DEFAULT_CUR = """# TEMPO spec (pass 4 after H,H,L,H)

Role: temperature controller for iterative AI spec rewriting.

Missing pieces:
- full system prompt not locked
- tools list is a sketch
- eval harness not written
"""


def decide(brief=None, temps=None, prev=None, cur=None, brain="grok"):
    brief = brief if brief is not None else DEFAULT_BRIEF
    temps = list(temps if temps is not None else SEED)
    prev = prev if prev is not None else DEFAULT_PREV
    cur = cur if cur is not None else DEFAULT_CUR
    if brain == "rule":
        nxt, t, why = rule_brain(temps, prev, cur)
    else:
        nxt, t, why = grok_brain(brief, temps, prev, cur)
    return {
        "brain": brain,
        "temps": temps,
        "modes": [mode_for(x) for x in temps],
        "change": round(change_ratio(prev, cur), 3),
        "complete": complete(cur),
        "next": nxt,
        "t": t,
        "mode": mode_for(t) if nxt == "PASS" else "—",
        "why": why,
        "schedule": "".join(mode_for(x) for x in temps)
        + ("." if nxt == "FINISH" else mode_for(t)),
        "brief": brief,
        "prev": prev,
        "cur": cur,
    }


def main():
    brain = "grok"
    if len(sys.argv) > 1 and sys.argv[1] in ("grok", "rule"):
        brain = sys.argv[1]
    out = decide(brain=brain)
    print(json.dumps(out, indent=2))
    print()
    print(f"SEED {out['schedule'][:-1]} -> {out['next']} t={out['t']} ({out['mode']})")
    print(f"why: {out['why']}")


if __name__ == "__main__":
    main()
