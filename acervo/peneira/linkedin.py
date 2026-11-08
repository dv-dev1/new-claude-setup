#!/usr/bin/env python3
"""LinkedIn Easy Apply pela sessão `linkedin` do playwright-cli: busca, formulário e envio."""

import base64
import bisect
import html
import json
import os
import random
import re
import string
import subprocess
import time
import unicodedata
import urllib.parse

BASE = "https://www.linkedin.com"
GEO_BRASIL = "106057199"
# ponytail: a busca server-rendered traz 7 vagas por página (captura 24/10/2026); mudou, mude aqui.
POR_PAGINA = 7
MODELOS = {"remoto": "remoto", "híbrido": "hibrido", "hibrido": "hibrido",
           "presencial": "presencial"}

# companyName, trackingId e ATS vêm juntos só no Navigate do Easy Apply; o
# primeiro trackingId da página é de outro componente.
EASY = re.compile(r'\\"companyName\\":\\"([^"\\]+)\\",\\"trackingId\\":\\"([^"\\]+)\\",'
                  r'\\"applicantTrackingSystemName\\":\\"LinkedIn\\"')
ONDE = re.compile(r'\\"children\\":\[\\"[^"\\]+ • ([^"\\]+)\\"\]')
SOBRE = re.compile(r"Sobre a vaga</h2>.*?<span[^>]*>(.*?)</span></div>", re.S)


def url_busca(termo, janela, inicio):
    consulta = {"keywords": termo, "f_AL": "true", "f_TPR": janela,
                "geoId": GEO_BRASIL, "start": inicio}
    return f"{BASE}/jobs/search/?{urllib.parse.urlencode(consulta)}"


def vagas_da_busca(pagina):
    texto = html.unescape(pagina)
    vistos, saida = set(), []
    for m in re.finditer(r'\{"trackingUrn":"urn:li:jobPosting:(\d+)"', texto):
        obj, _ = json.JSONDecoder().raw_decode(texto, m.start())
        if m.group(1) not in vistos and obj.get("title"):
            vistos.add(m.group(1))
            saida.append((m.group(1), obj["title"]))
    return saida


def detalhe_da_vaga(pagina):
    easy = EASY.search(pagina)
    if not easy:
        return None
    onde, corpo = ONDE.search(pagina), SOBRE.search(pagina)
    local = onde.group(1) if onde else ""
    modelo = re.search(r"\s*\((\w+)\)$", local)
    texto = html.unescape(re.sub(r"<[^>]+>", " ", corpo.group(1))) if corpo else ""
    return {"empresa": easy.group(1), "tracking": easy.group(2),
            "local": local[:modelo.start()] if modelo else local,
            "modelo": MODELOS.get(modelo.group(1).lower(), "") if modelo else "",
            "texto": re.sub(r"\s+", " ", texto).strip()}


def recorte_vaga(pagina):
    """Só os trechos que detalhe_da_vaga lê: o resto traz dados do usuário logado."""
    pedacos = [m.group(0) for m in (rx.search(pagina) for rx in (EASY, ONDE, SOBRE)) if m]
    i = pagina.find("applicantTrackingSystemName")
    if i >= 0:
        pedacos.append(pagina[max(0, i - 300):i + 300])
    return "\n".join(pedacos)


REQ = "com.linkedin.sdui.requests.jobseeker.easyapply."
TELA_EA = "com.linkedin.sdui.flagshipnav.jobs.easyapply.EasyApply"
_INICIO_PEDIDO = '{"$type":"proto.sdui.actions.core.ServerRequest","value":{"requestId":"' + REQ
# O cliente web não manda estes campos nem os "$undefined" do RSC.
_SO_DO_SERVIDOR = ("maxRetries", "backOffMultiplier", "maxSeconds")
# Grupo 1 só existe no padrão decimal `^[0-9]+([.][0-9]+)?$`; o inteiro é `^[0-9]+$`.
NUMERICO = re.compile(
    r'"regexPattern":"\^\[0-9\]\+(\(\[\.\]\[0-9\]\+\)\?)?\$"\}\},'
    r'"value":\{"\$type":"proto\.sdui\.bindings\.core\.Bindable",'
    r'"key":\{"key":\{"value":\{"\$case":"id","id":"([^"]+)"')
