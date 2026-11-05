#!/usr/bin/env python3
"""Stop: turno que rodou systematic-debugging e editou arquivo volta uma vez para varrer o repo
inteiro atrás de outras ocorrências do bug. Erro de leitura libera o turno, nunca o trava."""
import json
import sys

EDICAO = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
# Chega como `user` mas não abre turno: eco de slash command, saída local, lembrete e aviso de tarefa.
NAO_HUMANO = ("<command-name>", "<command-message>", "<local-command-", "<system-reminder>", "<task-notification>")
MOTIVO = (
    "Varredura: este turno corrigiu um bug. Antes de encerrar, procure outras ocorrências do mesmo padrão "
    "no repo inteiro, partindo da raiz (`git rev-parse --show-toplevel`; fora de git, suba até a raiz do "
    "projeto), não da subpasta onde você estava. Use `rg` sem filtro de pasta e com variações: caixa, "
    "sinônimos, chamadas indiretas, e `rg -uu` quando arquivo ignorado puder ter o padrão. Corrija o que "
    "achar e diga a contagem final e onde buscou. Se não houver mais nenhuma, diga isso em uma linha."
)


def abre_turno(entrada):
    if entrada.get("type") != "user" or entrada.get("isMeta") or entrada.get("isSidechain"):
        return False
    conteudo = (entrada.get("message") or {}).get("content")
    if isinstance(conteudo, list):
        conteudo = "\n".join(b.get("text") or "" for b in conteudo if isinstance(b, dict) and b.get("type") == "text")
    texto = (conteudo or "").strip() if isinstance(conteudo, str) else ""
    return bool(texto) and not texto.startswith(NAO_HUMANO)


def precisa_varrer(entradas):
    debug = editou = False
    for entrada in reversed(entradas):
        if abre_turno(entrada):
            break
        if entrada.get("type") != "assistant" or entrada.get("isSidechain"):
            continue
        for bloco in (entrada.get("message") or {}).get("content") or []:
            if not isinstance(bloco, dict) or bloco.get("type") != "tool_use":
                continue
            if bloco.get("name") == "Skill" and str((bloco.get("input") or {}).get("skill", "")).endswith("systematic-debugging"):
                debug = True
            editou = editou or bloco.get("name") in EDICAO
    return debug and editou


def ler(caminho):
    entradas = []
    with open(caminho, encoding="utf-8", errors="replace") as fh:
        for linha in fh:
            try:
                entradas.append(json.loads(linha))
            except ValueError:
                continue
    return entradas


def main():
    try:
        dados = json.load(sys.stdin)
        if dados.get("stop_hook_active") or not precisa_varrer(ler(dados["transcript_path"])):
            return
    except Exception:
        return
    print(json.dumps({"decision": "block", "reason": MOTIVO}, ensure_ascii=False))


if __name__ == "__main__":
    main()
