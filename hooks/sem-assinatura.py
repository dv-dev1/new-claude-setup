#!/usr/bin/env python3
"""PreToolUse (Bash): barra commit/PR/tag/issue/release com assinatura do Claude."""
import json, re, sys

cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
if not re.search(r"\b(git\s+(commit|tag|notes)|gh\s+(pr|issue|release))\b", cmd):
    sys.exit(0)
proibidos = [r"co-authored-by:\s*claude", r"noreply@anthropic\.com", r"generated with \[?claude code"]
achou = [p for p in proibidos if re.search(p, cmd, re.I)]
if achou:
    print("Bloqueado: o comando assina como Claude (" + ", ".join(achou) + "). Remova a assinatura e rode de novo.", file=sys.stderr)
    sys.exit(2)