_PREFIXO = re.compile(r'"prefix":"((?:[^"\\]|\\.)+)"')
# Qualquer chave ea.q:: ancora o prefixo: o de um campo fixo (Currículo, E-mail) cai na própria
# chave e não pode rotular a pergunta seguinte. `_label` é a irmã da escolha e não conta.
_CHAVE_EA = re.compile(r"ea\.q::[A-Za-z0-9_]+(?:::[A-Za-z0-9_]+)*")
_PERGUNTA = re.compile(r"ea\.q::\d+::[A-Za-z_]+::value_\d+_\d+")
_JANELA_ROTULO = 20000
# O prefixo da pergunta vem logo antes do componentKey do campo, que traz o id dela. Quando o
# campo é uma linha $L definida bem adiante, a próxima chave ea.q:: já é de outra pergunta.
_FOCO = re.compile(r"easyApplyFieldFocus_ea_validation_p\d+_\d+_(\d+)")
_ALCANCE_FOCO = 300


def pedido(texto, nome):
    i = texto.find(_INICIO_PEDIDO + nome + '"')
    if i < 0:
        return None
    sr = json.JSONDecoder().raw_decode(texto, i)[0]["value"]
    return {k: v for k, v in sr.items() if k not in _SO_DO_SERVIDOR and v != "$undefined"}


def _rotulos(rsc):
    """chave -> pergunta: o `prefix` do i18nPattern que antecede a chave, o primeiro vence."""
    chaves = [(m.start(), m.group(0)) for m in _CHAVE_EA.finditer(rsc)
              if not m.group(0).endswith("_label")]
    inicios = [i for i, _ in chaves]
    achados = {}
    for p in _PREFIXO.finditer(rsc):
        k = bisect.bisect_left(inicios, p.end())
        if (k == len(chaves) or inicios[k] - p.end() > _JANELA_ROTULO
                or not _PERGUNTA.fullmatch(chaves[k][1])):
            continue
        # O prefixo de "Inclua uma mensagem" (preferencial) tem topChoice até a chave.
        if rsc.find("topChoice", p.end(), inicios[k]) >= 0:
            continue
        achados.setdefault(chaves[k][1], json.loads('"' + p.group(1) + '"'))
    # Segunda passada: só preenche o que a primeira não rotulou, então os rótulos achados não mudam.
    for p in _PREFIXO.finditer(rsc):
        foco = _FOCO.search(rsc, p.end(), p.end() + _ALCANCE_FOCO)
        if foco:
            for _, chave in chaves:
                if _PERGUNTA.fullmatch(chave) and chave.split("::")[1] == foco.group(1):
                    achados.setdefault(chave, json.loads('"' + p.group(1) + '"'))
    return achados


def rotulo(rsc, chave):
    # Sem achado a própria chave identifica a pergunta na pendência.
    return _rotulos(rsc).get(chave, chave)


def opcoes(rsc, chave):
    """Valores da lista de um select, sem o placeholder (`disabled`); [] se o campo não tem lista."""
    # A lista termina colada no valueStateKey da própria chave; o options mais próximo antes dele é o dela.
    alvo = '"valueStateKey":{"key":{"value":{"$case":"id","id":"' + chave + '"}}}'
    decodificador, achadas = json.JSONDecoder(), []
    for m in re.finditer(re.escape(alvo), rsc):
        i = rsc.rfind('"options":[', 0, m.start())
        if i < 0:
            continue
        try:
            itens, fim = decodificador.raw_decode(rsc, i + len('"options":'))
        except ValueError:
            continue
        if fim != m.start() - 1:
            continue
        for item in itens:
            if isinstance(item, str) and item.startswith("$L"):
                linha = re.search(r"(?m)^" + re.escape(item[2:]) + ":", rsc)
                item = decodificador.raw_decode(rsc, linha.end())[0] if linha else None
            props = item[3] if isinstance(item, list) and len(item) > 3 else None
            if isinstance(props, dict) and not props.get("disabled") and "value" in props:
                achadas.append(props["value"])
        break
    return achadas


