#!/usr/bin/env python3
"""CLI desk. Usage:
    python3 ask.py "what is the next t?"
    python3 ask.py                  # interactive
"""
import json
import sys
from desk import answer, fresh_state, HELP
from tempo import decide, mode_for


def apply_line(line, state):
    raw = line.strip()
    if not raw:
        return ""
    low = raw.lower()

    if low in ("quit", "exit", "q"):
        return "__QUIT__"
    if low in ("help", "?"):
        return HELP
    if low == "reset":
        state.clear()
        state.update(fresh_state())
        return "reset to seed HHLH"
    if low == "spec":
        return state["cur"]
    if low.startswith("set spec"):
        text = raw[8:].strip()
        if not text:
            return "usage: set spec <text>"
        state["prev"] = state["cur"]
        state["cur"] = text
        return f"spec updated ({len(text)} chars). prev frozen."
    if low.startswith("brief "):
        state["brief"] = raw[6:].strip()
        return "brief set."
    if low == "next":
        return answer("what is the next t?", state)
    if low == "rule":
        state["brain"] = "rule"
        msg = answer("what is the next t?", state)
        state["brain"] = "grok"
        return "rule brain:\n" + msg
    if low == "commit":
        out = state.get("last") or decide(
            brief=state["brief"], temps=state["temps"],
            prev=state["prev"], cur=state["cur"], brain="grok",
        )
        if out["next"] == "FINISH":
            return "already at FINISH — nothing to commit"
        state["temps"].append(float(out["t"]))
        state["last"] = None
        return "committed t=" + str(out["t"]) + "  now " + "".join(mode_for(t) for t in state["temps"])
    if low.startswith("ask "):
        raw = raw[4:]
    msg = answer(raw, state)
    state["log"].append({"q": raw, "a": msg})
    return msg


def main():
    state = fresh_state()
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        print(apply_line(q, state))
        return
    print("TEMPO desk  (Grok, no key)  seed HHLH")
    print("type help  |  quit to leave")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        msg = apply_line(line, state)
        if msg == "__QUIT__":
            break
        if msg:
            print(msg)


if __name__ == "__main__":
    main()
