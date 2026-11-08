#!/usr/bin/env python3
"""Checagem offline: ledger e parsing da resposta do Google Books, sem rede."""

import json
import os
import tempfile
from pathlib import Path

os.environ["LIVRO_CERTO_LEDGER"] = str(
    Path(tempfile.mkdtemp()) / "lidos.json"
)

import livro

RESPOSTA_PT = {
    "docs": [
        {
            "title": "Atomic Habits",
            "author_name": ["James Clear"],
            "language": ["eng", "por", "spa"],
            "first_publish_year": 2016,
            "number_of_pages_median": 323,
            "ratings_average": 3.974468,
            "ratings_count": 1410,
            "edition_count": 41,
        }
    ]
}


def _falso(resposta):
    livro._get = lambda url: resposta


n = 0


def check(cond, msg):
    global n
    assert cond, msg
    n += 1


_falso(RESPOSTA_PT)
r = livro.checar("Hábitos Atômicos", "James Clear")
check(r["achou"] and r["pt_br"], "\"por\" na lista de idiomas devia dar pt-BR")
check(r["nota"] == 4.0 and r["votos"] == 1410, "nota devia vir arredondada do payload")
check(r["paginas"] == 323 and r["edicoes"] == 41, "páginas e edições do payload")

_falso({"docs": [{"title": "X", "language": ["eng"]}]})
check(livro.checar("X")["pt_br"] is False, "só edição em inglês não é pt-BR")

_falso(
    {
        "docs": [
            {"title": "Mindset 6 Books Collection Set", "edition_count": 1},
            {"title": "Mindset", "language": ["por"], "edition_count": 37},
        ]
    }
)
check(livro.checar("Mindset")["titulo"] == "Mindset", "box-set devia perder para a obra")

_falso(
    {
        "docs": [
            {"title": "Mindset, The One Thing 4 Books Collection Set", "edition_count": 9},
            {"title": "Mindset", "language": ["por"], "edition_count": 2},
        ]
    }
)
check(
    livro.checar("Mindset")["pt_br"] is True,
    "box-set com mais edições ainda devia perder pelo título empilhado",
)

_falso({"docs": []})
check(livro.checar("Nada")["achou"] is False, "resposta vazia não acha nada")

livro._get = lambda url: (_ for _ in ()).throw(TimeoutError("timeout"))
check("erro" in livro.checar("Y"), "falha de rede devia virar erro, não exceção")

livro.registrar("Hábitos Atômicos", "James Clear", "prescrito", motivo="disciplina")
livro.registrar("HABITOS ATOMICOS!", status="abandonado", nota="repetitivo")
h = livro.historico()
check(len(h) == 1, f"pontuação e caixa deviam colidir na mesma chave, veio {len(h)}")
check(
    h[0]["status"] == "abandonado" and h[0]["motivo"] == "disciplina",
    "atualizar status devia preservar o motivo original",
)

print(f"ok — {n} checagens")
