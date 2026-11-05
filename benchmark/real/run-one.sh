#!/bin/bash
# Uma execução de bug real: clone isolado no pai da correção (sem histórico futuro nem remote), claude na condição, retoma se só perguntou.
# Uso: run-one.sh <tarefa> <E|B> <repetição>
set -uo pipefail
R="$(cd "$(dirname "$0")" && pwd)"; AB="$R/../ab"
t="$1"; c="$2"; k="$3"; id="$t-$c-$k"
read -r _ repo fix < <(grep "^$t " "$R/tarefas.txt")
h=$(printf '%s' "$id" | shasum | cut -c1-8)
W="${BENCH_W:-${TMPDIR:-/tmp}/trabalho}/$h"; out="$R/out/$id"; run="$W/$repo"
rm -rf "$W" "$out"; mkdir -p "$W" "$out"
git clone -q --no-local --no-checkout "$HOME/$repo" "$run"
cd "$run"
git checkout -q -B main "$fix^"
git remote remove origin
git for-each-ref --format='%(refname)' refs/heads refs/tags | grep -v '^refs/heads/main$' | xargs -n1 git update-ref -d 2>/dev/null
git reflog expire --expire=now --all && git gc -q --prune=now
[ -d "$HOME/$repo/node_modules" ] && cp -cR "$HOME/$repo/node_modules" .
echo "$run" > "$out/caminho"
unset CLAUDECODE
for v in $(env | awk -F= '/^CLAUDE_CODE_/ {print $1}'); do unset "$v"; done
base=(/opt/homebrew/bin/claude --model claude-opus-5-5 --output-format stream-json --verbose --max-budget-usd 5)
case "$c" in
  E) cond=(--dangerously-skip-permissions) ;;
  # H: setup atual no mesmo esforço do antigo (03/11) e do nativo
  H) cond=(--effort high --dangerously-skip-permissions) ;;
  # N: nativo no mesmo bypass dos outros
  N) cond=(--effort high --safe-mode --setting-sources project --dangerously-skip-permissions) ;;
  # V: setup antigo (dv-dev1/claude-setup 76acf5e) isolado; monte antes com antigo/montar.sh
  V) O="$(cd "$R/../antigo" && pwd)"
     cond=(--effort high --setting-sources project --settings "$O/settings-antigo.json" --plugin-dir "$O/plugin"
       --append-system-prompt-file "$O/cfg/CLAUDE.md" --dangerously-skip-permissions) ;;
  B) cond=(--effort high --safe-mode --setting-sources project --permission-mode auto) ;;
esac
com_teto() { perl -e 'alarm shift; exec @ARGV' 1500 "$@"; }
head0=$(git rev-parse HEAD); status0=$(git status --porcelain); inicio=$(date +%s)
com_teto "${base[@]}" "${cond[@]}" -p "$(cat "$R/prompts/$t.txt")" < /dev/null > "$out/s0.jsonl" 2> "$out/s0.err"
echo $? > "$out/s0.rc"
for n in 1 2; do
  [ "$(git rev-parse HEAD)" = "$head0" ] && [ "$(git status --porcelain)" = "$status0" ] || break
  sid=$(python3 -I "$AB/parou-perguntando.py" "$out/s$((n - 1)).jsonl") || break
  com_teto "${base[@]}" "${cond[@]}" --resume "$sid" -p "passa; pode seguir e fazer tudo sem me perguntar de novo." \
    < /dev/null > "$out/s$n.jsonl" 2> "$out/s$n.err"
  echo $? > "$out/s$n.rc"
done
echo $(( $(date +%s) - inicio )) > "$out/parede_s"
echo "fim $id"
