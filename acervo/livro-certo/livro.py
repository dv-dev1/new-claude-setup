#!/usr/bin/env python3
"""Ledger de leitura e checagem de edição em português para a skill livro-certo."""

import argparse
import json
import os
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

LEDGER = Path(
    os.environ.get(
        "LIVRO_CERTO_LEDGER", Path.home() / ".local/share/livro-certo/lidos.json"
    )
)
API = "https://openlibrary.org/search.json"
STATUS = ("prescrito", "lendo", "lido", "abandonado", "rejeitado")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "livro-certo/1"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _carregar():
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _salvar(livros):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(
        json.dumps(livros, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def chave(titulo):
    sem_acento = unicodedata.normalize("NFKD", titulo.lower())
    return "".join(c for c in sem_acento if c.isalnum() and not unicodedata.combining(c))


def checar(titulo, autor=""):
    """Tem edição em português? Quantas páginas, que nota, quantas edições?"""
    q = f'title:"{titulo}"' + (f' author:"{autor}"' if autor else "")
    url = API + "?" + urllib.parse.urlencode(
        {
            "q": q,
            "limit": 3,
            "fields": "title,author_name,first_publish_year,number_of_pages_median,"
            "ratings_average,ratings_count,language,edition_count",
        }
    )
    try:
        docs = _get(url).get("docs") or []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return {"erro": str(e)}
    if not docs:
        return {"achou": False, "pt_br": False, "titulo": titulo, "autores": autor}
    # Busca por título casa também com box-set ("Mindset, The One Thing 4 Books
    # Collection Set"), que empilha títulos e some com o livro pedido.
    curtos = [d for d in docs if len(d.get("title", "")) < 3 * len(titulo) + 20]
    if not curtos:
        return {"achou": False, "pt_br": False, "titulo": titulo, "autores": autor}
    d = max(curtos, key=lambda x: x.get("edition_count") or 0)
    return {
        "achou": True,
        # ponytail: "por" na lista de idiomas prova edição em português, não
        # presença na loja Kindle BR. Livro antigo pode ter só edição de papel.
        "pt_br": "por" in (d.get("language") or []),
        "titulo": d.get("title", titulo),
        "autores": ", ".join(d.get("author_name", [])) or autor,
        "ano": d.get("first_publish_year") or "?",
        "paginas": d.get("number_of_pages_median") or 0,
        "nota": round(d.get("ratings_average") or 0, 1),
        "votos": d.get("ratings_count") or 0,
        "edicoes": d.get("edition_count") or 0,
    }


def registrar(titulo, autor="", status="prescrito", motivo="", nota=""):
    if status not in STATUS:
        raise ValueError(f"status inválido: {status}. Use um de {', '.join(STATUS)}")
    livros = _carregar()
    k = chave(titulo)
    novo = {
        "chave": k,
        "titulo": titulo,
        "autor": autor,
        "status": status,
        "motivo": motivo,
        "nota": nota,
        "data": date.today().isoformat(),
    }
    for i, l in enumerate(livros):
        if l["chave"] == k:
            novo["motivo"] = motivo or l.get("motivo", "")
            novo["autor"] = autor or l.get("autor", "")
            livros[i] = novo
            break
    else:
        livros.append(novo)
    _salvar(livros)
    return novo


def historico():
    return _carregar()


def _fmt_checar(r):
    if "erro" in r:
        return f"erro na consulta: {r['erro']}"
    if not r["achou"]:
        return (
            f'"{r["titulo"]}" não consta no Open Library. Isso não prova que não '
            f"existe em português: tente o título brasileiro, ou confirme por busca."
        )
    nota = f'{r["nota"]}/5 ({r["votos"]} votos)' if r["votos"] else "sem nota"
    pt = "sim" if r["pt_br"] else "não consta (confirme pelo título brasileiro)"
    return (
        f'pt-BR: {pt} — "{r["titulo"]}" '
        f'({r["autores"]}, {r["ano"]}) | {r["paginas"]} páginas '
        f'| nota: {nota} | {r["edicoes"]} edições'
    )


def _fmt_historico(livros):
    if not livros:
        return "ledger vazio"
    return "\n".join(
        f'{l["data"]} [{l["status"]}] {l["titulo"]}'
        + (f' — {l["autor"]}' if l["autor"] else "")
        + (f' | motivo: {l["motivo"]}' if l.get("motivo") else "")
        + (f' | nota: {l["nota"]}' if l.get("nota") else "")
        for l in livros
    )


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("checar", help="tem edição em português?")
    c.add_argument("titulo")
    c.add_argument("--autor", default="")

    r = sub.add_parser("registrar", help="grava ou atualiza um livro no ledger")
    r.add_argument("titulo")
    r.add_argument("--autor", default="")
    r.add_argument("--status", default="prescrito", choices=STATUS)
    r.add_argument("--motivo", default="", help="o problema que motivou a prescrição")
    r.add_argument("--nota", default="", help="o que ele achou, depois de ler")

    sub.add_parser("historico", help="tudo que já foi prescrito, lido ou rejeitado")

    a = p.parse_args(argv)
    if a.cmd == "checar":
        print(_fmt_checar(checar(a.titulo, a.autor)))
    elif a.cmd == "registrar":
        l = registrar(a.titulo, a.autor, a.status, a.motivo, a.nota)
        print(f'gravado: [{l["status"]}] {l["titulo"]} em {LEDGER}')
    else:
        print(_fmt_historico(historico()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
