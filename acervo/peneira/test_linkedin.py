#!/usr/bin/env python3
"""LinkedIn offline: parsing, corpos SDUI e fluxo de aplicar sobre fixtures sanitizadas."""

import argparse
import base64
import contextlib
import io
import json
import os
import re
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import buscar
import linkedin

FIX = os.path.join(AQUI, "fixtures", "linkedin")


def ler(nome):
    with open(os.path.join(FIX, nome), encoding="utf-8") as f:
        return f.read()


def ler_json(nome):
    return json.loads(ler(nome))


def test_fixtures_sanitizadas():
    with open(os.path.join(AQUI, "respostas.json"), encoding="utf-8") as f:
        r = json.load(f)
    digitos = re.sub(r"\D", "", r["telefone"])
    proibidos = [r["email"], digitos[2:], r["nome"], *r["nome"].split(), r["cidade"].split(",")[0],
                 "JSESSIONID", "li_at"]
    padroes = [r"ajax:[1-9]", r"x-li-ambry-ep=(?!FAKE)", r"/AA(?!FAKE)[A-Za-z0-9_-]{20,}\.pdf",
               r'canonicalMemberId\\*"\s*:\s*\\*"(?!1000000001)', r"ACoAA(?!FAKE)",
               r"media\.licdn\.com/(?!FAKE)", r'[tT]racking(?:Id|Code)\\*"\s*:\s*\\*"(?!FAKE)',
               r'treeId\\*"\s*:\s*\\*"(?!FAKE)', r"trackingId=(?!FAKE)", r"&amp;mt=(?!FAKE)"]
    arquivos = [n for n in os.listdir(FIX) if not n.endswith(".py") and not n.startswith(".")]
    assert len(arquivos) == 12, sorted(arquivos)
    for nome in arquivos:
        texto = ler(nome)
        # A mensagem não repete o valor achado: o assert não pode vazar o dado.
        assert not any(p in texto for p in proibidos), f"{nome}: dado pessoal"
        for padrao in padroes:
            assert not re.search(padrao, texto), f"{nome}: {padrao}"


def test_rotulos_de_escolha():
    # Pergunta de escolha (chave com irmã _label): o SetState Yes/No é o valor a enviar.
    rsc, rotulos = ler("formulario_rotulos.rsc"), ler_json("rotulos.json")
    escolhas = [c for c in rotulos if c + "_label" in rsc]
    assert len(escolhas) >= 5, escolhas
    for chave in escolhas:
        for valor in ("Yes", "No"):
            setstate = re.escape(chave) + r'"\}\}\},"value":\{"\$case":"stringValue","stringValue":"' + valor
            assert re.search(setstate, rsc), f"{chave}: sem SetState {valor}"


def test_busca():
    vagas = linkedin.vagas_da_busca(ler("busca.html"))
    assert len(vagas) == 7, vagas
    assert vagas[0] == ("4481061055", "Desenvolvedor(a) Python | IA Generativa e Machine Learning")
    assert linkedin.vagas_da_busca("") == []
    url = linkedin.url_busca("ai engineer", "r86400", 7)
    assert url == ("https://www.linkedin.com/jobs/search/?keywords=ai+engineer&f_AL=true"
                   "&f_TPR=r86400&geoId=106057199&start=7"), url


def test_detalhe_da_vaga():
    d = linkedin.detalhe_da_vaga(ler("vaga.html"))
    assert (d["empresa"], d["tracking"], d["local"], d["modelo"]) == \
        ("Agento", "FAKE==", "Brasil", "remoto"), d
    assert d["texto"].startswith("Forward Deployed Engineer (FDE)"), d["texto"][:80]
    assert "window." not in d["texto"] and len(d["texto"]) < 20000
    # ATS externo não é Easy Apply: a vaga é pulada. O marcador prova que o recorte
    # não saiu vazio, senão o None abaixo passaria sem provar nada.
    assert "applicantTrackingSystemName" in ler("vaga_externa.html")
    assert linkedin.detalhe_da_vaga(ler("vaga_externa.html")) is None


def test_pedido_e_perguntas():
    rsc = ler("formulario.rsc")
    sr = linkedin.pedido(rsc, "submit")
    assert sr["requestId"] == linkedin.REQ + "submit"
    assert not {"maxRetries", "backOffMultiplier", "maxSeconds"} & set(sr)
    assert "$undefined" not in sr.values()
    assert linkedin.pedido(rsc, "naoExiste") is None
    qs = linkedin.perguntas(sr, rsc)
    assert [(q["tipo"], q["campo"], q["numerico"], q["escolha"]) for q in qs] == [
        ("EMAIL", "email", False, False), ("PHONE_MOBILE", "phoneCountryCode", False, False),
        ("PHONE_MOBILE", "phoneNumber", False, False), ("LARGER_RESUME", "selectedResume", False, False),
        ("UNKNOWN", "value_0_0", True, False), ("UNKNOWN", "value_0_1", True, False),
        ("UNKNOWN", "value_0_2", True, False)], qs
    assert qs[0]["chave"] == "ea.q::32383411364::EMAIL::email"


def test_rotulos():
    rsc = ler("formulario_rotulos.rsc")
    for chave, esperado in ler_json("rotulos.json").items():
        assert linkedin.rotulo(rsc, chave) == esperado, (chave, linkedin.rotulo(rsc, chave))
    # Sem rótulo achado, a própria chave identifica a pergunta na pendência.
    assert linkedin.rotulo("", "ea.q::1::UNKNOWN::x") == "ea.q::1::UNKNOWN::x"
    # A primeira ocorrência vence; prefixo vazio e a irmã _label não ancoram rótulo.
    sintetico = ('"prefix":"Primeira?" "prefix":"" "prefix":"Segunda?" ea.q::1::UNKNOWN::value_0_0_label '
                 'ea.q::1::UNKNOWN::value_0_0:validationState "prefix":"Terceira?" ea.q::1::UNKNOWN::value_0_0')
    assert linkedin.rotulo(sintetico, "ea.q::1::UNKNOWN::value_0_0") == "Primeira?"
    # Prefixo de campo fixo (Currículo) cai na própria chave e não pode rotular a pergunta seguinte.
    fixo = ('"prefix":"Currículo" ea.q::2::LARGER_RESUME::selectedResume ' + "x" * 5000 +
            ' "prefix":"Aceita PJ?" ea.q::2::UNKNOWN::value_0_0')
    assert linkedin.rotulo(fixo, "ea.q::2::UNKNOWN::value_0_0") == "Aceita PJ?"
    assert linkedin.rotulo(fixo, "ea.q::2::LARGER_RESUME::selectedResume") == \
        "ea.q::2::LARGER_RESUME::selectedResume"


def test_perguntas_escolha_e_numerica():
    rsc = ler("formulario_rotulos.rsc")
    qs = linkedin.perguntas(linkedin.pedido(rsc, "submit"), rsc)
    por_chave = {q["chave"]: q for q in qs}
    rotulos = ler_json("rotulos.json")
    assert set(rotulos) <= set(por_chave), sorted(por_chave)
    escolhas = {"ea.q::22381743033::UNKNOWN::value_0_0", "ea.q::22381743025::UNKNOWN::value_0_2",
                "ea.q::22381743009::UNKNOWN::value_0_4", "ea.q::22381743017::UNKNOWN::value_0_5",
                "ea.q::22381742569::UNKNOWN::value_0_0"}
    numericas = {"ea.q::22381742561::UNKNOWN::value_0_1", "ea.q::22381742609::UNKNOWN::value_0_3"}
    assert escolhas | numericas == set(rotulos)
    for c in escolhas:
        assert (por_chave[c]["escolha"], por_chave[c]["numerico"]) == (True, False), c
    for c in numericas:
        assert (por_chave[c]["escolha"], por_chave[c]["numerico"]) == (False, True), c
    assert all(por_chave[c]["rotulo"] == rotulos[c] for c in rotulos)