def perguntas(sr, rsc):
    p = sr["requestedArguments"]["payload"]
    validadores, rotulos = NUMERICO.findall(rsc), _rotulos(rsc)
    numericos = {chave for _, chave in validadores}
    decimais = {chave for decimal, chave in validadores if decimal}
    saida = []
    for campo in p["questionFieldsList"]:
        chave = campo["key"]
        _, qid, tipo, nome = chave.split("::")
        escolha = tipo == "UNKNOWN" and chave + "_label" in rsc
        saida.append({"chave": chave, "id": qid, "tipo": tipo, "campo": nome,
                      "numerico": chave in numericos, "decimal": chave in decimais,
                      "escolha": escolha, "opcoes": opcoes(rsc, chave) if escolha else [],
                      "rotulo": rotulos.get(chave, chave)})
    for tipo, lista in (("LISTA", p.get("questionListFieldsList", [])),
                        ("DATA", p.get("questionDateFieldsList", []))):
        for campo in lista:
            chave = campo.get("key") or json.dumps(campo)
            saida.append({"chave": chave, "id": "", "tipo": tipo, "campo": "", "numerico": False,
                          "decimal": False, "escolha": False, "opcoes": [],
                          "rotulo": rotulos.get(chave, chave)})
    return saida


def normalizar(texto):
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", sem_acento.lower())).strip()


_SIM, _NAO = {"sim", "yes"}, {"nao", "no"}
_OUTRO_SALARIO = {"atual", "ultimo", "current", "last", "anual", "annual", "hora", "hour",
                  "usd", "dolar", "dolares", "minimo", "minimos", "assalariado"}


def _opcao(valor, opcoes):
    """A opção da lista que a resposta guardada escolhe: pelo texto, ou Sim/Não no idioma da lista."""
    normal = normalizar(str(valor))
    for o in opcoes:
        if normalizar(o) == normal:
            return o
    for grupo in (_SIM, _NAO):
        if normal in grupo:
            return next((o for o in opcoes if normalizar(o) in grupo), None)
    return None


def _pretensao(q, r):
    """Pretensão calculada pela vaga (CLT ou PJ, conforme o rótulo); None se a pergunta é outra."""
    rotulo = normalizar(q["rotulo"])
    if "pretensao" not in r or not any(t in rotulo for t in ("pretens", "salar")):
        return None
    # Salário atual, anual, por hora ou em dólar não é a pretensão mensal: fica para o usuário.
    if _OUTRO_SALARIO & set(rotulo.split()):
        return None
    return str(round(r["pretensao"]["pj" if "pj" in rotulo.split() else "clt"]))


def resolver(qs, r, cv_id):
    """(valores por chave, pendências). Só responde o que está guardado: nunca inventa."""
    guardadas = {normalizar(k): v for k, v in r.get("formulario_linkedin", {}).items()}
    valores, pendencias = {}, []
    for q in qs:
        if q["tipo"] == "EMAIL":
            valores[q["chave"]] = r["email"]
        elif q["tipo"] in ("LARGER_RESUME", "RESUME"):
            valores[q["chave"]] = cv_id
        elif q["tipo"] == "PHONE_MOBILE":
            valores[q["chave"]] = ("br" if q["campo"] == "phoneCountryCode"
                                   else re.sub(r"\D", "", r["telefone"]))
        elif q["tipo"] == "UNKNOWN" and (q["numerico"] or q["escolha"]):
            valor = guardadas.get(normalizar(q["rotulo"]))
            lista = q.get("opcoes") or []
            dica = f" (opções: {', '.join(lista)})" if lista else ""
            if valor is None and q["numerico"]:
                valor = _pretensao(q, r)
            if valor is None:
                pendencias.append(f"sem resposta: {q['rotulo']}{dica}")
            elif q["escolha"] and lista:
                escolhida = _opcao(valor, lista)
                if escolhida is None:
                    pendencias.append(f"resposta fora das opções para '{q['rotulo']}': {valor}{dica}")
                else:
                    valores[q["chave"]] = escolhida
            elif q["escolha"]:
                sim_nao = {"sim": "Yes", "yes": "Yes", "nao": "No", "no": "No"}.get(
                    normalizar(str(valor)))
                if sim_nao:
                    valores[q["chave"]] = sim_nao
                else:
                    pendencias.append(f"resposta não Sim/Não para '{q['rotulo']}': {valor}")
            elif not re.fullmatch(r"[0-9]{1,20}([.][0-9]{1,20})?" if q.get("decimal") else r"[0-9]{1,20}",
                                  str(valor)):
                pendencias.append(f"resposta não numérica para '{q['rotulo']}': {valor}")
            else:
                valores[q["chave"]] = str(valor)
        else:
            pendencias.append(f"tipo {q['tipo']} não mapeado: {q['rotulo']}")
    return valores, pendencias


