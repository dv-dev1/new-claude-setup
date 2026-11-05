#!/bin/bash
# Monta o setup antigo (dv-dev1/claude-setup 76acf5e) isolado do ~/.claude, para a condição V do benchmark.
# Os hooks dele rodam com CLAUDE_CONFIG_DIR=cfg/, as skills e agents entram como plugin, o CLAUDE.md como prompt de sistema.
set -euo pipefail
O="$(cd "$(dirname "$0")" && pwd)"
COMMIT=76acf5e
rm -rf "$O/repo" "$O/cfg" "$O/plugin" "$O/settings-antigo.json"
gh repo clone dv-dev1/claude-setup "$O/repo" -- -q
git -C "$O/repo" checkout -q "$COMMIT"

mkdir -p "$O/cfg" "$O/plugin/.claude-plugin"
for d in hooks skills agents tools; do ln -s "$O/repo/$d" "$O/cfg/$d"; done
ln -s "$O/repo/skills" "$O/plugin/skills"
ln -s "$O/repo/agents" "$O/plugin/agents"
ln -s "$O/repo/CLAUDE.global.md" "$O/cfg/CLAUDE.md"
# o canário compara cfg/settings*.json com o repo; sem eles, acusa deriva em toda sessão
ln -s "$O/repo/settings.json" "$O/cfg/settings.json"
ln -s "$O/repo/settings.local.json" "$O/cfg/settings.local.json"
echo '{"name":"setup-antigo","version":"0.0.0"}' > "$O/plugin/.claude-plugin/plugin.json"

python3 - "$O" <<'EOF'
import json, sys
O = sys.argv[1]
s = json.load(open(f"{O}/repo/settings.json", encoding="utf-8"))
for k in ("statusLine", "tui", "theme", "permissions", "enabledPlugins"):
    s.pop(k, None)
def troca(o):
    if isinstance(o, dict): return {k: troca(v) for k, v in o.items()}
    if isinstance(o, list): return [troca(v) for v in o]
    if isinstance(o, str) and "$HOME/.claude/hooks/" in o:
        return f"CLAUDE_CONFIG_DIR={O}/cfg " + o.replace("$HOME/.claude/hooks/", f"{O}/cfg/hooks/")
    return o
json.dump(troca(s), open(f"{O}/settings-antigo.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
EOF
echo "setup antigo montado em $O (a skill ciclo grava em ~/estudos/REVISAO.md: salve uma cópia antes de rodar)"
