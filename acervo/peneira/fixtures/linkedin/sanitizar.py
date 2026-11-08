#!/usr/bin/env python3
"""Gera as fixtures do LinkedIn sem dado pessoal: python3 sanitizar.py [pasta das capturas cruas]."""

import bisect
import html
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PENEIRA = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, PENEIRA)
import linkedin

JANELA = 20000
REGRAS = [
    (r"ajax:\d+", "ajax:0000000000000000000"),
    (r"ACoAA[\w-]+", "ACoAAFAKE"),
    (r'([tT]racking(?:Id|Code)\\*"\s*:\s*\\*")[^"\\]+', r"\g<1>FAKE=="),
    (r'(treeId\\*"\s*:\s*\\*")[^"\\]+', r"\g<1>FAKE=="),
    (r"(trackingId=)[^&\"\\\s]+", r"\g<1>FAKE"),
    (r"(x-li-ambry-ep=)[^&\"\\\s]+", r"\g<1>FAKE"),
    (r"(&mt=)[^&\"\\\s]+", r"\g<1>FAKE"),
    (r"https://media\.licdn\.com/[^\"\\\s]+", "https://media.licdn.com/FAKE"),
    (r'(canonicalMemberId\\*"\s*:\s*\\*")\d+', r"\g<1>1000000001"),
    # Cartão do perfil no formulário: o bloco com maxLineCountExpression 5 é o headline.
    (r'("maxLineCountExpression":5,[^\]]*?"children":\[")[^"\\]+', r"\g<1>Engenheiro de Teste"),
    (r"Candidato_Teste_\w+\.pdf", "Candidato_Teste_CV.pdf"),
]


def segredos():
    with open(os.path.join(PENEIRA, "respostas.json"), encoding="utf-8") as f:
        r = json.load(f)
    dig = re.sub(r"\D", "", r["telefone"])
    return [(r["email"], "candidato@example.com"), (r["telefone"], "(83) 90000-0000"),
            (dig, "83900000000"), (f"{dig[2:7]}-{dig[7:]}", "90000-0000"),
            (dig[2:], "900000000"), (r["nome"], "Candidato Teste"),
            (r["nome"].replace(" ", "_"), "Candidato_Teste"),
            (r["linkedin"].rstrip("/").rsplit("/", 1)[-1], "candidato-teste"),
            (r["cidade"].split(",")[0], "Cidade Teste"),
            *[(parte, "Teste") for parte in r["nome"].split()]]


def sanear(texto, mapa):
    for real, falso in sorted(segredos(), key=lambda par: -len(par[0])):
        texto = texto.replace(real, falso)
    for padrao, troca in REGRAS:
        texto = re.sub(padrao, troca, texto)
    # O mesmo id real vira sempre o mesmo id falso, para os corpos continuarem
    # coerentes entre upload e submit.
    return re.sub(r"/AA[A-Za-z0-9_-]{20,}\.pdf",
                  lambda m: mapa.setdefault(m.group(0), f"/AAFAKE{len(mapa)}.pdf"), texto)


def sanear_rsc(texto, mapa):
    """Linha T do RSC guarda o comprimento em bytes: trocar a URL exige reescrevê-lo."""
    bruto, saida, pos = texto.encode(), [], 0
    for m in re.finditer(rb"(?m)^([0-9a-f]+):T([0-9a-f]+),", bruto):
        if m.start() < pos:
            continue
        fim = m.end() + int(m.group(2), 16)
        conteudo = sanear(bruto[m.end():fim].decode(), mapa).encode()
        saida += [sanear(bruto[pos:m.start()].decode(), mapa).encode(),
                  m.group(1) + b":T" + format(len(conteudo), "x").encode() + b"," + conteudo]
        pos = fim
    saida.append(sanear(bruto[pos:].decode(), mapa).encode())
    return b"".join(saida).decode()