def test_resolver():
    def q(tipo, campo, rotulo="", numerico=False, escolha=False):
        return {"chave": f"ea.q::9::{tipo}::{campo}", "id": "9", "tipo": tipo, "campo": campo,
                "numerico": numerico, "escolha": escolha, "rotulo": rotulo}
    r = {"email": "candidato@example.com", "telefone": "(83) 90000-0000",
         "formulario_linkedin": {"Quantos anos de experiência com Python?": "3",
                                 "Anos com React": "2 anos", "Aceita PJ?": "Sim",
                                 "Trabalha híbrido?": "não", "Pode mudar?": "Yes",
                                 "Tem CNH?": "talvez", "Pretensão salarial?": "8000",
                                 "Anos com Rust": "³"}}
    qs = [q("EMAIL", "email"), q("PHONE_MOBILE", "phoneCountryCode"),
          q("PHONE_MOBILE", "phoneNumber"), q("LARGER_RESUME", "selectedResume"),
          q("RESUME", "selectedResume"),
          q("UNKNOWN", "a", "quantos anos de experiencia com python", True),
          q("UNKNOWN", "b", "Anos com React", True), q("UNKNOWN", "c", "Anos com Go", True),
          q("UNKNOWN", "l", "Anos com Rust", True),
          q("UNKNOWN", "f", "Aceita PJ?", escolha=True),
          q("UNKNOWN", "g", "Trabalha híbrido?", escolha=True),
          q("UNKNOWN", "h", "Pode mudar?", escolha=True),
          q("UNKNOWN", "i", "Tem CNH?", escolha=True),
          q("UNKNOWN", "j", "Fala inglês?", escolha=True),
          q("UNKNOWN", "k", "Pretensão salarial?"),
          q("RADIO", "d", "Aceita CLT?"), q("COVER_LETTER", "e", "Carta")]
    valores, pend = linkedin.resolver(qs, r, "/AAFAKE0.pdf")
    assert valores == {"ea.q::9::EMAIL::email": "candidato@example.com",
                       "ea.q::9::PHONE_MOBILE::phoneCountryCode": "br",
                       "ea.q::9::PHONE_MOBILE::phoneNumber": "83900000000",
                       "ea.q::9::LARGER_RESUME::selectedResume": "/AAFAKE0.pdf",
                       "ea.q::9::RESUME::selectedResume": "/AAFAKE0.pdf",
                       "ea.q::9::UNKNOWN::a": "3", "ea.q::9::UNKNOWN::f": "Yes",
                       "ea.q::9::UNKNOWN::g": "No", "ea.q::9::UNKNOWN::h": "Yes"}, valores
    assert pend == ["resposta não numérica para 'Anos com React': 2 anos",
                    "sem resposta: Anos com Go",
                    "resposta não numérica para 'Anos com Rust': ³",
                    "resposta não Sim/Não para 'Tem CNH?': talvez",
                    "sem resposta: Fala inglês?",
                    "tipo UNKNOWN não mapeado: Pretensão salarial?",
                    "tipo RADIO não mapeado: Aceita CLT?",
                    "tipo COVER_LETTER não mapeado: Carta"], pend
    assert linkedin.normalizar("  Não, às vezes! ") == "nao as vezes"


SELECT = "ea.q::37770075890::UNKNOWN::value_0_0"
INGLES = ["None", "Conversational", "Professional", "Native or bilingual"]
PYTHON, AWS, PRESENCIAL, PRETENSAO = (f"ea.q::{qid}::UNKNOWN::value_0_{i}" for i, qid in enumerate(
    ("37765680914", "37765680906", "37765680898", "37765680890")))


def test_opcoes_do_select():
    rsc = ler("formulario_select.rsc")
    # "Selecionar opção" (disabled) é o placeholder: não é resposta.
    assert linkedin.opcoes(rsc, SELECT) == INGLES
    assert linkedin.opcoes(rsc, "ea.q::1::UNKNOWN::x") == []
    # Lista inline (sem linhas $L): o placeholder disabled também sai.
    assert linkedin.opcoes(rsc, "ea.q::37770075882::EMAIL::email") == ["candidato@example.com"]
    # Vale o `value`, não o `label`; a linha $L pode vir antes ou depois da lista.
    linhas = ('9:["$","$L45","A",{"label":"Sim, claro","value":"Yes"}]\n'
              'x{"options":["$L9","$La"],"valueStateKey":{"key":{"value":{"$case":"id","id":"K"}}}}\n'
              'a:["$","$L45","B",{"label":"Não","value":"No"}]')
    assert linkedin.opcoes(linhas, "K") == ["Yes", "No"]
    # "options" que não termina no valueStateKey da chave é de outro campo.
    outro = ('9:["$","$L45","A",{"label":"A","value":"Yes"}]\n"options":["$L9"],"x":1,'
             '"valueStateKey":{"key":{"value":{"$case":"id","id":"K"}}}')
    assert linkedin.opcoes(outro, "K") == []


def test_perguntas_com_opcoes_e_decimal():
    rsc = ler("formulario_select.rsc")
    qs = {q["chave"]: q for q in linkedin.perguntas(linkedin.pedido(rsc, "submit"), rsc)}
    assert qs[SELECT]["escolha"] and qs[SELECT]["opcoes"] == INGLES
    assert all(q["opcoes"] == [] for c, q in qs.items() if c != SELECT), qs
    rsc = ler("formulario_decimal.rsc")
    qs = {q["chave"]: q for q in linkedin.perguntas(linkedin.pedido(rsc, "submit"), rsc)}
    assert [(qs[c]["numerico"], qs[c]["decimal"], qs[c]["escolha"])
            for c in (PYTHON, AWS, PRETENSAO, PRESENCIAL)] == [
        (True, False, False), (True, False, False), (True, True, False), (False, False, True)], qs
    # O radio não tem lista: a escolha cai no Sim/Não de sempre.
    assert qs[PRESENCIAL]["opcoes"] == []


def test_rotulo_longe_do_prefixo():
    # O campo da AWS é uma linha $L definida 450 mil caracteres adiante: o prefixo
    # acha o campo pelo componentKey easyApplyFieldFocus, não pela próxima chave ea.q::.
    rsc = ler("formulario_decimal.rsc")
    assert linkedin.rotulo(rsc, AWS) == "Há quantos anos você já usa Amazon Web Services no trabalho?"
    assert linkedin.rotulo(rsc, PYTHON) == "Há quantos anos você já usa Python no trabalho?"
    assert linkedin.rotulo(rsc, PRETENSAO) == "Qual a sua pretensão salarial PJ?"


def _q(campo, rotulo, numerico=False, escolha=False, decimal=False, opcoes=()):
    return {"chave": f"ea.q::9::UNKNOWN::{campo}", "id": "9", "tipo": "UNKNOWN", "campo": campo,
            "numerico": numerico, "decimal": decimal, "escolha": escolha, "rotulo": rotulo,
            "opcoes": list(opcoes)}


def test_resolver_numero_decimal():
    r = {"formulario_linkedin": {"Meta decimal?": "123.45", "Meta inteira?": "123.45",
                                 "Inteiro no decimal?": "123", "Milhar?": "12.000", "Real?": "R$ 12.000,00",
                                 "Vírgula?": "1,5", "Ponto solto?": "12.", "Sem inteiro?": ".5"}}
    qs = [_q("a", "Meta decimal?", True, decimal=True), _q("b", "Meta inteira?", True),
          _q("c", "Inteiro no decimal?", True, decimal=True), _q("d", "Milhar?", True),
          _q("e", "Real?", True, decimal=True), _q("f", "Vírgula?", True, decimal=True),
          _q("g", "Ponto solto?", True, decimal=True), _q("h", "Sem inteiro?", True, decimal=True)]
    valores, pend = linkedin.resolver(qs, r, "/AAFAKE0.pdf")
    assert valores == {"ea.q::9::UNKNOWN::a": "123.45", "ea.q::9::UNKNOWN::c": "123"}, valores
    assert pend == ["resposta não numérica para 'Meta inteira?': 123.45",
                    "resposta não numérica para 'Milhar?': 12.000",
                    "resposta não numérica para 'Real?': R$ 12.000,00",
                    "resposta não numérica para 'Vírgula?': 1,5",
                    "resposta não numérica para 'Ponto solto?': 12.",
                    "resposta não numérica para 'Sem inteiro?': .5"], pend


def test_resolver_escolha_com_opcoes():
    r = {"formulario_linkedin": {"Inglês?": "conversational", "Sim ou não?": "sim",
                                 "Remoto?": "Não", "Fala yes?": "yes", "Fluência?": "fluente",
                                 "Aceita?": "sim", "Porte?": "no"}}
    sim_nao, pt = ["Yes", "No"], ["Sim", "Não"]
    qs = [_q("a", "Inglês?", escolha=True, opcoes=INGLES),
          _q("b", "Sim ou não?", escolha=True, opcoes=sim_nao), _q("c", "Remoto?", escolha=True, opcoes=pt),
          _q("d", "Fala yes?", escolha=True, opcoes=pt), _q("e", "Fluência?", escolha=True, opcoes=INGLES),
          _q("f", "Aceita?", escolha=True, opcoes=INGLES), _q("g", "Porte?", escolha=True, opcoes=sim_nao),
          _q("h", "Nível de Java?", escolha=True, opcoes=INGLES), _q("i", "Aceita PJ?", escolha=True)]
    valores, pend = linkedin.resolver(qs, r, "/AAFAKE0.pdf")
    assert valores == {"ea.q::9::UNKNOWN::a": "Conversational", "ea.q::9::UNKNOWN::b": "Yes",
                       "ea.q::9::UNKNOWN::c": "Não", "ea.q::9::UNKNOWN::d": "Sim",
                       "ea.q::9::UNKNOWN::g": "No"}, valores
    todas = "None, Conversational, Professional, Native or bilingual"
    assert pend == [f"resposta fora das opções para 'Fluência?': fluente (opções: {todas})",
                    f"resposta fora das opções para 'Aceita?': sim (opções: {todas})",
                    f"sem resposta: Nível de Java? (opções: {todas})",
                    "sem resposta: Aceita PJ?"], pend


