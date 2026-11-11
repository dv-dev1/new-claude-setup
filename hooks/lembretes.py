#!/usr/bin/env python3
"""UserPromptSubmit: os lembretes de superpowers, ponytail e caveman só em fala humana. Aviso de tarefa,
saída de comando local e lembrete do sistema também chegam como prompt e não ganham lembrete."""
import json
import sys

# Mesma tupla do varredura.py: chega como prompt, mas não é fala humana.
NAO_HUMANO = ("<local-command-", "<system-reminder>", "<task-notification>")
LEMBRETES = (
    "SUPERPOWERS: as unicas skills de ciclo de engenharia do usuario sao as superpowers:*. Antes de agir, decida se alguma se aplica (brainstorming, systematic-debugging, test-driven-development, writing-plans, verification-before-completion etc.) e invoque-a com a ferramenta Skill. Pergunta simples nao e excecao. Use em silencio: nao anuncie a skill nem escreva linha Superpowers: na resposta. Projeto novo ou decisao cara de desfazer: skill arquitetura antes de codar. Caveman/Ponytail nao autorizam pular.",
    "PONYTAIL: ao escrever codigo, faca a menor mudanca que resolve a tarefa por completo. Reuse o que ja existe no codebase/stdlib/dependencias instaladas; sem abstracao, opcao ou codigo para depois que ninguem pediu. Nunca corte validacao, tratamento de erro, seguranca ou testes necessarios. Ponytail define o tamanho do codigo, nao o processo: nao autoriza pular skill do superpowers.",
    "CAVEMAN MODE ACTIVE (caveman). Respond terse like smart caveman. All technical substance stay. Only fluff die. Answer only what was asked: no unrequested background, lists, examples, walkthroughs, or follow-up offers; give code, steps, or warnings when the task needs them. Security warnings, irreversible actions, multi-step order: normal prose. Technical terms, code, commands, paths, and errors stay exact.",
)


def main():
    try:
        prompt = json.load(sys.stdin).get("prompt") or ""
    except Exception:
        prompt = ""  # erro de leitura não cala o lembrete
    if prompt.lstrip().startswith(NAO_HUMANO):
        return
    contexto = "\n\n".join(LEMBRETES)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": contexto}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
