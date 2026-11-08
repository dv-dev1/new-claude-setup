#!/usr/bin/env python3
"""Testes do setup fora da varredura: hooks do caveman e acervo. Rode: python3 tests/test_setup.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAVEMAN = os.path.join(RAIZ, "hooks", "caveman.md")
LEMBRETE = ("CAVEMAN MODE ACTIVE (caveman). Respond terse like smart caveman. All technical substance stay. "
            "Only fluff die. Answer only what was asked: no unrequested background, lists, examples, walkthroughs, "
            "or follow-up offers; give code, steps, or warnings when the task needs them. Security warnings, "
            "irreversible actions, multi-step order: normal prose. Technical terms, code, commands, paths, "
            "and errors stay exact.")


def comandos(evento):
    with open(os.path.join(RAIZ, "settings.json"), encoding="utf-8") as fh:
        hooks = json.load(fh).get("hooks", {})
    return [h["command"] for grupo in hooks.get(evento, []) for h in grupo.get("hooks", [])]


def saidas(evento):
    """Saída de cada hook do evento, num HOME de mentira onde o install.sh já ligou o caveman.md."""
    with tempfile.TemporaryDirectory() as home:
        os.makedirs(os.path.join(home, ".claude", "hooks"))
        shutil.copy(CAVEMAN, os.path.join(home, ".claude", "hooks", "caveman.md"))
        return [subprocess.run(["sh", "-c", c], env={**os.environ, "HOME": home}, capture_output=True,
                               text=True, check=True).stdout for c in comandos(evento)]


def conteudo():
    with open(CAVEMAN, encoding="utf-8") as fh:
        return fh.read()


def test_sessionstart_imprime_o_caveman():
    assert conteudo() in saidas("SessionStart")


def test_subagentstart_emite_json_do_caveman():
    esperado = {"hookEventName": "SubagentStart", "additionalContext": conteudo()}
    assert esperado in [json.loads(s)["hookSpecificOutput"] for s in saidas("SubagentStart")]


def test_lembrete_caveman_por_mensagem():
    assert LEMBRETE in [json.loads(s)["hookSpecificOutput"]["additionalContext"] for s in saidas("UserPromptSubmit")]


if __name__ == "__main__":
    falhas = 0
    for nome, teste in sorted(globals().items()):
        if nome.startswith("test_"):
            try:
                teste()
                print("ok  ", nome)
            except Exception as erro:
                falhas += 1
                print("FALHA", nome, repr(erro))
    sys.exit(1 if falhas else 0)