def test_resolver_pretensao_vem_do_calculo():
    pretensao = {"clt": 7650.4, "pj": 10710.6}
    r = {"formulario_linkedin": {"Pretensão guardada?": "9000"}, "pretensao": pretensao}
    qs = [_q("a", "Qual a sua pretensão salarial?", True), _q("b", "Qual a pretensão salarial PJ?", True, decimal=True),
          _q("c", "Expected salary (PJ)?", True), _q("d", "Salário desejado?", True, decimal=True),
          _q("e", "Pretensão guardada?", True), _q("f", "Salary expectation?", True),
          _q("g", "Quantos anos de Python?", True), _q("h", "Salário combinado?", escolha=True),
          _q("i", "Pretensão da pjotr?", True), _q("j", "Qual seu salário atual?", True),
          _q("k", "Current salary?", True), _q("l", "Pretensão salarial por hora (PJ)?", True),
          _q("m", "Anos com Salesforce?", True)]
    valores, pend = linkedin.resolver(qs, r, "/AAFAKE0.pdf")
    assert valores == {"ea.q::9::UNKNOWN::a": "7650", "ea.q::9::UNKNOWN::b": "10711",
                       "ea.q::9::UNKNOWN::c": "10711", "ea.q::9::UNKNOWN::d": "7650",
                       "ea.q::9::UNKNOWN::e": "9000", "ea.q::9::UNKNOWN::f": "7650",
                       "ea.q::9::UNKNOWN::i": "7650"}, valores
    assert pend == ["sem resposta: Quantos anos de Python?", "sem resposta: Salário combinado?",
                    "sem resposta: Qual seu salário atual?", "sem resposta: Current salary?",
                    "sem resposta: Pretensão salarial por hora (PJ)?", "sem resposta: Anos com Salesforce?"], pend
    # Sem `pretensao` em r o comportamento é o de antes: a pergunta fica sem resposta.
    valores, pend = linkedin.resolver(qs[:1], {"formulario_linkedin": {}}, "/AAFAKE0.pdf")
    assert valores == {} and pend == ["sem resposta: Qual a sua pretensão salarial?"], (valores, pend)


def bate(a, b):
    # `==` ignora a ordem das chaves e iguala True a 1; o que vai no fio é o texto do json.dumps.
    return json.dumps(a) == json.dumps(b)


def test_corpo_submit_igual_ao_capturado():
    cap = ler_json("submit.json")["corpo"]
    valores = {s["key"]: s["value"] for s in cap["states"] if s["key"].startswith("ea.q::")}
    # Na captura o usuário deixou "seguir empresa" marcado; o corpo precisa bater byte a byte.
    assert bate(linkedin.corpo_submit(cap["serverRequest"], valores, True, False, ""), cap)
    p = cap["serverRequest"]["requestedArguments"]["payload"]
    corpo = linkedin.corpo_submit(cap["serverRequest"], valores, False, True, "m" * 20)
    assert linkedin.valor_estado(corpo, p["followCompany"]["key"]) is False
    assert linkedin.valor_estado(corpo, p["topChoiceInfo"]["isTopChoiceMarked"]["value"]["key"]) is True
    # O submit montado a partir do RSC tem os mesmos campos de topo que o capturado.
    sr = linkedin.pedido(ler("formulario.rsc"), "submit")
    assert sorted(sr) == sorted(cap["serverRequest"]), sorted(sr)


def test_submit_sem_seguir_empresa_nao_envia():
    cap = ler_json("submit.json")["corpo"]
    valores = {s["key"]: s["value"] for s in cap["states"] if s["key"].startswith("ea.q::")}
    sr = json.loads(json.dumps(cap["serverRequest"]))
    seguir = sr["requestedArguments"]["payload"]["followCompany"]["key"]
    pedidas = sr["requestedArguments"]["requestedStateKeys"]
    sr["requestedArguments"]["requestedStateKeys"] = [k for k in pedidas if k["key"]["value"]["id"] != seguir]
    try:
        linkedin.corpo_submit(sr, valores, False, False, "")
    except RuntimeError:
        pass
    else:
        raise AssertionError("corpo sem o estado de seguir empresa foi montado")


def test_submit_com_escolha_sem_label():
    # O cliente só manda as chaves de requestedStateKeys: a `_label` (Sim/Não) é só da tela.
    rsc = ler("formulario_rotulos.rsc")
    sr = linkedin.pedido(rsc, "submit")
    qs = linkedin.perguntas(sr, rsc)
    valores = {q["chave"]: "Yes" if q["escolha"] else "1" for q in qs}
    corpo = linkedin.corpo_submit(sr, valores, False, False, "")
    chaves = [s["key"] for s in corpo["states"]]
    assert not any(c.endswith("_label") for c in chaves), chaves
    escolhas = [q["chave"] for q in qs if q["escolha"]]
    assert len(escolhas) == 5
    assert all(linkedin.valor_estado(corpo, c) == "Yes" for c in escolhas)


def test_corpos_do_upload():
    up = ler_json("upload.json")
    cap = up["escolher"]["corpo"]
    midia = cap["states"][0]["value"]["mediaFiles"][0]
    estados = [linkedin.estado("resume-picked-media",
                               linkedin.midia_pdf(midia["fileName"], int(midia["size"]), midia["filePointer"])),
               linkedin.estado("easyApply.resumeSelectedKeyId", cap["states"][1]["value"])]
    job = cap["serverRequest"]["requestedArguments"]["payload"]["jobId"]
    assert bate(linkedin.corpo_servidor(linkedin.sr_escolher_arquivo(job), estados), cap)
    vincular = up["vincular"]["corpo"]
    sr = linkedin.pedido(up["url"]["resposta"], "setResumeFormBinding")
    assert bate(linkedin.corpo_servidor(sr, vincular["states"]), vincular)
    url = linkedin.url_ambry(up["url"]["resposta"])
    assert url.startswith("https://www.linkedin.com/ambry/?x-li-ambry-ep=FAKE") and url.endswith(".pdf"), url
    # O id do currículo vem no header `location` do POST; no corpo ou em outro header não vale.
    assert linkedin.id_do_ambry(ler_json("ambry_put.json")).startswith("/AAFAKE")
    outro = {"text": "/AAFAKE9.pdf", "headers": {"raw": "x-other: /AAFAKE8.pdf\r\n"}}
    try:
        linkedin.id_do_ambry(outro)
    except RuntimeError:
        pass
    else:
        raise AssertionError("id fora do header location foi aceito")


def test_corpo_navegacao():
    nav = ler_json("navegacao.json")
    assert bate(linkedin.corpo_navegacao(nav["job_id"], nav["empresa"], "FAKE=="), nav["corpo"])
    assert linkedin.BASE + nav["url"] == linkedin.URL_NAVEGACAO, nav["url"]


def test_enviado():
    resposta = ler_json("submit.json")["resposta"]
    assert linkedin.enviado(resposta, "4482617482")
    assert not linkedin.enviado(resposta, "1")
    assert not linkedin.enviado(resposta.replace('"errors":[]', '"errors":["x"]'), "4482617482")


class FakeLinkedIn:
    """Responde como o LinkedIn a partir das fixtures e anota cada chamada."""

    def __init__(self, me=200, submit=None, cair_no_submit=None, ruins=(), externas=()):
        self.chamadas, self.me = [], me
        self.extras = []
        self.submit = submit if submit is not None else ler_json("submit.json")["resposta"]
        self.cair_no_submit = cair_no_submit
        # `ruins`: trechos de URL que respondem 429; `externas`: ids de vaga com ATS externo.
        self.ruins, self.externas = ruins, externas

    def __call__(self, metodo, url, corpo=None, cabecalhos=None, b64=None):
        self.chamadas.append((metodo, url, corpo))
        self.extras.append((cabecalhos, b64))

        def ok(texto, status=200):
            return {"sessao": True, "status": status, "url": url, "headers": {}, "text": texto}
        if any(trecho in url for trecho in self.ruins):
            return ok("", 429)
        if "/voyager/api/me" in url:
            return ok("{}", self.me)
        if "/jobs/search/" in url:
            return ok(ler("busca.html") if "start=0" in url else "")
        if "/jobs/view/" in url:
            externa = any(f"/jobs/view/{i}/" in url for i in self.externas)
            return ok(ler("vaga_externa.html" if externa else "vaga.html"))
        if "actions/navigation" in url:
            return ok(ler("formulario.rsc"))
        if "/ambry/" in url:
            return dict(ler_json("ambry_put.json"), sessao=True, url=url)
        etapas = {"handlePickedFile": "escolher", "getAmbryUploadUrl": "url",
                  "setResumeFormBinding": "vincular"}
        for nome, chave in etapas.items():
            if nome in url:
                return ok(ler_json("upload.json")[chave]["resposta"])
        if "easyapply.submit" in url:
            envios = len(self.enviados("easyapply.submit"))
            if self.cair_no_submit and envios >= self.cair_no_submit:
                raise linkedin.SessaoExpirada(linkedin.SESSAO)
            return ok(self.submit)
        raise AssertionError(f"chamada inesperada: {metodo} {url}")

    def enviados(self, trecho):
        return [json.loads(c) if c else None for _, u, c in self.chamadas if trecho in u]


