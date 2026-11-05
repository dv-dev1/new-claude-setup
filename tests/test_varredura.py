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


def resultado():
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t", "content": "ok"}]}}


def meta():
    return {"type": "user", "isMeta": True, "message": {"content": [{"type": "text", "text": "Base directory for this skill"}]}}


def test_debug_e_edicao_no_turno_bloqueia():
    assert varredura.precisa_varrer([humano("corrige o bug"), debug(), resultado(), edit()]) is True


def test_debug_sem_edicao_nao_bloqueia():
    assert varredura.precisa_varrer([humano("por que quebra?"), debug(), resultado()]) is False


def test_edicao_sem_debug_nao_bloqueia():
    assert varredura.precisa_varrer([humano("renomeia"), edit()]) is False


def test_debug_em_turno_anterior_nao_bloqueia():
    assert varredura.precisa_varrer([humano("bug"), debug(), humano("agora troca o texto"), edit()]) is False


def test_tool_result_e_meta_nao_abrem_turno():
    assert varredura.precisa_varrer([humano("bug"), debug(), resultado(), meta(), edit()]) is True


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


def transcript(entradas):
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    fh.write("\n".join(json.dumps(e) for e in entradas) + "\nlinha quebrada{\n")
    fh.close()
    return fh.name


def test_main_stop_hook_active_nao_imprime():
    caminho = transcript([humano("bug"), debug(), edit()])
    assert rodar_main({"stop_hook_active": True, "transcript_path": caminho}) == ""


def test_main_transcript_inexistente_nao_imprime():
    assert rodar_main({"stop_hook_active": False, "transcript_path": "/nao/existe.jsonl"}) == ""


def test_main_bloqueia_imprime_json():
    caminho = transcript([humano("bug"), debug(), edit()])
    saida = json.loads(rodar_main({"stop_hook_active": False, "transcript_path": caminho}))
    assert saida["decision"] == "block"
    assert "raiz" in saida["reason"]


def test_compactar_cabe_em_500():
    texto = open(os.path.join(RAIZ, "hooks", "compactar.txt"), encoding="utf-8").read().strip()
    assert len(texto) <= 500, len(texto)
    for trecho in ("PENDING", "Context & Goal", "Open Questions"):
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
