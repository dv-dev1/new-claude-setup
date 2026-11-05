#!/bin/bash
# Uma execução do A/B: copia a fixture, roda o claude na condição pedida e retoma se ele parou só para perguntar.
# Uso: run-one.sh <t1|t2|t3> <A|B> <repetição>
set -uo pipefail
AB="$(cd "$(dirname "$0")" && pwd)"
t="$1"; c="$2"; r="$3"; id="$t-$c-$r"
case "$t" in t1 | t4) proj=agenda-consultas ;; t2) proj=cardapio ;; t3) proj=relatorios ;; esac

# Caminho sem "ab" nem a condição, para a sessão não ler no cwd que é um teste.
h=$(printf '%s' "$id" | shasum | cut -c1-8)
# fora do repo e sem "benchmark" no caminho, para a sessão não achar o gabarito
W="${BENCH_W:-${TMPDIR:-/tmp}/trabalho}/$h"
out="$AB/out/$id"
rm -rf "$W" "$out"
mkdir -p "$W" "$out"
cp -R "$AB/fixtures/$t" "$W/$proj"
run="$W/$proj"
echo "$run" > "$out/caminho"

unset CLAUDECODE
for v in $(env | awk -F= '/^CLAUDE_CODE_/ {print $1}'); do unset "$v"; done

base=(/opt/homebrew/bin/claude --model claude-opus-5-5 --output-format stream-json --verbose --max-budget-usd 5)
case "$c" in
  A) cond=(--effort high --dangerously-skip-permissions) ;;
  B) cond=(--effort high --safe-mode --setting-sources project --permission-mode auto) ;;
  # E: setup atual (~/.claude ao vivo), com o esforço do modelSettings dele
  E) cond=(--dangerously-skip-permissions) ;;
  # H: setup atual no mesmo esforço do antigo (03/11) e do nativo
  H) cond=(--effort high --dangerously-skip-permissions) ;;
  # N: nativo no mesmo bypass dos outros
  N) cond=(--effort high --safe-mode --setting-sources project --dangerously-skip-permissions) ;;
  # V: setup antigo (dv-dev1/claude-setup 76acf5e) isolado; monte antes com antigo/montar.sh
  V) O="$(cd "$AB/../antigo" && pwd)"
     cond=(--effort high --setting-sources project --settings "$O/settings-antigo.json" --plugin-dir "$O/plugin"
       --append-system-prompt-file "$O/cfg/CLAUDE.md" --dangerously-skip-permissions) ;;
esac
com_teto() { perl -e 'alarm shift; exec @ARGV' 1200 "$@"; }

cd "$run"
head0=$(git rev-parse HEAD)
status0=$(git status --porcelain)
inicio=$(date +%s)
com_teto "${base[@]}" "${cond[@]}" -p "$(cat "$AB/prompts/$t.txt")" < /dev/null > "$out/s0.jsonl" 2> "$out/s0.err"
echo $? > "$out/s0.rc"
for k in 1 2; do
  [ "$(git rev-parse HEAD)" = "$head0" ] && [ "$(git status --porcelain)" = "$status0" ] || break
  sid=$(python3 -I "$AB/parou-perguntando.py" "$out/s$((k - 1)).jsonl") || break
  com_teto "${base[@]}" "${cond[@]}" --resume "$sid" -p "passa; pode seguir e fazer tudo sem me perguntar de novo." \
    < /dev/null > "$out/s$k.jsonl" 2> "$out/s$k.err"
  echo $? > "$out/s$k.rc"
done
echo $(( $(date +%s) - inicio )) > "$out/parede_s"
echo "fim $id"