SESSAO = ("sessão do LinkedIn expirada: abra `playwright-cli -s=linkedin open https://www.linkedin.com/feed/"
          " --headed --persistent` e faça login")


def navegador_falso(resposta, expressoes=None):
    """Imita o `playwright-cli --json eval`: o resultado vem serializado duas vezes."""
    def navegador(*args):
        assert args[0] == "eval" and len(args) == 2, args
        if expressoes is not None:
            expressoes.append(args[1])
        return json.dumps(json.dumps(resposta, ensure_ascii=False))
    return navegador


def test_chamar_e_sessao():
    antigo, linkedin.PAUSA = (linkedin.navegador, linkedin.PAUSA), (0, 0)
    try:
        expressoes = []
        texto = "ação \u009a 😀  " + "x" * 5_000_000
        linkedin.navegador = navegador_falso({"sessao": True, "status": 200, "url": "u", "headers": {}, "text": texto},
                                             expressoes=expressoes)
        assert linkedin.chamar("GET", "https://www.linkedin.com/x")["text"] == texto
        assert '"method": "GET"' in expressoes[0] and "document.cookie" in expressoes[0]
        assert "403" in expressoes[0]
        linkedin.navegador = navegador_falso({"sessao": True, "status": 201, "url": "u", "headers": {}, "text": ""})
        assert linkedin.chamar("POST", "https://www.linkedin.com/ambry/x", b64="A" * 200_000)["status"] == 201
        linkedin.navegador = navegador_falso({"sessao": False})
        try:
            linkedin.chamar("GET", "https://www.linkedin.com/x")
        except linkedin.SessaoExpirada as e:
            assert str(e) == SESSAO
        else:
            raise AssertionError("sessão não detectada")
    finally:
        linkedin.navegador, linkedin.PAUSA = antigo


def test_navegador_falhas():
    antigo = linkedin.subprocess.run
    fechado = '{"isError": true, "error": "The browser \'linkedin\' is not open, please run open first"}'
    casos = [(linkedin.subprocess.TimeoutExpired("playwright-cli", 180), RuntimeError),
             (FileNotFoundError("playwright-cli"), RuntimeError),
             (linkedin.subprocess.CompletedProcess([], 1, "", "Error: runtime fora"), RuntimeError),
             (linkedin.subprocess.CompletedProcess([], 1, '{"isError": true, "error": "Error: boom"}', ""), RuntimeError),
             (linkedin.subprocess.CompletedProcess([], 1, fechado, ""), linkedin.SessaoExpirada)]
    try:
        for caso, esperado in casos:
            def falso(cmd, *a, caso=caso, **k):
                assert cmd[:3] == ["playwright-cli", "-s=linkedin", "--json"], cmd
                assert k["encoding"] == "utf-8" and k["timeout"] == 180
                if isinstance(caso, Exception):
                    raise caso
                return caso
            linkedin.subprocess.run = falso
            try:
                linkedin.navegador("eval", "1")
            except esperado as e:
                assert esperado is not linkedin.SessaoExpirada or str(e) == SESSAO
            else:
                raise AssertionError(f"{caso!r} não virou {esperado.__name__}")
    finally:
        linkedin.subprocess.run = antigo


def test_so_200_vale():
    antigo, linkedin.chamar = linkedin.chamar, lambda *a, **k: {"sessao": True, "status": 429, "text": "x"}
    try:
        for funcao, args in ((linkedin.buscar_pagina, ("python", "r604800", 0)),
                             (linkedin.pagina_da_vaga, ("1",)), (linkedin.post_servidor, ("n", {})),
                             (linkedin.abrir_formulario, ("1", "e", "t"))):
            try:
                funcao(*args)
            except RuntimeError as e:
                assert "429" in str(e)
            else:
                raise AssertionError(f"{funcao.__name__} aceitou 429")
    finally:
        linkedin.chamar = antigo


def test_id_do_ambry_dos_dois_formatos():
    # A ponte devolve headers como dict (Object.fromEntries); a fixture guarda a forma bruta.
    assert linkedin.id_do_ambry({"headers": {"location": "/AAFAKE7.pdf"}}) == "/AAFAKE7.pdf"
    assert linkedin.id_do_ambry({"headers": {"raw": "location: /AAFAKE7.pdf\r\n"}}) == "/AAFAKE7.pdf"


def test_enviar_cv():
    antigo = linkedin.chamar
    try:
        falso = linkedin.chamar = FakeLinkedIn()
        up = ler_json("upload.json")
        chave_cv = up["escolher"]["corpo"]["states"][1]["value"]
        with tempfile.TemporaryDirectory() as tmp:
            caminho = os.path.join(tmp, "cv.pdf")
            with open(caminho, "wb") as f:
                f.write(b"0" * 101237)
            asset = linkedin.enviar_cv("4482617482", chave_cv, caminho, ponteiro="kxk3e2cwei")
        assert asset == linkedin.id_do_ambry(ler_json("ambry_put.json"))
        assert falso.enviados("handlePickedFile") == [up["escolher"]["corpo"]]
        antigo_id = up["vincular"]["corpo"]["states"][0]["value"][0]
        esperado = json.loads(json.dumps(up["vincular"]["corpo"]).replace(antigo_id, asset))
        assert falso.enviados("setResumeFormBinding") == [esperado]
        assert [m for m, u, _ in falso.chamadas if "/ambry/" in u] == ["POST"]
        (cabecalhos, b64), = [e for (_, u, _), e in zip(falso.chamadas, falso.extras) if "/ambry/" in u]
        assert cabecalhos == {"Content-Type": "application/pdf"}
        assert base64.b64decode(b64) == b"0" * 101237
    finally:
        linkedin.chamar = antigo


P_TESTE = {"cargos": ["python", "ai engineer", "engineer"], "excluir": [],
           "modelos": ["remoto", "hibrido", "presencial"], "cidades": [], "dias_max": 45,
           "stack_excluir": [], "stack": ["python"], "niveis_aceitos": ["junior", "pleno"],
           "paginas_linkedin": 1}


def _rotulos_do_formulario():
    rsc = ler("formulario.rsc")
    return [q["rotulo"] for q in linkedin.perguntas(linkedin.pedido(rsc, "submit"), rsc)
            if q["tipo"] == "UNKNOWN"]


R_TESTE = {"email": "candidato@example.com", "telefone": "(83) 90000-0000",
           "formulario_linkedin": {r: "2" for r in _rotulos_do_formulario()},
           "desconto_pretensao": 0.15, "multiplicador_pj": 1.4,
           "faixas_clt_mensal": {"junior": 5000, "pleno": 9000, "senior": 15000}}


@contextlib.contextmanager
def ambiente():
    """Banco, dossiês, respostas e LinkedIn falsos; restaura tudo na saída."""
    antigo = (buscar.BANCO, buscar.DOSSIES, buscar.RESPOSTAS, buscar.perfil, linkedin.chamar,
              linkedin.PAUSA, buscar.PAUSA_BUSCA)
    with tempfile.TemporaryDirectory() as tmp:
        buscar.BANCO = os.path.join(tmp, "vagas.db")
        buscar.DOSSIES = os.path.join(tmp, "dossies")
        buscar.RESPOSTAS = os.path.join(tmp, "respostas.json")
        with open(buscar.RESPOSTAS, "w", encoding="utf-8") as f:
            json.dump(R_TESTE, f)
        buscar.perfil = lambda: P_TESTE
        linkedin.PAUSA, buscar.PAUSA_BUSCA = (0, 0), 0
        try:
            yield tmp
        finally:
            (buscar.BANCO, buscar.DOSSIES, buscar.RESPOSTAS, buscar.perfil, linkedin.chamar,
             linkedin.PAUSA, buscar.PAUSA_BUSCA) = antigo


def semear(con, *ids):
    buscar.guardar(con, [{"chave": f"linkedin:{i}", "fonte": "linkedin", "origem": "Agento",
                          "titulo": f"Forward Deployed Engineer {n}",
                          "url": f"https://www.linkedin.com/jobs/view/{i}/",
                          "publicada": buscar.hoje(), "modelo": "remoto", "contrato": "",
                          "nivel": "", "local": "Brasil", "texto": "python"}
                         for n, i in enumerate(ids)], P_TESTE)


def curriculo(tmp, chave, ats, mensagem=""):
    pdf = os.path.join(tmp, f"{chave.replace(':', '_')}.pdf")
    with open(pdf, "wb") as f:
        f.write(b"%PDF-1.4 teste")
    with contextlib.redirect_stdout(io.StringIO()):
        return buscar.cmd_curriculo(argparse.Namespace(chave=chave, pdf=pdf, ats=ats, mensagem=mensagem))


def aplicar(quantas, seco):
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        codigo = buscar.cmd_aplicar(argparse.Namespace(quantas=quantas, seco=seco))
    return codigo, saida.getvalue()


