#!/usr/bin/env python3
"""Testes do medidor de cobertura da compactação. Rode: python3 tests/test_cobertura.py"""
import importlib.util
import json
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("cobertura", os.path.join(RAIZ, "benchmark", "compactacao", "cobertura.py"))
cobertura = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cobertura)


def edit(caminho, texto=""):
    blocos = [{"type": "tool_use", "id": "t", "name": "Edit", "input": {"file_path": caminho}}]
    if texto:
        blocos.append({"type": "text", "text": texto})
    return json.dumps({"type": "assistant", "message": {"content": blocos}})


RESUMO = json.dumps({"type": "user", "isCompactSummary": True, "timestamp": "2026-11-12T00:00:00Z",
                     "message": {"content": [{"type": "text", "text": "mexi em a.py no 1a2b3c4"}]}})


def gravar(pasta, nome, linhas):
    caminho = os.path.join(pasta, nome)
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write("\n".join(linhas) + "\n")
    return caminho


def test_cobertura_conta_so_o_trecho_antes_do_resumo():
    with tempfile.TemporaryDirectory() as pasta:
        f = gravar(pasta, "s.jsonl", [edit("/r/a.py"), edit("/r/b.py", "commit 1a2b3c4"), "{corrompida", RESUMO, edit("/r/c.py")])
        r = cobertura.cobertura([f], "2026-11-11")
    assert r["compactacoes"] == 1
    assert r["arquivos"] == (1, 2)
    assert r["shas"] == (1, 1)


def test_cobertura_ignora_resumo_antes_da_data_e_sessao_sem_resumo():
    with tempfile.TemporaryDirectory() as pasta:
        f = gravar(pasta, "s.jsonl", [edit("/r/a.py"), RESUMO])
        sem = gravar(pasta, "t.jsonl", [edit("/r/a.py")])
        assert cobertura.cobertura([f], "2026-11-13")["compactacoes"] == 0
        assert cobertura.cobertura([sem], "2026-11-11")["compactacoes"] == 0


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
