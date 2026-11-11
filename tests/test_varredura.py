#!/usr/bin/env python3
"""Testes do hook de varredura e do texto de compactação. Rode: python3 tests/test_varredura.py"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("varredura", os.path.join(RAIZ, "hooks", "varredura.py"))
varredura = importlib.util.module_from_spec(spec)
spec.loader.exec_module(varredura)


def humano(texto):
    return {"type": "user", "message": {"content": texto}}


def ferramenta(nome, entrada=None):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t", "name": nome, "input": entrada or {}}]}}


def debug():
    return ferramenta("Skill", {"skill": "superpowers:systematic-debugging"})


def edit():
    return ferramenta("Edit", {"file_path": "/x.py"})


def resultado(**extra):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t", "content": "ok"}]}, **extra}


def meta(texto="Base directory for this skill"):
    return {"type": "user", "isMeta": True, "message": {"content": [{"type": "text", "text": texto}]}}


def test_debug_e_edicao_no_turno_bloqueia():
    assert varredura.precisa_varrer([humano("corrige o bug"), debug(), resultado(), edit()]) is True


def test_debug_sem_edicao_nao_bloqueia():
    assert varredura.precisa_varrer([humano("por que quebra?"), debug(), resultado()]) is False


def test_edicao_sem_debug_nao_bloqueia():
    assert varredura.precisa_varrer([humano("renomeia"), edit()]) is False


def test_correcao_no_turno_seguinte_ao_debug_bloqueia():
    assert varredura.precisa_varrer([humano("bug"), debug(), resultado(), humano("pode corrigir"), edit()]) is True


def test_debug_dois_turnos_atras_nao_bloqueia():
    assert varredura.precisa_varrer([humano("bug"), debug(), humano("e o log?"), ferramenta("Read"),
                                     humano("agora troca o texto"), edit()]) is False


def test_debug_anterior_que_ja_editou_nao_bloqueia():
    assert varredura.precisa_varrer([humano("bug"), debug(), edit(), humano("agora troca o texto"), edit()]) is False


def test_debug_anterior_por_slash_command_conta():
    comando = humano("<command-message>superpowers:systematic-debugging</command-message>\n"
                     "<command-name>/superpowers:systematic-debugging</command-name>")
    carga = meta("Base directory for this skill: /c/superpowers/7.0.1/skills/systematic-debugging\n\n# Systematic Debugging")
    assert varredura.precisa_varrer([comando, carga, humano("pode corrigir"), edit()]) is True


def test_varredura_no_turno_anterior_fecha_a_janela():
    feedback = {"type": "user", "isMeta": True, "message": {"content": "Stop hook feedback:\n" + varredura.MOTIVO}}
    assert varredura.precisa_varrer([humano("bug"), debug(), feedback, humano("e agora?"), edit()]) is False


def test_tool_result_e_meta_nao_abrem_turno():
    assert varredura.precisa_varrer([humano("bug"), debug(), resultado(), meta(), edit()]) is True


def test_varredura_anterior_fecha_a_janela():
    feedback = {"type": "user", "isMeta": True, "message": {"content": "Stop hook feedback:\n" + varredura.MOTIVO}}
    aviso = humano("<task-notification>\n<task-id>x</task-id>\n</task-notification>")
    assert varredura.precisa_varrer([humano("bug"), debug(), edit(), feedback, ferramenta("Bash"), aviso]) is False


def test_slash_command_abre_turno():
    comando = humano("<command-message>caveman-review</command-message>\n<command-name>/caveman-review</command-name>")
    assert varredura.precisa_varrer([humano("bug"), debug(), edit(), comando, edit()]) is False


def test_compactacao_no_meio_do_turno_nao_perde_o_debug():
    resumo = {"type": "user", "isCompactSummary": True,
              "message": {"content": "This session is being continued from a previous conversation."}}
    assert varredura.precisa_varrer([humano("bug"), debug(), resumo, edit()]) is True


def test_debug_digitado_como_slash_command_conta():
    comando = humano("<command-message>superpowers:systematic-debugging</command-message>\n"
                     "<command-name>/superpowers:systematic-debugging</command-name>")
    carga = meta("Base directory for this skill: /c/superpowers/7.0.1/skills/systematic-debugging\n\n# Systematic Debugging")
    assert varredura.precisa_varrer([comando, carga, edit()]) is True


def gravar(pasta, entradas, subagentes=None):
    """Transcript da sessão em `pasta`, com subagentes em `<sessao>/subagents/agent-<id>.jsonl`.
    Como no transcript real, toda entrada de subagente vem com `isSidechain: true`."""
    caminho = os.path.join(pasta, "sessao.jsonl")
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(e) for e in entradas) + "\nlinha quebrada{\n")
    for agente, linhas in (subagentes or {}).items():
        os.makedirs(os.path.join(pasta, "sessao", "subagents"), exist_ok=True)
        with open(os.path.join(pasta, "sessao", "subagents", f"agent-{agente}.jsonl"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(json.dumps({**e, "isSidechain": True}) for e in linhas))
    return caminho


def delegou(agente, status="completed"):
    return [ferramenta("Agent", {"prompt": "corrige"}), resultado(toolUseResult={"agentId": agente, "status": status})]


def aviso_de_termino(agente):
    return humano(f"<task-notification>\n<task-id>{agente}</task-id>\n<status>completed</status>\n</task-notification>")


def test_subagente_em_segundo_plano_que_termina_noutro_turno_conta():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("corrige o bug"), *delegou("abc", "async_launched"), humano("e aí?"),
                                 aviso_de_termino("abc")], {"abc": [humano("corrige"), debug(), edit()]})
        assert varredura.precisa_varrer(varredura.ler(caminho), caminho) is True


def test_lancamento_em_segundo_plano_nao_le_transcript_parcial():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("corrige o bug"), *delegou("abc", "async_launched")],
                         {"abc": [humano("corrige"), debug(), edit()]})
        assert varredura.precisa_varrer(varredura.ler(caminho), caminho) is False


def test_turno_sem_resposta_no_meio_nao_gasta_a_janela():
    for meio in (humano("[Request interrupted by user for tool use]"), humano("<bash-input>git status</bash-input>")):
        assert varredura.precisa_varrer([humano("bug"), debug(), meio, humano("pode corrigir"), edit()]) is True, meio


def test_feedback_da_varredura_corta_a_janela_no_mesmo_turno():
    feedback = {"type": "user", "isMeta": True, "message": {"content": "Stop hook feedback:\n" + varredura.MOTIVO}}
    assert varredura.precisa_varrer([humano("bug"), debug(), feedback, edit()]) is False


def test_debug_e_edicao_dentro_do_subagente_bloqueia():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("corrige o bug"), *delegou("abc")], {"abc": [humano("corrige"), debug(), edit()]})
        assert varredura.precisa_varrer(varredura.ler(caminho), caminho) is True


def test_subagente_com_debug_sem_edicao_nao_bloqueia():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("investiga"), *delegou("abc")], {"abc": [humano("investiga"), debug()]})
        assert varredura.precisa_varrer(varredura.ler(caminho), caminho) is False


def test_edicao_feita_por_subagente_conta():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("bug"), debug(), *delegou("abc")], {"abc": [humano("corrige"), edit()]})
        assert varredura.precisa_varrer(varredura.ler(caminho), caminho) is True


def test_subagente_que_so_le_nao_conta():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("bug"), debug(), *delegou("abc")], {"abc": [humano("procura"), ferramenta("Grep")]})
        assert varredura.precisa_varrer(varredura.ler(caminho), caminho) is False


def test_subagente_sem_transcript_nao_quebra():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("bug"), debug(), *delegou("sumiu")])
        assert varredura.precisa_varrer(varredura.ler(caminho), caminho) is False


def rodar_main(entrada):
    saida = io.StringIO()
    stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps(entrada))
    try:
        with contextlib.redirect_stdout(saida):
            varredura.main()
    finally:
        sys.stdin = stdin
    return saida.getvalue()


def test_main_stop_hook_active_nao_imprime():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("bug"), debug(), edit()])
        assert rodar_main({"stop_hook_active": True, "transcript_path": caminho}) == ""


def test_main_transcript_inexistente_nao_imprime():
    assert rodar_main({"stop_hook_active": False, "transcript_path": "/nao/existe.jsonl"}) == ""


def test_main_transcript_vazio_nao_imprime():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = os.path.join(pasta, "vazio.jsonl")
        open(caminho, "w").close()
        assert rodar_main({"stop_hook_active": False, "transcript_path": caminho}) == ""


def test_main_bloqueia_imprime_json():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("bug"), debug(), edit()])
        saida = json.loads(rodar_main({"stop_hook_active": False, "transcript_path": caminho}))
    assert saida["decision"] == "block"
    assert "raiz" in saida["reason"]


def test_main_bloqueia_com_edicao_de_subagente():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("bug"), debug(), *delegou("abc")], {"abc": [humano("corrige"), edit()]})
        assert json.loads(rodar_main({"stop_hook_active": False, "transcript_path": caminho}))["decision"] == "block"


def test_compactar_cabe_no_limite_do_precompact():
    texto = open(os.path.join(RAIZ, "hooks", "compactar.txt"), encoding="utf-8").read().strip()
    assert len(texto) <= 10000, len(texto)  # limite do Claude Code por saída de hook PreCompact
    for trecho in ("PENDING", "Context & Goal", "Open Questions"):
        assert trecho in texto, trecho


def test_compactar_e_o_prompt_integral_do_colega():
    texto = open(os.path.join(RAIZ, "hooks", "compactar.txt"), encoding="utf-8").read()
    for trecho in ("Preserve the following verbatim or near-verbatim:",
                   'Multiple failed attempts into "we tried some approaches"',
                   "Err on the side of keeping more rather than less. Length is not a concern."):
        assert trecho in texto, trecho


def test_compactar_guarda_fala_do_usuario_verificacao_e_nao_copia_segredo():
    texto = open(os.path.join(RAIZ, "hooks", "compactar.txt"), encoding="utf-8").read()
    for trecho in ("The user's own instructions, preferences, corrections, approvals and rejections",
                   "The user's latest request and the exact next action.",
                   "Commands run to verify work and their actual results",
                   "External state: branches, commit SHAs",
                   "Never copy secret values",
                   "User Instructions & Preferences",
                   "Verification Status"):
        assert trecho in texto, trecho


def test_compactar_segura_compactacao_repetida():
    texto = open(os.path.join(RAIZ, "hooks", "compactar.txt"), encoding="utf-8").read()
    for trecho in ("Inputs the user already provided",
                   "The user's last 3 messages verbatim.",
                   "Sources of truth on disk",
                   "Subagents and background tasks in flight",
                   "If a previous summary exists, carry its User Instructions & Preferences and PENDING items forward",
                   "Before finishing: re-scan every user message since the last summary",
                   "User-Provided Inputs"):
        assert trecho in texto, trecho


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