def enviar(quantas):
    """O fluxo do SKILL.md: o --seco mostra o lote e o envio real só vale para o que ele mostrou."""
    aplicar(quantas, seco=True)
    return aplicar(quantas, seco=False)


def aprovacao():
    return os.path.join(os.path.dirname(buscar.BANCO), "lote_aprovado.json")


def test_cacar_linkedin():
    with ambiente():
        falso = linkedin.chamar = FakeLinkedIn()
        con = buscar.abrir()
        vagas = buscar.do_linkedin(dict(P_TESTE, cargos=["python", "ai engineer"]), con)
        assert sorted(v["chave"] for v in vagas) == \
            ["linkedin:4480695140", "linkedin:4481061055", "linkedin:4483177134"], vagas
        assert {v["fonte"] for v in vagas} == {"linkedin"} and vagas[0]["origem"] == "Agento"
        # Vaga já no ledger não custa outra visita à página.
        novas, _, _ = buscar.guardar(con, vagas, P_TESTE)
        visitas = len([u for _, u, _ in falso.chamadas if "/jobs/view/" in u])
        assert buscar.do_linkedin(dict(P_TESTE, cargos=["python", "ai engineer"]), con) == []
        assert len([u for _, u, _ in falso.chamadas if "/jobs/view/" in u]) == visitas
        # Sem novidade em 24 h, a busca repete na janela de 7 dias, nunca antes dela.
        janelas = [re.search(r"f_TPR=(r\d+)", u).group(1)
                   for _, u, _ in falso.chamadas if "/jobs/search/" in u]
        assert janelas == ["r86400"] * 4 + ["r604800"] * 2, janelas


def test_vaga_externa_nao_entra_nem_volta_na_janela_de_7_dias():
    with ambiente():
        p = dict(P_TESTE, cargos=["python"])
        falso = linkedin.chamar = FakeLinkedIn(externas=("4481061055",))
        assert buscar.do_linkedin(p, buscar.abrir()) == []
        # 24 h só trouxe a externa; a janela de 7 dias a vê de novo na busca, mas não a reabre.
        assert [u for _, u, _ in falso.chamadas if "/jobs/search/" in u and "r604800" in u]
        assert len([u for _, u, _ in falso.chamadas if "/jobs/view/4481061055/" in u]) == 1
        # Com outras vagas Easy Apply na busca, só a externa fica de fora.
        linkedin.chamar = FakeLinkedIn(externas=("4481061055",))
        vagas = buscar.do_linkedin(dict(p, cargos=["python", "ai engineer"]), buscar.abrir())
        assert sorted(v["chave"] for v in vagas) == ["linkedin:4480695140", "linkedin:4483177134"], vagas


def test_fallback_de_7_dias_vale_pelas_vagas_que_o_perfil_aceita():
    with ambiente():
        # A única vaga das 24 h é remota e o perfil só aceita presencial: não conta como novidade.
        p = dict(P_TESTE, cargos=["python"], modelos=["presencial"])
        falso = linkedin.chamar = FakeLinkedIn()
        vagas = buscar.do_linkedin(p, buscar.abrir())
        assert any("r604800" in u for _, u, _ in falso.chamadas if "/jobs/search/" in u)
        # A recusada volta para o guardar contar em "recusadas pelo perfil".
        assert [v["chave"] for v in vagas] == ["linkedin:4481061055"]
        assert buscar.guardar(buscar.abrir(), vagas, p) == ([], 0, 1)


def test_status_ruim_numa_busca_e_numa_vaga_nao_derruba_o_cacar():
    with ambiente():
        buscar.perfil = lambda: dict(P_TESTE, cargos=["python", "ai engineer"])
        linkedin.chamar = FakeLinkedIn(ruins=("keywords=ai+engineer", "/jobs/view/4481061055/"))
        erro = io.StringIO()
        with contextlib.redirect_stderr(erro), contextlib.redirect_stdout(io.StringIO()):
            codigo = buscar.main(["cacar", "--fonte", "linkedin"])
        avisos = erro.getvalue().strip().splitlines()
        assert codigo == 0 and len(avisos) == 2 and all("429" in a for a in avisos), (codigo, avisos)
        chaves = [l["chave"] for l in buscar.abrir().execute("SELECT chave FROM vagas")]
        assert sorted(chaves) == ["linkedin:4480695140", "linkedin:4483177134"], chaves


def test_pausa_entre_buscas():
    with ambiente():
        linkedin.chamar = FakeLinkedIn()
        pausas, antigo = [], buscar.time.sleep
        buscar.PAUSA_BUSCA, buscar.time.sleep = 1.5, pausas.append
        try:
            buscar.do_linkedin(dict(P_TESTE, cargos=["python", "ai engineer"]), buscar.abrir())
        finally:
            buscar.time.sleep = antigo
        assert pausas == [1.5, 1.5], pausas


def test_cacar_sessao_expirada_sai_com_2():
    with ambiente():
        linkedin.chamar = FakeLinkedIn(me=401)
        erro = io.StringIO()
        with contextlib.redirect_stderr(erro):
            codigo = buscar.main(["cacar", "--fonte", "linkedin"])
        assert codigo == 2 and erro.getvalue().strip() == linkedin.SESSAO, (codigo, erro.getvalue())


def test_melhores_filtra_por_fonte():
    with ambiente():
        con = buscar.abrir()
        for fonte in ("linkedin", "gupy"):
            con.execute("INSERT INTO vagas (chave,fonte,titulo,publicada,vista_em) VALUES (?,?,?,?,?)",
                        (f"{fonte}:1", fonte, f"Python {fonte}", "2026-10-24", "2026-10-24"))
        assert [v["fonte"] for v in buscar.melhores(con, P_TESTE, 10, fonte="linkedin")] == ["linkedin"]
        assert len(buscar.melhores(con, P_TESTE, 10)) == 2


def test_aplicar_seco_nao_envia():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482")
        assert curriculo(tmp, "linkedin:4482617482", 88) == 0
        codigo, saida = aplicar(1, seco=True)
        assert codigo == 0 and "vaga" in saida and "pendências" in saida and "pronta" in saida, saida
        assert falso.enviados("easyapply.submit") == [] and falso.enviados("/ambry/") == []


def test_seco_mostra_pendencia_e_responder_resolve():
    with ambiente():
        linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482")
        with open(buscar.RESPOSTAS, "w", encoding="utf-8") as f:
            json.dump(dict(R_TESTE, formulario_linkedin={}), f)
        _, saida = aplicar(1, seco=True)
        assert "sem resposta:" in saida and "pendência\n" in saida, saida
        for rotulo in _rotulos_do_formulario():
            with contextlib.redirect_stdout(io.StringIO()):
                buscar.cmd_responder(argparse.Namespace(pergunta=rotulo, valor="3"))
        _, saida = aplicar(1, seco=True)
        assert "sem resposta:" not in saida and "sem currículo" in saida, saida


def test_responder_nao_apaga_o_resto_do_arquivo():
    with ambiente():
        # `linkedin` guarda a URL do perfil: gravar respostas nela apagaria o dado.
        with open(buscar.RESPOSTAS, "w", encoding="utf-8") as f:
            json.dump(dict(R_TESTE, linkedin="https://example.com/in/x"), f)
        with contextlib.redirect_stdout(io.StringIO()):
            buscar.cmd_responder(argparse.Namespace(pergunta="Anos com Go?", valor="1"))
        with open(buscar.RESPOSTAS, encoding="utf-8") as f:
            r = json.load(f)
        assert r["linkedin"] == "https://example.com/in/x" and r["email"] == R_TESTE["email"]
        assert r["formulario_linkedin"]["Anos com Go?"] == "1"


def test_cv_sumido_vira_sem_curriculo():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482")
        curriculo(tmp, "linkedin:4482617482", 88)
        aplicar(1, seco=True)
        os.remove(os.path.join(tmp, "linkedin_4482617482.pdf"))
        _, saida = aplicar(1, seco=False)
        assert "sem currículo" in saida and falso.enviados("handlePickedFile") == [], saida


def test_curriculo_valida_entrada():
    with ambiente() as tmp:
        semear(buscar.abrir(), "4482617482")
        erro = io.StringIO()
        with contextlib.redirect_stderr(erro):
            assert curriculo(tmp, "linkedin:4482617482", 92, mensagem="curta") == 1
            assert buscar.cmd_curriculo(argparse.Namespace(
                chave="linkedin:4482617482", pdf="/nao/existe.pdf", ats=90, mensagem="")) == 1
        assert "20 a 400" in erro.getvalue() and "PDF não encontrado" in erro.getvalue()


def pagina(texto):
    return {"sessao": True, "status": 200, "url": "", "headers": {}, "text": texto}


def com_desvio(falso, trecho, resposta):
    """linkedin.chamar que, para URLs com `trecho`, usa resposta(corpo) (None = segue o falso)."""
    def chamar(metodo, url, corpo=None, cabecalhos=None, b64=None):
        achado = resposta(corpo) if trecho in url else None
        return achado if achado is not None else falso(metodo, url, corpo, cabecalhos, b64)
    return chamar


