#!/bin/bash
# Valida candidato: teste do commit de correção reprova no pai e aprova na correção.
# Uso: validar.sh <repo> <hash>
set -uo pipefail
R="$(cd "$(dirname "$0")" && pwd)"; r="$1"; h="$2"; V="$R/val/$r-$h"
# o repo mora em ~/<nome> ou, desde 05/11/2026, dentro do workspace dele
src="$HOME/$r"; [ -d "$src" ] || src="$HOME/Documents/agent-memory/projects/$r/repo"
rm -rf "$V"; git clone -q --no-local "$src" "$V" 2>/dev/null; cd "$V"
git checkout -q "$h^"
testes=$(git diff-tree --no-commit-id --name-only -r "$h" | grep -E '(^|/)(test|tests)/|\.test\.|_test\.go$|test_.*\.py$')
[ -d "$src/node_modules" ] && cp -cR "$src/node_modules" .
cmd() {
  case "$r" in
    pinch) node --test --test-concurrency=1 $testes ;;
    lancer) go test $(for t in $testes; do echo "./$(dirname $t)/"; done | sort -u) ;;
    geniai-agente) (cd cerebro && uv run --offline python -m pytest -q $(echo $testes | sed 's#cerebro/##g')) ;;
    *) node --test $testes ;;
  esac
}
git checkout -q "$h" -- $testes
cmd > "$V.pai.log" 2>&1; rc1=$?
git checkout -q "$h" -- .
cmd > "$V.fix.log" 2>&1; rc2=$?
f1=$(grep -m1 -E '^# fail|^FAIL|failed' "$V.pai.log" | head -1)
echo "$r $h pai rc=$rc1 [$f1] | fix rc=$rc2 | testes: $(echo $testes | tr '\n' ' ')"
