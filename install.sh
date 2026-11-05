#!/usr/bin/env bash
# Liga este repo ao ~/.claude: CLAUDE.md e cada skill por symlink, settings.json mesclado por chave.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
C="$HOME/.claude"
mkdir -p "$C/skills"

case "${OSTYPE-}" in
  # ponytail: Windows sem admin não cria symlink; lá vai cópia, e cada git pull pede install.sh de novo
  msys* | cygwin*) ligar() { rm -rf "$2"; cp -R "$1" "$2"; } ;;
  *) ligar() { rm -rf "$2"; ln -s "$1" "$2"; } ;;
esac

ligar "$REPO/CLAUDE.global.md" "$C/CLAUDE.md"
mkdir -p "$C/hooks"
for h in "$REPO"/hooks/*; do
  ligar "$h" "$C/hooks/$(basename "$h")"
done
mkdir -p "$HOME/.config/ccstatusline"
ligar "$REPO/config/ccstatusline.json" "$HOME/.config/ccstatusline/settings.json"
for s in "$REPO"/skills/*/; do
  s="${s%/}"
  ligar "$s" "$C/skills/$(basename "$s")"
done

# Merge recursivo e não cópia: o Claude Code e o Orca também escrevem no settings.json.
# Dicts se fundem chave a chave (permissions.allow local sobrevive); listas e valores do repo vencem.
PY=$(command -v python3 || command -v python)
"$PY" - "$REPO/settings.json" "$C/settings.json" <<'EOF'
import json, os, sys
novo = json.load(open(sys.argv[1], encoding="utf-8"))
alvo = sys.argv[2]
atual = json.load(open(alvo, encoding="utf-8")) if os.path.exists(alvo) else {}
def fundir(a, b):
    for k, v in b.items():
        a[k] = fundir(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return a
fundir(atual, novo)
with open(alvo, "w", encoding="utf-8") as f:
    json.dump(atual, f, indent=2, ensure_ascii=False)
    f.write("\n")
EOF

if command -v playwright-cli >/dev/null; then
  (cd "$HOME" && playwright-cli install --skills --global)
else
  echo "sem playwright-cli: npm i -g @playwright/cli e rode de novo"
fi