def estados(con):
    return sorted(r["estado"] for r in con.execute("SELECT estado FROM vagas"))


def test_vaga_externa_vira_cortada():
    with ambiente():
        linkedin.chamar = com_desvio(FakeLinkedIn(), "/jobs/view/", lambda c: pagina(ler("vaga_externa.html")))
        con = buscar.abrir()
        semear(con, "4482617482")
        _, saida = aplicar(1, seco=True)
        assert "cortada: não é Easy Apply" in saida and estados(con) == ["cortada"], saida


def test_tipo_nao_mapeado_vira_cortada():
    with ambiente():
        rsc = ler("formulario.rsc").replace("::EMAIL::", "::COVER_LETTER::")
        linkedin.chamar = com_desvio(FakeLinkedIn(), "actions/navigation", lambda c: pagina(rsc))
        con = buscar.abrir()
        semear(con, "4482617482")
        _, saida = aplicar(1, seco=True)
        assert "cortada: tipo de campo não mapeado" in saida and estados(con) == ["cortada"], saida


def _com_pergunta_de_escolha(falso, job_com_escolha):
    """O formulário do job ganha uma irmã `_label`: a resposta numérica guardada vira pendência."""
    chave = next(q["chave"] for q in linkedin.perguntas(
        linkedin.pedido(ler("formulario.rsc"), "submit"), ler("formulario.rsc")) if q["tipo"] == "UNKNOWN")
    rsc = ler("formulario.rsc") + " " + chave + "_label"
    return com_desvio(falso, "actions/navigation", lambda c: pagina(rsc) if job_com_escolha in c else None)


def test_pendencia_nao_gasta_a_cota_e_fica_nova():
    with ambiente():
        linkedin.chamar = _com_pergunta_de_escolha(FakeLinkedIn(), "4482617482")
        con = buscar.abrir()
        semear(con, "4482617482", "4482617483")
        # A pendente lidera a fila (título com a stack); sem isso a ordem seria só de inserção.
        con.execute("UPDATE vagas SET titulo = 'Python Engineer' WHERE chave = 'linkedin:4482617482'")
        con.commit()
        _, saida = aplicar(1, seco=True)
        assert "resposta não Sim/Não" in saida and "sem currículo" in saida, saida
        assert estados(con) == ["nova", "nova"]


def test_preparar_linkedin_calcula_a_pretensao_por_vaga():
    with ambiente():
        con = buscar.abrir()
        semear(con, "4482617482")
        v = con.execute("SELECT * FROM vagas").fetchone()
        guardadas = {"Há quantos anos você já usa Python no trabalho?": "2",
                     "Há quantos anos você já usa Amazon Web Services no trabalho?": "1",
                     "Você trabalharia presencialmente?": "sim"}
        r = dict(R_TESTE, formulario_linkedin=guardadas)
        rsc = ler("formulario_decimal.rsc")
        # Pleno: 9000 em CLT, x1,4 em PJ, menos 15% de desconto nos dois.
        for form, esperado in ((rsc, "10710"), (rsc.replace("salarial PJ?", "salarial?"), "7650")):
            linkedin.chamar = com_desvio(FakeLinkedIn(), "actions/navigation", lambda c: pagina(form))
            e = buscar.preparar_linkedin(v, r)
            assert e["pendencias"] == [] and e["valores"][PRETENSAO] == esperado, (e["pendencias"], esperado)


def test_teto_de_vagas_puladas():
    with ambiente():
        linkedin.chamar = FakeLinkedIn()
        with open(buscar.RESPOSTAS, "w", encoding="utf-8") as f:
            json.dump(dict(R_TESTE, formulario_linkedin={}), f)
        semear(buscar.abrir(), "4482617482", "4482617483", "4482617484", "4482617485")
        antigo, buscar.MAX_PULADAS = buscar.MAX_PULADAS, 2
        try:
            _, saida = aplicar(1, seco=True)
        finally:
            buscar.MAX_PULADAS = antigo
        assert saida.count("pendência\n") == 2, saida


def test_erro_numa_vaga_nao_derruba_o_lote():
    with ambiente():
        def cai(corpo):
            raise RuntimeError("vaga respondeu 429")
        linkedin.chamar = com_desvio(FakeLinkedIn(), "/jobs/view/4482617482", cai)
        con = buscar.abrir()
        semear(con, "4482617482", "4482617483")
        _, saida = aplicar(2, seco=True)
        assert "erro: vaga respondeu 429" in saida and "sem currículo" in saida, saida
        assert estados(con) == ["nova", "nova"]


def test_sessao_expirada_na_preparacao_sai_com_2():
    with ambiente():
        def expira(corpo):
            raise linkedin.SessaoExpirada(linkedin.SESSAO)
        linkedin.chamar = com_desvio(FakeLinkedIn(), "/jobs/view/", expira)
        semear(buscar.abrir(), "4482617482")
        erro = io.StringIO()
        with contextlib.redirect_stderr(erro), contextlib.redirect_stdout(io.StringIO()):
            codigo = buscar.main(["aplicar", "--seco"])
        assert codigo == 2 and erro.getvalue().strip() == linkedin.SESSAO


def _sonos():
    """Troca time.sleep do buscar por um coletor; devolve (lista, restaurar)."""
    dormidas, antigo = [], buscar.time.sleep
    buscar.time.sleep = dormidas.append
    return dormidas, lambda: setattr(buscar.time, "sleep", antigo)


def test_aplicar_envia_marca_e_nao_segue():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        con = buscar.abrir()
        semear(con, "4482617482")
        curriculo(tmp, "linkedin:4482617482", 88)
        codigo, saida = enviar(1)
        assert codigo == 0 and "1 de 1 candidaturas enviadas" in saida, saida
        corpo = falso.enviados("easyapply.submit")[0]
        p = corpo["serverRequest"]["requestedArguments"]["payload"]
        assert linkedin.valor_estado(corpo, p["followCompany"]["key"]) is False
        assert linkedin.valor_estado(corpo, p["topChoiceInfo"]["isTopChoiceMarked"]["value"]["key"]) is False
        assert linkedin.valor_estado(corpo, "ea.q::32383411340::LARGER_RESUME::selectedResume") == \
            linkedin.id_do_ambry(ler_json("ambry_put.json"))
        r = con.execute("SELECT * FROM vagas").fetchone()
        assert (r["estado"], r["aplicada_em"]) == ("aplicada", buscar.hoje())
        d = buscar.ler_dossie(r)
        assert (d["enviada_em"], d["preferencial"], d["seguir"]) == (buscar.hoje(), False, False), d
        placar = io.StringIO()
        with contextlib.redirect_stdout(placar):
            buscar.cmd_placar(None)
        assert re.search(r"linkedin\s+1\s+1\s", placar.getvalue()), placar.getvalue()


def test_intervalo_entre_envios():
    with ambiente() as tmp:
        linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482", "4482617483")
        for chave in ("linkedin:4482617482", "linkedin:4482617483"):
            curriculo(tmp, chave, 88)
        dormidas, restaurar = _sonos()
        try:
            _, saida = enviar(2)
        finally:
            restaurar()
        assert "2 de 2" in saida and len(dormidas) == 1 and 25 <= dormidas[0] <= 35, (saida, dormidas)


def test_preferencial_so_com_ats_90_elegibilidade_e_limite():
    msg = "Quero muito esta vaga pela stack de agentes."
    # Mensagem é opcional: o LinkedIn não exige mínimo (captura 24/10).
    for ats, mensagem, ja_no_mes, esperado in ((92, msg, 0, True), (92, "", 0, True),
                                               (89, msg, 0, False), (92, msg, 2, False)):
        with ambiente() as tmp:
            falso = linkedin.chamar = FakeLinkedIn()
            for n in range(ja_no_mes):
                pasta = os.path.join(buscar.DOSSIES, f"antiga-{n}")
                os.makedirs(pasta)
                with open(os.path.join(pasta, f"linkedin-{n}.json"), "w", encoding="utf-8") as f:
                    json.dump({"preferencial": True, "enviada_em": buscar.hoje()}, f)
            semear(buscar.abrir(), "4482617482")
            curriculo(tmp, "linkedin:4482617482", ats, mensagem)
            enviar(1)
            corpo = falso.enviados("easyapply.submit")[0]
            topo = corpo["serverRequest"]["requestedArguments"]["payload"]["topChoiceInfo"]
            assert linkedin.valor_estado(corpo, topo["isTopChoiceMarked"]["value"]["key"]) is esperado, \
                (ats, mensagem, ja_no_mes)
            assert linkedin.valor_estado(corpo, topo["topChoiceMessage"]["value"]["key"]) == \
                (mensagem if esperado else ""), (ats, mensagem, ja_no_mes)


