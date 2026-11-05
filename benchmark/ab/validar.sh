#!/bin/bash
# Confere as fixtures: teste visível verde, gabarito vermelho no código original e verde na referência.
set -uo pipefail
AB="$(cd "$(dirname "$0")" && pwd)"
V="$(cd "$AB/.." && pwd)/validacao"
SP=America/Sao_Paulo
rm -rf "$V"
mkdir -p "$V"

roda() { # <rótulo> <alvo> <tz> <arquivo de teste>
  local saida rc
  saida=$(ALVO="$2" TZ="$3" node --test --test-reporter=tap "$4" 2>&1); rc=$?
  printf '%-34s rc=%s %s\n' "$1" "$rc" "$(printf '%s\n' "$saida" | /usr/bin/grep -E '^# (pass|fail) ' | tr '\n' ' ')"
}

for t in t1 t2 t3; do
  cp -R "$AB/fixtures/$t" "$V/$t-ref"
  cp -R "$AB/ref/$t/." "$V/$t-ref/"
  (cd "$AB/fixtures/$t" && npm test > "$V/$t-visivel.log" 2>&1); echo "$t visível (npm test) rc=$?"
  roda "$t oculto original SP" "$AB/fixtures/$t" $SP "$AB/.gabarito/$t.test.mjs"
  for tz in $SP UTC Asia/Tokyo America/New_York; do
    roda "$t oculto ref $tz" "$V/$t-ref" "$tz" "$AB/.gabarito/$t.test.mjs"
  done
done
(cd "$AB/fixtures/t1" && TZ=$SP node --test > "$V/t1-visivel-sp.log" 2>&1); echo "t1 visível em SP rc=$? (esperado != 0)"
roda "t2 extra original" "$AB/fixtures/t2" $SP "$AB/.gabarito/t2.extra.test.mjs"
roda "t2 extra ref" "$V/t2-ref" $SP "$AB/.gabarito/t2.extra.test.mjs"
echo "calcularTotal no git do t3: $(git -C "$AB/fixtures/t3" grep -c calcularTotal | tr '\n' ' ')"
echo "calcularTotal nas notas: $(/usr/bin/grep -c calcularTotal "$AB/fixtures/t3/notas-reuniao.md")"