URL_NAVEGACAO = f"{BASE}/flagship-web/rsc-action/actions/navigation?screenId={TELA_EA}&sduiid={TELA_EA}"
_CASO = {bool: "booleanValue", list: "stringListValue", dict: "mediaListValue"}


def estado(chave, valor):
    return {"key": chave, "namespace": "MemoryNamespace", "value": valor,
            "originalProtoCase": _CASO.get(type(valor), "stringValue"),
            "protoKey": {"$type": "proto.sdui.Key", "value": {"$case": "id", "id": chave}}}


def corpo_servidor(sr, estados):
    """Envelope que o cliente SDUI manda em todo server-request."""
    argumentos = dict(sr["requestedArguments"], states=estados, screenId=TELA_EA,
                      knownTemplateIds=[])
    return {"requestId": sr["requestId"], "serverRequest": sr, "states": estados,
            "requestedArguments": argumentos}


def corpo_submit(sr, valores, seguir, preferencial, mensagem):
    p = sr["requestedArguments"]["payload"]
    # Só as chaves pedidas vão no corpo: a `_label` das perguntas de escolha não está entre elas.
    chaves = [k["key"]["value"]["id"] for k in sr["requestedArguments"]["requestedStateKeys"]]
    # Sem a chave o corpo não diria "não seguir" e o servidor segue a empresa por padrão.
    if p["followCompany"]["key"] not in chaves:
        raise RuntimeError("submit sem o estado de seguir empresa: não envio")
    extra = {p["followCompany"]["key"]: seguir}
    topo = p.get("topChoiceInfo")
    if topo:
        extra[topo["isTopChoiceMarked"]["value"]["key"]] = preferencial
        extra[topo["topChoiceMessage"]["value"]["key"]] = mensagem
    tudo = dict(valores, **extra)
    return corpo_servidor(sr, [estado(c, tudo[c]) for c in chaves])


def valor_estado(corpo, chave):
    return next(s["value"] for s in corpo["states"] if s["key"] == chave)


def sr_escolher_arquivo(job_id):
    """handlePickedFile não vem pronto no RSC; a forma é a do cliente web (captura 24/10)."""
    ligacao = lambda chave: {"key": chave, "namespace": "MemoryNamespace"}
    return {"requestId": REQ + "handlePickedFile",
            "requestedArguments": {
                "$type": "proto.sdui.actions.requests.RequestedArguments",
                "requestedStateKeys": [{"key": {"value": {"$case": "id", "id": k}}}
                                       for k in ("resume-picked-media", "easyApply.resumeSelectedKeyId")],
                "payload": {"mediaList": ligacao("resume-picked-media"),
                            "mediaListBinding": ligacao("resume-picked-media"),
                            "progressBinding": ligacao("resume-upload-progress"),
                            "isUploadingBinding": ligacao("resume-upload-state"),
                            "documentUploadKind": "resume",
                            "resumeSelectedKeyId": ligacao("easyApply.resumeSelectedKeyId"),
                            "fullWidth": False, "jobId": job_id},
                "requestMetadata": {"$type": "proto.sdui.common.RequestMetadata"}},
            "isApfcEnabled": False, "isStreaming": False, "rumPageKey": ""}


