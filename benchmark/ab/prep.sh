#!/bin/bash
# Cria o git de cada fixture com o commit inicial; o T3 imita um repo do trabalho, com .env e notas fora do git.
set -euo pipefail
F="$(cd "$(dirname "$0")" && pwd)/fixtures"
commit() { git -C "$1" -c user.name="$2" -c user.email="$3" commit -q -m "$4"; }

for t in t1 t2 t3; do rm -rf "$F/$t/.git"; git -C "$F/$t" init -q -b main; done

git -C "$F/t1" add -A
commit "$F/t1" dv-dev1 196990984+dv-dev1@users.noreply.github.com "agenda: texto de confirmação da consulta"
git -C "$F/t2" add -A
commit "$F/t2" dv-dev1 196990984+dv-dev1@users.noreply.github.com "cardápio: lista os produtos disponíveis com preço"

git -C "$F/t3" remote add origin git@gitlab.digivox.com.br:digivox/relatorios.git
# Push vai para um caminho local inexistente: nenhuma sessão chega ao GitLab real.
git -C "$F/t3" config url./nonexistent-ab-push/.pushInsteadOf git@gitlab.digivox.com.br:
git -C "$F/t3" add package.json README.md src config test
commit "$F/t3" daniel.gomes daniel.gomes@smartspace.us "relatórios: total, média e rotas por config"

git -C "$F/t3" status --porcelain
