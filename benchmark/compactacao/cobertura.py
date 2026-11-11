#!/usr/bin/env python3
"""Cobertura da compactação: quanto dos arquivos editados e dos SHAs citados no trecho compactado aparece no
resumo. Só lê transcripts. Uso: python3 benchmark/compactacao/cobertura.py [--desde 2026-11-11] [--raiz DIR]"""
import argparse
import glob
import json
import os
import re

EDICAO = {"Edit", "Write", "MultiEdit"}
SHA = re.compile(r"\b[0-9a-f]{7,10}\b")


def texto_do_resumo(entrada):
    conteudo = (entrada.get("message") or {}).get("content")
    if isinstance(conteudo, list):
        return "\n".join(b.get("text") or "" for b in conteudo if isinstance(b, dict))
    return conteudo if isinstance(conteudo, str) else ""


def cobertura(caminhos, desde):
    r = {"compactacoes": 0, "arquivos": (0, 0), "shas": (0, 0)}
    for caminho in caminhos:
        arquivos, shas = set(), set()
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            for linha in fh:
                try:
                    e = json.loads(linha)
                except ValueError:
                    continue
                if e.get("isCompactSummary"):
                    # O trecho de cada resumo vai do resumo anterior até ele; resumo fora da data só fecha o trecho.
                    if e.get("timestamp", "") >= desde:
                        resumo = texto_do_resumo(e)
                        a, b = r["arquivos"]
                        r["arquivos"] = (a + sum(os.path.basename(p) in resumo for p in arquivos), b + len(arquivos))
                        a, b = r["shas"]
                        r["shas"] = (a + sum(s in resumo for s in shas), b + len(shas))
                        r["compactacoes"] += 1
                    arquivos, shas = set(), set()
                    continue
                if e.get("type") != "assistant":
                    continue
                for bloco in (e.get("message") or {}).get("content") or []:
                    if not isinstance(bloco, dict):
                        continue
                    if bloco.get("type") == "tool_use" and bloco.get("name") in EDICAO:
                        p = (bloco.get("input") or {}).get("file_path")
                        if p:
                            arquivos.add(p)
                    elif bloco.get("type") == "text":
                        shas.update(s for s in SHA.findall(bloco.get("text") or "")
                                    if re.search(r"[a-f]", s) and re.search(r"\d", s))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2026-11-11")
    ap.add_argument("--raiz", default=os.path.expanduser("~/.claude/projects"))
    args = ap.parse_args()
    r = cobertura(glob.glob(os.path.join(args.raiz, "*", "*.jsonl")), args.desde)  # só sessões principais
    print(f"compactações: {r['compactacoes']}")
    for nome in ("arquivos", "shas"):
        a, b = r[nome]
        print(f"{nome}: {a}/{b} ({a / b:.0%})" if b else f"{nome}: 0/0")


if __name__ == "__main__":
    main()