def test_preferencial_respeita_elegibilidade_do_linkedin():
    rsc = ler("formulario.rsc")
    for velho, novo in (('"isEligibleToSeeTopChoice":true', '"isEligibleToSeeTopChoice":false'),
                        ('"isTopChoiceCreditLimitReached":false', '"isTopChoiceCreditLimitReached":true')):
        assert velho in rsc, velho
        with ambiente() as tmp:
            falso = FakeLinkedIn()
            linkedin.chamar = com_desvio(falso, "actions/navigation", lambda c: pagina(rsc.replace(velho, novo)))
            semear(buscar.abrir(), "4482617482")
            curriculo(tmp, "linkedin:4482617482", 95, "Quero muito esta vaga pela stack de agentes.")
            enviar(1)
            corpo = falso.enviados("easyapply.submit")[0]
            topo = corpo["serverRequest"]["requestedArguments"]["payload"]["topChoiceInfo"]
            assert linkedin.valor_estado(corpo, topo["isTopChoiceMarked"]["value"]["key"]) is False, novo


def test_campo_resume_tambem_sobe_o_pdf():
    # Algumas vagas usam RESUME no lugar de LARGER_RESUME (captura 4481061055).
    with ambiente() as tmp:
        rsc = ler("formulario.rsc").replace("::LARGER_RESUME::", "::RESUME::")
        falso = FakeLinkedIn()
        linkedin.chamar = com_desvio(falso, "actions/navigation", lambda c: pagina(rsc))
        semear(buscar.abrir(), "4482617482")
        curriculo(tmp, "linkedin:4482617482", 88)
        enviar(1)
        corpo = falso.enviados("easyapply.submit")[0]
        assert linkedin.valor_estado(corpo, "ea.q::32383411340::RESUME::selectedResume") == \
            linkedin.id_do_ambry(ler_json("ambry_put.json"))


def test_ats_baixo_corta():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        con = buscar.abrir()
        semear(con, "4482617482")
        curriculo(tmp, "linkedin:4482617482", 84)
        _, saida = aplicar(1, seco=True)
        assert "ATS 84 < 85" in saida and falso.enviados("easyapply.submit") == [], saida
        assert estados(con) == ["cortada"]


def test_submit_sem_confirmacao_corta_e_nao_reenvia():
    with ambiente() as tmp:
        resposta = ler_json("submit.json")["resposta"].replace('"errors":[]', '"errors":["x"]')
        falso = linkedin.chamar = FakeLinkedIn(submit=resposta)
        con = buscar.abrir()
        semear(con, "4482617482")
        curriculo(tmp, "linkedin:4482617482", 88)
        erro = io.StringIO()
        with contextlib.redirect_stderr(erro):
            _, saida = enviar(1)
        assert "0 de 1" in saida and "não confirmou" in erro.getvalue(), (saida, erro.getvalue())
        assert estados(con) == ["cortada"]
        enviar(1)
        assert len(falso.enviados("easyapply.submit")) == 1


def test_falha_de_um_envio_nao_para_o_lote():
    with ambiente() as tmp:
        quedas = []

        def cai_uma_vez(corpo):
            if not quedas:
                quedas.append(1)
                raise RuntimeError("submit respondeu 500")
        falso = FakeLinkedIn()
        linkedin.chamar = com_desvio(falso, "easyapply.submit", cai_uma_vez)
        con = buscar.abrir()
        semear(con, "4482617482", "4482617483")
        for chave in ("linkedin:4482617482", "linkedin:4482617483"):
            curriculo(tmp, chave, 88)
        dormidas, restaurar = _sonos()
        erro = io.StringIO()
        try:
            with contextlib.redirect_stderr(erro):
                _, saida = enviar(2)
        finally:
            restaurar()
        assert "1 de 2" in saida and "submit respondeu 500" in erro.getvalue(), (saida, erro.getvalue())
        assert estados(con) == ["aplicada", "nova"]


def test_sessao_cai_no_meio_do_lote():
    with ambiente() as tmp:
        linkedin.chamar = FakeLinkedIn(cair_no_submit=2)
        con = buscar.abrir()
        semear(con, "4482617482", "4482617483")
        for chave in ("linkedin:4482617482", "linkedin:4482617483"):
            curriculo(tmp, chave, 88)
        aplicar(2, seco=True)
        dormidas, restaurar = _sonos()
        erro = io.StringIO()
        try:
            with contextlib.redirect_stderr(erro), contextlib.redirect_stdout(io.StringIO()):
                codigo = buscar.main(["aplicar", "--quantas", "2"])
        finally:
            restaurar()
        assert codigo == 2 and linkedin.SESSAO in erro.getvalue()
        assert not os.path.exists(aprovacao()), "o ok sobreviveu à sessão caída"
        assert estados(con) == ["aplicada", "nova"], estados(con)


def test_reaplicar_nao_reenvia():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482")
        curriculo(tmp, "linkedin:4482617482", 88)
        enviar(1)
        _, saida = enviar(1)
        assert len(falso.enviados("easyapply.submit")) == 1 and "nenhuma vaga" in saida, saida


def test_envio_sem_seco_previo_sai_com_1():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482")
        curriculo(tmp, "linkedin:4482617482", 88)
        erro = io.StringIO()
        with contextlib.redirect_stderr(erro):
            codigo, _ = aplicar(1, seco=False)
        assert codigo == 1 and "--seco" in erro.getvalue(), erro.getvalue()
        assert falso.chamadas == [], "sem ok não há chamada ao LinkedIn"


def test_aprovacao_de_outro_dia_nao_vale():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482")
        curriculo(tmp, "linkedin:4482617482", 88)
        aplicar(1, seco=True)
        with open(aprovacao(), encoding="utf-8") as f:
            ok = json.load(f)
        with open(aprovacao(), "w", encoding="utf-8") as f:
            json.dump(dict(ok, data="2000-01-01"), f)
        with contextlib.redirect_stderr(io.StringIO()):
            codigo, _ = aplicar(1, seco=False)
        assert codigo == 1 and falso.enviados("easyapply.submit") == []


def test_so_envia_o_que_o_seco_mostrou_como_pronta():
    with ambiente() as tmp:
        base = FakeLinkedIn()

        def cai(corpo):
            raise RuntimeError("vaga respondeu 429")
        linkedin.chamar = com_desvio(base, "/jobs/view/4482617483", cai)
        con = buscar.abrir()
        semear(con, "4482617482", "4482617483")
        for chave in ("linkedin:4482617482", "linkedin:4482617483"):
            curriculo(tmp, chave, 88)
        _, saida = aplicar(2, seco=True)
        assert "erro: vaga respondeu 429" in saida, saida
        linkedin.chamar = base
        dormidas, restaurar = _sonos()
        try:
            _, saida = aplicar(2, seco=False)
        finally:
            restaurar()
        assert "fora do lote aprovado: linkedin:4482617483" in saida, saida
        assert "1 de 1 candidaturas enviadas" in saida and len(base.enviados("easyapply.submit")) == 1
        assert estados(con) == ["aplicada", "nova"]


def test_ok_vale_uma_vez():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482", "4482617483")
        for chave in ("linkedin:4482617482", "linkedin:4482617483"):
            curriculo(tmp, chave, 88)
        enviar(1)
        assert not os.path.exists(aprovacao())
        with contextlib.redirect_stderr(io.StringIO()):
            codigo, _ = aplicar(1, seco=False)
        assert codigo == 1 and len(falso.enviados("easyapply.submit")) == 1


def test_um_dossie_por_vaga_mesmo_com_titulo_igual():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        con = buscar.abrir()
        buscar.guardar(con, [{"chave": f"linkedin:{i}", "fonte": "linkedin", "origem": "Agento",
                              "titulo": "Forward Deployed Engineer", "url": "", "publicada": buscar.hoje(),
                              "modelo": "remoto", "contrato": "", "nivel": "", "local": "Brasil",
                              "texto": "python"} for i in ("4482617482", "4482617483")], P_TESTE)
        v1, v2 = con.execute("SELECT * FROM vagas ORDER BY chave").fetchall()
        assert buscar.dossie_linkedin(v1) != buscar.dossie_linkedin(v2)
        curriculo(tmp, v1["chave"], 92)
        enviar(1)
        assert buscar.ler_dossie(v2) == {}
        _, saida = aplicar(1, seco=True)
        assert "sem currículo" in saida and "pronta" not in saida, saida
        assert len(falso.enviados("easyapply.submit")) == 1


