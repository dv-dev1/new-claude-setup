#!/usr/bin/env python3
"""Stop: turno que rodou systematic-debugging e editou arquivo volta uma vez para varrer o repo
inteiro atrás de outras ocorrências do bug. Conta também o debug feito dentro de subagente (o de
segundo plano conta no turno do aviso de término) e o debug do turno anterior que não editou (a
correção veio agora, no "pode corrigir"). Erro de leitura libera o turno, nunca o trava."""
import json
import os
import re
import sys

EDICAO = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
# Chega como `user` mas não abre turno: saída de comando local, lembrete e aviso de tarefa.
# Eco de slash command abre: é fala humana.
NAO_HUMANO = ("<local-command-", "<system-reminder>", "<task-notification>")
CARGA_DE_SKILL = "Base directory for this skill:"
MOTIVO = (
    "Varredura: este turno corrigiu um bug. Antes de encerrar, procure outras ocorrências do mesmo padrão "
    "no repo inteiro, partindo da raiz (`git rev-parse --show-toplevel`; fora de git, suba até a raiz do "
    "projeto), não da subpasta onde você estava. Use `rg` sem filtro de pasta e com variações: caixa, "
    "sinônimos, chamadas indiretas, e `rg -uu` quando arquivo ignorado puder ter o padrão. Corrija o que "
    "achar e diga a contagem final e onde buscou. Se não houver mais nenhuma, diga isso em uma linha."
)


def texto(entrada):
    conteudo = (entrada.get("message") or {}).get("content")
    if isinstance(conteudo, list):
        conteudo = "\n".join(b.get("text") or "" for b in conteudo if isinstance(b, dict) and b.get("type") == "text")
    return conteudo.strip() if isinstance(conteudo, str) else ""


def abre_turno(entrada):
    # O feedback desta varredura fecha a janela: o que veio antes já foi varrido.
    if entrada.get("isMeta") and MOTIVO[:40] in texto(entrada):
        return True
    # O resumo de compactação não é fala humana: o turno segue antes dele no mesmo arquivo.
    if entrada.get("type") != "user" or entrada.get("isMeta") or entrada.get("isSidechain") or entrada.get("isCompactSummary"):
        return False
    corpo = texto(entrada)
    return bool(corpo) and not corpo.startswith(NAO_HUMANO)


def ferramentas(entrada, subagente=False):
    # No transcript do subagente toda entrada vem com isSidechain; só no da sessão a flag marca eco a ignorar.
    if entrada.get("type") != "assistant" or (entrada.get("isSidechain") and not subagente):
        return []
    blocos = (entrada.get("message") or {}).get("content") or []
    return [b for b in blocos if isinstance(b, dict) and b.get("type") == "tool_use"]


def sinais(entradas, caminho, subagente=False):
    """(debug, editou) das entradas e, no transcript da sessão, dos subagentes lançados nelas."""
    debug = editou = False
    for entrada in entradas:
        corpo = texto(entrada) if entrada.get("isMeta") else ""
        # Skill chamada pela ferramenta ou digitada como /superpowers:systematic-debugging carrega igual.
        if corpo.startswith(CARGA_DE_SKILL) and corpo.splitlines()[0].rstrip("/").endswith("systematic-debugging"):
            debug = True
        for bloco in ferramentas(entrada, subagente):
            if bloco.get("name") == "Skill" and str((bloco.get("input") or {}).get("skill", "")).endswith("systematic-debugging"):
                debug = True
            editou = editou or bloco.get("name") in EDICAO
        resultado = entrada.get("toolUseResult")
        # Lançado em segundo plano ainda roda e o transcript é parcial: conta no aviso de término, que traz o id.
        agente = resultado.get("agentId") if isinstance(resultado, dict) and resultado.get("status") != "async_launched" else None
        aviso = re.match(r"<task-notification>\s*<task-id>([\w-]+)</task-id>", texto(entrada)) if entrada.get("type") == "user" else None
        agente = agente or (aviso and aviso.group(1))
        if caminho and not subagente and agente:
            debug_sub, editou_sub = sinais_do_subagente(caminho, str(agente))
            debug, editou = debug or debug_sub, editou or editou_sub
    return debug, editou


def sinais_do_subagente(caminho, agente):
    # O Claude Code grava cada subagente em <sessão>/subagents/agent-<id>.jsonl, ao lado do transcript.
    arquivo = os.path.join(os.path.splitext(caminho)[0], "subagents", f"agent-{agente}.jsonl")
    try:
        return sinais(ler(arquivo), caminho, subagente=True)
    except OSError:
        return False, False


def precisa_varrer(entradas, caminho=None):
    atual, anterior = [], []
    alvo = atual
    for entrada in reversed(entradas):
        if abre_turno(entrada):
            # isMeta aqui só pode ser o feedback da varredura: fecha a janela. Fala humana passa ao turno anterior;
            # turno sem resposta do modelo (/comando, !cmd, interrupção) não gasta a janela.
            if entrada.get("isMeta") or (alvo is anterior and any(e.get("type") == "assistant" for e in anterior)):
                break
            alvo = anterior
            continue
        alvo.append(entrada)
    debug, editou = sinais(atual, caminho)
    if editou and not debug:
        # Debug sem correção no turno anterior: esta edição é a correção ("pode corrigir").
        debug_anterior, editou_anterior = sinais(anterior, caminho)
        debug = debug_anterior and not editou_anterior
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
        caminho = dados["transcript_path"]
        if dados.get("stop_hook_active") or not precisa_varrer(ler(caminho), caminho):
            return
    except Exception:
        return
    print(json.dumps({"decision": "block", "reason": MOTIVO}, ensure_ascii=False))


if __name__ == "__main__":
    main()
