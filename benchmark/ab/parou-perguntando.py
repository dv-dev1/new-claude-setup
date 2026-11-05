#!/usr/bin/env python3
"""Uso: parou-perguntando.py <stream.jsonl>. Imprime o session_id e sai 0 se a sessão terminou numa pergunta."""
import json
import sys


def resultado(caminho):
    with open(caminho, encoding="utf-8", errors="replace") as arquivo:
        for linha in arquivo:
            try:
                evento = json.loads(linha)
            except ValueError:
                continue
            if evento.get("type") == "result":
                return evento
    return None


if __name__ == "__main__":
    evento = resultado(sys.argv[1])
    # qualquer linha terminando em "?": o brainstorming fecha com a oferta "ou se preferir, comece logo"
    # qualquer "?" na fala final: o run-one só retoma se a árvore ficou intocada, então não há falso retorno com código feito
    if not evento or "?" not in (evento.get("result") or ""):
        sys.exit(1)
    print(evento["session_id"])