def test_revisar_nao_reabre_corte_do_linkedin():
    rsc = ler("formulario.rsc")
    recusa = ler_json("submit.json")["resposta"].replace('"errors":[]', '"errors":["x"]')
    externa = com_desvio(FakeLinkedIn(), "/jobs/view/", lambda c: pagina(ler("vaga_externa.html")))
    tipo = com_desvio(FakeLinkedIn(), "actions/navigation",
                      lambda c: pagina(rsc.replace("::EMAIL::", "::COVER_LETTER::")))
    for nome, falso, ats in (("externa", externa, None), ("tipo", tipo, None),
                             ("ATS", FakeLinkedIn(), 84), ("recusa", FakeLinkedIn(submit=recusa), 88)):
        with ambiente() as tmp:
            linkedin.chamar = falso
            con = buscar.abrir()
            semear(con, "4482617482")
            if ats:
                curriculo(tmp, "linkedin:4482617482", ats)
            with contextlib.redirect_stderr(io.StringIO()):
                enviar(1)
            assert estados(con) == ["cortada"], nome
            with contextlib.redirect_stdout(io.StringIO()):
                buscar.cmd_revisar(None)
            assert estados(con) == ["cortada"], nome
    # Controle: corte sem motivo do LinkedIn continua reaberto pelo perfil.
    with ambiente():
        con = buscar.abrir()
        semear(con, "4482617482")
        con.execute("UPDATE vagas SET estado = 'cortada'")
        con.commit()
        with contextlib.redirect_stdout(io.StringIO()):
            buscar.cmd_revisar(None)
        assert estados(con) == ["nova"]


def test_estrela_desconta_as_preferenciais_do_lote():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        ids = ("4482617482", "4482617483", "4482617484")
        semear(buscar.abrir(), *ids)
        for i in ids:
            curriculo(tmp, f"linkedin:{i}", 95)
        _, saida = aplicar(3, seco=True)
        assert saida.count("★") == 2, saida
        dormidas, restaurar = _sonos()
        try:
            aplicar(3, seco=False)
        finally:
            restaurar()
        marcas = []
        for corpo in falso.enviados("easyapply.submit"):
            topo = corpo["serverRequest"]["requestedArguments"]["payload"]["topChoiceInfo"]
            marcas.append(linkedin.valor_estado(corpo, topo["isTopChoiceMarked"]["value"]["key"]))
        assert marcas == [True, True, False], marcas


def test_submit_impossivel_falha_antes_do_upload():
    with ambiente() as tmp:
        rsc = ler("formulario.rsc")
        seguir = linkedin.pedido(rsc, "submit")["requestedArguments"]["payload"]["followCompany"]["key"]
        sem_seguir = rsc.replace(',{"key":{"value":{"$case":"id","id":"' + seguir + '"}}}', "")
        assert sem_seguir != rsc
        falso = FakeLinkedIn()
        linkedin.chamar = com_desvio(falso, "actions/navigation", lambda c: pagina(sem_seguir))
        con = buscar.abrir()
        semear(con, "4482617482", "4482617483")
        for chave in ("linkedin:4482617482", "linkedin:4482617483"):
            curriculo(tmp, chave, 88)
        dormidas, restaurar = _sonos()
        erro = io.StringIO()
        try:
            with contextlib.redirect_stderr(erro):
                _, saida = enviar(2)
        finally:
            restaurar()
        assert "0 de 2" in saida and erro.getvalue().count("falhou:") == 2, (saida, erro.getvalue())
        for trecho in ("handlePickedFile", "/ambry/", "setResumeFormBinding", "easyapply.submit"):
            assert falso.enviados(trecho) == [], trecho
        assert estados(con) == ["nova", "nova"]


def test_pdf_sumido_antes_do_upload_vira_runtime_error():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        con = buscar.abrir()
        semear(con, "4482617482")
        curriculo(tmp, "linkedin:4482617482", 88)
        e = buscar.preparar_linkedin(con.execute("SELECT * FROM vagas").fetchone(), R_TESTE)
        assert e["situacao"] == "pronta", e["situacao"]
        os.remove(e["d"]["cv"])
        try:
            buscar.enviar_linkedin(e, R_TESTE, False)
        except RuntimeError:
            pass
        else:
            raise AssertionError("PDF sumido não virou RuntimeError")
        assert falso.enviados("handlePickedFile") == []


def test_quantas_menor_que_1_e_recusado():
    with ambiente():
        falso = linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482")
        for n in ("0", "-2"):
            erro = io.StringIO()
            try:
                with contextlib.redirect_stderr(erro):
                    buscar.main(["aplicar", "--quantas", n, "--seco"])
            except SystemExit as saiu:
                assert saiu.code == 2, saiu.code
            else:
                raise AssertionError(f"--quantas {n} foi aceito")
        assert falso.chamadas == []


def test_ats_baixo_ja_registrado_corta_sem_rede():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        con = buscar.abrir()
        semear(con, "4482617482")
        curriculo(tmp, "linkedin:4482617482", 84)
        _, saida = aplicar(1, seco=True)
        assert "cortada: ATS 84 < 85" in saida and estados(con) == ["cortada"], saida
        assert [u for _, u, _ in falso.chamadas if "/jobs/view/" in u or "navigation" in u] == []


def _marcas(falso):
    marcas = []
    for corpo in falso.enviados("easyapply.submit"):
        topo = corpo["serverRequest"]["requestedArguments"]["payload"]["topChoiceInfo"]
        marcas.append(linkedin.valor_estado(corpo, topo["isTopChoiceMarked"]["value"]["key"]))
    return marcas


def test_ok_guarda_a_estrela_e_o_envio_obedece():
    with ambiente() as tmp:
        falso = linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482")
        curriculo(tmp, "linkedin:4482617482", 88)
        _, saida = aplicar(1, seco=True)
        assert "★" not in saida
        with open(aprovacao(), encoding="utf-8") as f:
            assert json.load(f)["chaves"] == {"linkedin:4482617482": False}
        # Depois do ok a nota sobe: a tabela que o usuário viu não tinha ★, então o envio também não.
        curriculo(tmp, "linkedin:4482617482", 95, "Quero muito esta vaga pela stack de agentes.")
        _, saida = aplicar(1, seco=False)
        assert _marcas(falso) == [False] and "★" not in saida, saida


def test_estrela_nao_migra_quando_a_aprovada_falha():
    with ambiente() as tmp:
        base = FakeLinkedIn()
        linkedin.chamar = base
        ids = ("4482617482", "4482617483", "4482617484")
        semear(buscar.abrir(), *ids)
        for i in ids:
            curriculo(tmp, f"linkedin:{i}", 95)
        _, saida = aplicar(3, seco=True)
        assert saida.count("★") == 2, saida

        def cai(corpo):
            raise RuntimeError("vaga respondeu 429")
        linkedin.chamar = com_desvio(base, "/jobs/view/" + ids[0], cai)
        dormidas, restaurar = _sonos()
        try:
            aplicar(3, seco=False)
        finally:
            restaurar()
        assert _marcas(base) == [True, False], _marcas(base)


def test_ok_malformado_vale_como_sem_ok():
    for conteudo in ("[]", '{"data": "%s"}', '{"data": "%s", "chaves": "linkedin:4482617482"}',
                     '{"data": "%s", "chaves": ["linkedin:4482617482"]}'):
        with ambiente() as tmp:
            falso = linkedin.chamar = FakeLinkedIn()
            semear(buscar.abrir(), "4482617482")
            curriculo(tmp, "linkedin:4482617482", 88)
            with open(aprovacao(), "w", encoding="utf-8") as f:
                f.write(conteudo.replace("%s", buscar.hoje()))
            with contextlib.redirect_stderr(io.StringIO()):
                codigo, _ = aplicar(1, seco=False)
            assert codigo == 1 and falso.chamadas == [], conteudo


def test_ok_vazio_sai_sem_chamar_o_linkedin():
    with ambiente():
        falso = linkedin.chamar = FakeLinkedIn()
        semear(buscar.abrir(), "4482617482", "4482617483")
        aplicar(2, seco=True)
        antes = len(falso.chamadas)
        codigo, saida = aplicar(2, seco=False)
        assert codigo == 0 and "nenhuma vaga" in saida, saida
        assert len(falso.chamadas) == antes and not os.path.exists(aprovacao())


def test_marcar_nova_limpa_o_motivo():
    with ambiente() as tmp:
        recusa = ler_json("submit.json")["resposta"].replace('"errors":[]', '"errors":["x"]')
        linkedin.chamar = FakeLinkedIn(submit=recusa)
        con = buscar.abrir()
        semear(con, "4482617482")
        curriculo(tmp, "linkedin:4482617482", 88)
        with contextlib.redirect_stderr(io.StringIO()):
            enviar(1)
        v = con.execute("SELECT * FROM vagas").fetchone()
        assert buscar.ler_dossie(v)["motivo"]
        with contextlib.redirect_stdout(io.StringIO()):
            buscar.cmd_marcar(argparse.Namespace(chave=v["chave"], estado="nova"))
        d = buscar.ler_dossie(v)
        assert "motivo" not in d and d["ats"] == 88, d
        # Sem o motivo velho, um corte do perfil que depois cai reabre a vaga como qualquer outra.
        for excluir, esperado in ((["engineer"], ["cortada"]), ([], ["nova"])):
            buscar.perfil = lambda excluir=excluir: dict(P_TESTE, excluir=excluir)
            with contextlib.redirect_stdout(io.StringIO()):
                buscar.cmd_revisar(None)
            assert estados(con) == esperado, (excluir, estados(con))


def rodar():
    for nome, funcao in sorted(globals().items()):
        if nome.startswith("test_") and callable(funcao):
            funcao()


if __name__ == "__main__":
    rodar()
    print("ok")
