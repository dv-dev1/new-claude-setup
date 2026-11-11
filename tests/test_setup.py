#!/usr/bin/env python3
"""Testes do setup fora da varredura: hooks do caveman e acervo. Rode: python3 tests/test_setup.py"""
import json
import os
import re
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


def saidas(evento, entrada=""):
    """Saída de cada hook do evento, num HOME de mentira onde o install.sh já ligou os hooks."""
    with tempfile.TemporaryDirectory() as home:
        os.makedirs(os.path.join(home, ".claude", "hooks"))
        shutil.copy(CAVEMAN, os.path.join(home, ".claude", "hooks", "caveman.md"))
        shutil.copy(os.path.join(RAIZ, "hooks", "lembretes.py"), os.path.join(home, ".claude", "hooks", "lembretes.py"))
        return [subprocess.run(["sh", "-c", c], env={**os.environ, "HOME": home}, input=entrada, capture_output=True,
                               text=True, check=True).stdout for c in comandos(evento)]


def conteudo():
    with open(CAVEMAN, encoding="utf-8") as fh:
        return fh.read()


def test_sessionstart_imprime_o_caveman():
    assert conteudo() in saidas("SessionStart")


def test_subagentstart_emite_json_do_caveman():
    esperado = {"hookEventName": "SubagentStart", "additionalContext": conteudo()}
    assert esperado in [json.loads(s)["hookSpecificOutput"] for s in saidas("SubagentStart")]


def lembretes(prompt=None, cru=None):
    entrada = cru if cru is not None else json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt})
    return [json.loads(s)["hookSpecificOutput"]["additionalContext"] for s in saidas("UserPromptSubmit", entrada) if s.strip()]


def test_lembrete_caveman_por_mensagem():
    textos = lembretes("corrige o bug")
    assert len(textos) == 1 and LEMBRETE in textos[0]
    assert "SUPERPOWERS: as unicas skills" in textos[0] and "PONYTAIL: ao escrever codigo" in textos[0]


def test_lembrete_calado_em_aviso_de_tarefa():
    assert lembretes("<task-notification>\n<task-id>a1</task-id>") == []
    assert lembretes("  \n<task-notification><task-id>a1</task-id>") == []
    assert lembretes("<local-command-stdout>ok</local-command-stdout>") == []


def test_lembrete_sai_em_fala_que_so_cita_o_aviso():
    assert len(lembretes("o que é <task-notification>?")) == 1


def test_lembrete_falha_aberto():
    assert len(lembretes(cru="nao e json")) == 1
    assert len(lembretes(cru="{}")) == 1


ACERVO = os.path.join(RAIZ, "acervo")


def pastas_do_acervo():
    """(nome, caminho) de cada skill do acervo: acervo/<nome>/ e acervo/caveman/<nome>/."""
    pastas = []
    for base in (ACERVO, os.path.join(ACERVO, "caveman")):
        for nome in sorted(os.listdir(base)):
            caminho = os.path.join(base, nome)
            if os.path.isdir(caminho) and caminho != os.path.join(ACERVO, "caveman"):
                pastas.append((nome, caminho))
    return pastas


def test_acervo_listado_no_claude_global():
    with open(os.path.join(RAIZ, "CLAUDE.global.md"), encoding="utf-8") as fh:
        linha = next(l for l in fh if l.startswith("- Acervo:"))
    pastas = pastas_do_acervo()
    assert pastas
    for nome, caminho in pastas:
        assert os.path.isfile(os.path.join(caminho, "SKILL.md")), nome
        assert re.search(rf"(?<![\w-]){re.escape(nome)}(?![\w-])", linha), nome


def test_acervo_sem_caminho_de_skill_ativa():
    arquivos = [os.path.join(raiz, a) for raiz, _, nomes in os.walk(ACERVO) for a in nomes]
    assert arquivos
    velhos = []
    for arquivo in arquivos:
        with open(arquivo, encoding="utf-8", errors="ignore") as fh:
            if "~/.claude/skills/" in fh.read():
                velhos.append(os.path.relpath(arquivo, ACERVO))
    assert not velhos, velhos


def test_settings_corte_de_overhead():
    with open(os.path.join(RAIZ, "settings.json"), encoding="utf-8") as fh:
        s = json.load(fh)
    assert s["autoCompactWindow"] == 350000
    assert s["modelSettings"] == {"claude-opus-5-5": {"effortLevel": "high"},
                                  "claude-sonnet-5-5": {"effortLevel": "high"},
                                  "claude-fable-5-2": {"effortLevel": "medium"}}
    escondidas = ["code-review", "simplify", "loop", "schedule", "init", "security-review",
                  "fewer-permission-prompts", "keybindings-help", "plugin-authoring", "run",
                  "anthropic-skills:skill-creator", "anthropic-skills:docs", "anthropic-skills:docx",
                  "anthropic-skills:pptx"]
    assert all(s["skillOverrides"][n] == "user-invocable-only" for n in escondidas)
    assert s["skillOverrides"]["anthropic-skills:morning"] == "off"
    assert set(s["permissions"]["deny"]) == {"mcp__claude_ai_Gmail", "mcp__claude_ai_Google_Calendar",
                                             "mcp__claude_ai_Claude_Docs"}
    with open(os.path.join(RAIZ, "CLAUDE.global.md"), encoding="utf-8") as fh:
        assert "- Re-review" in fh.read()


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