def recorte_rsc(rsc):
    """O RSC do formulário passa de 10 MB, quase tudo radios repetidos. Ficam as linhas
    inteiras que cobrem os 20 000 caracteres após cada "prefix" (janela do rótulo), os
    validadores, os ServerRequest do easyapply, a primeira linha de cada chave ea.q::
    e os SetState Yes/No das perguntas de escolha."""
    inicios, pos = [], 0
    for linha in rsc.split("\n"):
        inicios.append(pos)
        pos += len(linha) + 1
    onde = lambda p: bisect.bisect_right(inicios, p) - 1
    ficam = set()
    for m in re.finditer(r'"prefix":"', rsc):
        ficam.update(range(onde(m.start()), onde(m.start() + JANELA) + 1))
    for padrao in (r"RegexValidator", r'"requestId":"com\.linkedin\.sdui\.requests\.jobseeker\.easyapply\.'):
        ficam.update(onde(m.start()) for m in re.finditer(padrao, rsc))
    primeiras = {}
    for m in re.finditer(r"ea\.q::\d+::[A-Z_]+::\w+", rsc):
        primeiras.setdefault(m.group(0), onde(m.start()))
    ficam.update(primeiras.values())
    # Pergunta de escolha (chave com irmã _label): os SetState Yes/No dos radios dão o valor a enviar.
    for chave in (c for c in primeiras if c + "_label" in primeiras):
        for m in re.finditer(re.escape(chave) + r'"\}\}\},"value":\{"\$case":"stringValue","stringValue":"(?:Yes|No)"', rsc):
            ficam.add(onde(m.start()))
    recorte = "\n".join(rsc.split("\n")[i] for i in sorted(ficam))
    for m in re.finditer(r'"prefix":"', rsc):
        assert rsc[m.start():m.start() + JANELA] in recorte, "janela do rótulo cortada"
    return recorte


def main(captura):
    mapa = {}

    def ler(nome):
        with open(os.path.join(captura, nome), encoding="utf-8") as f:
            return f.read()

    def gravar(nome, texto):
        with open(os.path.join(AQUI, nome), "w", encoding="utf-8") as f:
            f.write(texto)

    def par(e):
        return {"corpo": json.loads(sanear(e["req"], mapa)), "resposta": sanear_rsc(e["res"], mapa)}

    pagina = html.unescape(ler("search.html"))
    vagas = [json.JSONDecoder().raw_decode(pagina, m.start())[0]
             for m in re.finditer(r'\{"trackingUrn":"urn:li:jobPosting:\d+"', pagina)]
    gravar("busca.html", "".join(
        "<code>" + html.escape(json.dumps({"trackingUrn": v["trackingUrn"], "title": v["title"]},
                                          ensure_ascii=False, separators=(",", ":"))) + "</code>\n"
        for v in vagas))

    for origem, destino in (("view.html", "vaga.html"), ("view_externa.html", "vaga_externa.html")):
        cru = ler(origem)
        recorte = linkedin.recorte_vaga(cru)
        assert linkedin.detalhe_da_vaga(recorte) == linkedin.detalhe_da_vaga(cru), origem
        gravar(destino, sanear(recorte, mapa))

    nav = json.loads(ler("cap_navegacao.json"))
    rotulos = json.loads(ler("rotulos.json"))
    recorte = recorte_rsc(nav["res"])
    assert all(r in recorte for r in rotulos), "pergunta fora do recorte"
    gravar("formulario.rsc", sanear_rsc(recorte_rsc(ler("rsc.txt")), mapa))
    gravar("formulario_rotulos.rsc", sanear_rsc(recorte, mapa))
    gravar("rotulos.json", sanear(json.dumps(rotulos, ensure_ascii=False, indent=1), mapa))
    gravar("navegacao.json", sanear(json.dumps(
        {"job_id": nav["job_id"], "empresa": nav["empresa"], "url": nav["url"],
         "corpo": json.loads(nav["req"])}, ensure_ascii=False, indent=1), mapa))

    upload = [e for e in json.loads(ler("cap_upload.json")) if e.get("hdr")]
    etapas = {"escolher": "handlePickedFile", "url": "getAmbryUploadUrl",
              "vincular": "setResumeFormBinding"}
    gravar("upload.json", json.dumps(
        {k: par(next(e for e in upload if nome in e["url"])) for k, nome in etapas.items()},
        ensure_ascii=False, indent=1))
    submit = next(e for e in json.loads(ler("cap_submit.json")) if e.get("hdr"))
    gravar("submit.json", json.dumps(par(submit), ensure_ascii=False, indent=1))

    # O Ambry é um POST XHR: o id do currículo volta no header `location`, não no corpo.
    put = json.loads(ler("cap_ambry_put.json"))
    uteis = [h for h in put["headers"]["raw"].split("\r\n")
             if h.split(":")[0].lower() in ("location", "content-length")]
    gravar("ambry_put.json", sanear(json.dumps(
        {"method": put["method"], "req_hdr": put["req_hdr"], "status": put["status"],
         "headers": {"raw": "\r\n".join(uteis) + "\r\n"}, "text": put["text"]},
        ensure_ascii=False, indent=1), mapa))
    print(f"fixtures geradas em {AQUI}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1
         else os.path.expanduser("~/.claude/specs/linkedin-apply-captura"))