def midia_pdf(nome, tamanho, ponteiro):
    local = {"fileName": nome, "mimeType": "application/pdf", "filePointer": ponteiro,
             "size": str(tamanho), "shouldIncludeFileContents": False}
    return {"$type": "proto.sdui.media.MediaList", "mediaFiles": [{
        "mediaAttributions": [], "analysisData": {}, "fileName": nome,
        "source": {"$case": "localFile", "localFile": local}, "size": str(tamanho),
        "mimeType": "application/pdf", "filePointer": ponteiro, "mediaFileId": ponteiro,
        "captions": [], "thumbnails": []}]}


def corpo_navegacao(job_id, empresa, tracking):
    """Abre o formulário com o mesmo payload do Navigate da página da vaga."""
    return {"clientArguments": {
        "$type": "proto.sdui.actions.requests.RequestedArguments", "requestedStateKeys": [],
        "payload": {"jobId": job_id, "companyName": empresa, "trackingId": tracking,
                    "applicantTrackingSystemName": "LinkedIn"},
        "requestMetadata": {"$type": "proto.sdui.common.RequestMetadata"},
        "states": [], "screenId": TELA_EA, "knownTemplateIds": []}, "isModal": True}


def url_ambry(resposta):
    """A URL vem numa linha T do RSC: comprimento em bytes (hex), vírgula, texto."""
    m = re.search(r"(?m)^[0-9a-f]+:T([0-9a-f]+),", resposta)
    if not m:
        raise RuntimeError("resposta sem URL de upload do Ambry")
    bruto, inicio = resposta.encode(), len(resposta[:m.end()].encode())
    return bruto[inicio:inicio + int(m.group(1), 16)].decode()


def id_do_ambry(envio):
    """O POST no Ambry responde 201 sem corpo; o id do arquivo vem no header `location`."""
    # A ponte devolve headers como dict; a fixture capturada guarda o texto bruto.
    headers = envio.get("headers", {})
    texto = f"location: {headers['location']}\r\n" if "location" in headers else headers.get("raw", "")
    achado = re.search(r"(?im)^location:\s*(/AA[A-Za-z0-9_-]{4,}\.pdf)", texto)
    if not achado:
        raise RuntimeError("upload do currículo sem id de volta")
    return achado.group(1)


def enviado(resposta, job_id):
    aplicada = ('jdpApplyState_' + job_id
                + '"}}},"value":{"$case":"stringValue","stringValue":"Applied"')
    return '"errors":[]' in resposta and aplicada in resposta


SESSAO = ("sessão do LinkedIn expirada: abra `playwright-cli -s=linkedin open https://www.linkedin.com/feed/"
          " --headed --persistent` e faça login")
# Pausa entre chamadas para não parecer rajada; os testes zeram.
PAUSA = (2, 4)
# Captura 24/10: o servidor só exige content-type além do csrf-token que a ponte já põe.
CABECALHOS_SDUI = {"content-type": "application/json"}
CABECALHOS_AMBRY = {"Content-Type": "application/pdf"}

# O csrf-token é o JSESSIONID: lido aqui dentro da aba e nunca devolvido ao Python.
PONTE_JS = r"""
(async (A) => {
  const m = document.cookie.match(/JSESSIONID="?([^";]+)/);
  if (!m) return JSON.stringify({ sessao: false });
  let body = A.body;
  if (A.b64) {
    const bin = atob(A.b64);
    body = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) body[i] = bin.charCodeAt(i);
  }
  const s = await fetch(A.url, { method: A.method, headers: { "csrf-token": m[1], ...A.headers },
                                 body, redirect: "manual", credentials: "include" });
  const fora = s.type === "opaqueredirect" || /\/(login|authwall|checkpoint)/.test(s.url)
    || s.status === 401 || s.status === 403;
  return JSON.stringify({ sessao: !fora, status: s.status, url: s.url,
                          headers: Object.fromEntries(s.headers), text: fora ? "" : await s.text() });
})
"""


class SessaoExpirada(Exception):
    pass


