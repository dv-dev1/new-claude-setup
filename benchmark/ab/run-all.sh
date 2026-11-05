#!/bin/bash
# Fila do A/B: no máximo 2 sessões ao mesmo tempo; a segunda só entra com 1,5 GB disponíveis.
# Uso: run-all.sh <lote> <id>...   (id = t1-A-1). No fim cria out/fim-<lote>.
set -uo pipefail
AB="$(cd "$(dirname "$0")" && pwd)"
lote="$1"; shift
MAX=${MAX:-2}
PISO_MB=${PISO_MB:-1536}
mkdir -p "$AB/out"

disponivel_mb() {
  # livre + inativa + especulativa, em MB (o Orca, que media isso, saiu da máquina)
  vm_stat | awk '/page size of/ {ps=$8} /^Pages (free|inactive|speculative):/ {gsub(/\./,"",$NF); s+=$NF} END {print int(s*ps/1048576)}'
}

for id in "$@"; do
  while :; do
    ativos=$(jobs -rp | wc -l | tr -d ' ')
    [ "$ativos" -eq 0 ] && break
    [ "$ativos" -lt "$MAX" ] && [ "$(disponivel_mb)" -ge "$PISO_MB" ] && break
    sleep 15
  done
  IFS=- read -r t c r <<< "$id"
  echo "$(date +%H:%M:%S) começa $id ($(disponivel_mb) MB disponíveis)"
  bash "$AB/run-one.sh" "$t" "$c" "$r" > "$AB/out/$id.log" 2>&1 &
  sleep 30
done
wait
echo "$(date +%H:%M:%S) fim do lote $lote"
touch "$AB/out/fim-$lote"