def navegador(*args):
    try:
        r = subprocess.run(["playwright-cli", "-s=linkedin", "--json", *args],
                           capture_output=True, encoding="utf-8", timeout=180)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise RuntimeError(f"playwright-cli {args[0]} falhou: {type(e).__name__}") from e
    try:
        dados = json.loads(r.stdout)
    except ValueError:
        raise RuntimeError(f"playwright-cli {args[0]} saiu com {r.returncode}: {r.stderr.strip()[-500:]}") from None
    if dados.get("isError"):
        if "is not open" in dados.get("error", ""):
            raise SessaoExpirada(SESSAO)
        raise RuntimeError(f"playwright-cli {args[0]}: {dados.get('error')}"[:500])
    return dados["result"]


def chamar(metodo, url, corpo=None, cabecalhos=None, b64=None):
    args = {"method": metodo, "url": url, "body": corpo, "headers": cabecalhos or {}, "b64": b64}
    try:
        # ponytail: args vão no argv (teto ~1 MB no macOS); PDF maior que ~700 KB pede outro canal.
        expressao = f"({PONTE_JS})({json.dumps(args)})"
        # O CLI serializa o retorno da ponte, que já é JSON: duas camadas.
        r = json.loads(json.loads(navegador("eval", expressao)))
    finally:
        time.sleep(random.uniform(*PAUSA))
    if not r["sessao"]:
        raise SessaoExpirada(SESSAO)
    return r


def checar_sessao():
    if chamar("GET", f"{BASE}/voyager/api/me", cabecalhos={"accept": "application/json"})["status"] != 200:
        raise SessaoExpirada(SESSAO)


def _texto_200(r, nome):
    # Qualquer outro status traz HTML de erro que o parser leria como "vaga sem Easy Apply".
    if r["status"] != 200:
        raise RuntimeError(f"{nome} respondeu {r['status']}")
    return r["text"]


def buscar_pagina(termo, janela, inicio):
    return _texto_200(chamar("GET", url_busca(termo, janela, inicio)), "busca")


def pagina_da_vaga(job_id):
    return _texto_200(chamar("GET", f"{BASE}/jobs/view/{job_id}/"), "vaga")


def post_servidor(nome, corpo):
    url = f"{BASE}/flagship-web/rsc-action/actions/server-request?sduiid={REQ}{nome}"
    return _texto_200(chamar("POST", url, json.dumps(corpo), CABECALHOS_SDUI), nome)


def abrir_formulario(job_id, empresa, tracking):
    return _texto_200(chamar("POST", URL_NAVEGACAO, json.dumps(corpo_navegacao(job_id, empresa, tracking)),
                             CABECALHOS_SDUI), "formulário")


def _exigir(sr, nome):
    if not sr:
        raise RuntimeError(f"resposta sem o pedido {nome}")
    return sr


def enviar_cv(job_id, chave_cv, caminho, ponteiro=None):
    """Sobe o PDF pelo mesmo caminho do cliente web e devolve o id do Ambry."""
    with open(caminho, "rb") as f:
        dados = f.read()
    ponteiro = ponteiro or "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    midia = midia_pdf(os.path.basename(caminho), len(dados), ponteiro)
    escolha = post_servidor("handlePickedFile", corpo_servidor(sr_escolher_arquivo(job_id), [
        estado("resume-picked-media", midia), estado("easyApply.resumeSelectedKeyId", chave_cv)]))
    resposta = post_servidor("getAmbryUploadUrl", corpo_servidor(
        _exigir(pedido(escolha, "getAmbryUploadUrl"), "getAmbryUploadUrl"), []))
    envio = chamar("POST", url_ambry(resposta), cabecalhos=CABECALHOS_AMBRY,
                   b64=base64.b64encode(dados).decode())
    if envio["status"] >= 300:
        raise RuntimeError(f"upload do currículo respondeu {envio['status']}")
    asset = id_do_ambry(envio)
    post_servidor("setResumeFormBinding", corpo_servidor(
        _exigir(pedido(resposta, "setResumeFormBinding"), "setResumeFormBinding"), [
            estado("resume-uploaded-asset-ids", [asset]),
            estado("easyApply.resumeSelectedKeyId", chave_cv),
            estado("resume-picked-media", midia)]))
    return asset
