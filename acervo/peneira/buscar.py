#!/usr/bin/env python3
"""Caça vagas em APIs públicas e mantém o ledger de candidaturas."""

import argparse
import glob
import json
import os
import random
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import linkedin

RAIZ = os.path.dirname(os.path.abspath(__file__))
# Soma-se à pausa de linkedin.chamar para a rajada de buscas não parecer robô.
PAUSA_BUSCA = 1.5
BANCO = os.path.expanduser("~/.local/share/peneira/vagas.db")
DOSSIES = os.path.expanduser("~/Documents/peneira")
RESPOSTAS = os.path.join(RAIZ, "respostas.json")
GUPY = "https://employability-portal.gupy.io/api/v1/jobs"

# Quatro portais de vaga remota com a mesma forma: lista de itens com título,
# empresa, link, data e restrição geográfica. A tabela evita quatro coletores
# quase idênticos.
REMOTAS = {
    "remotive": dict(
        urls=["https://remotive.com/api/remote-jobs"], lista="jobs",
        id="id", titulo="title", empresa="company_name", link="url",
        data="publication_date", local="candidate_required_location",
        texto="description"),
    "himalayas": dict(
        # limit é capado em 20 pela API; o volume vem do offset.
        urls=[f"https://himalayas.app/jobs/api?limit=20&offset={o}"
              for o in range(0, 600, 20)], lista="jobs",
        id="guid", titulo="title", empresa="companyName", link="applicationLink",
        data="pubDate", local="locationRestrictions", texto="description"),
    "remoteok": dict(
        urls=["https://remoteok.com/api"], lista=None,
        id="id", titulo="position", empresa="company", link="url",
        data="date", local="location", texto="description"),
    "jobicy": dict(
        urls=[f"https://jobicy.com/api/v2/remote-jobs?count=50&tag={t}"
              for t in ("python", "react", "node", "javascript", "data", "engineer")],
        lista="jobs",
        id="id", titulo="jobTitle", empresa="companyName", link="url",
        data="pubDate", local="jobGeo", texto="jobDescription"),
}

ESTADOS = ("nova", "cortada", "aplicada", "resposta", "entrevista", "rejeitada", "silencio")
MODELO_GUPY = {"remote": "remoto", "hybrid": "hibrido", "on-site": "presencial"}
MODELO_LABEL = {"remoto": "remoto", "híbrido": "hibrido", "hibrido": "hibrido",
                "presencial": "presencial"}
NIVEIS = ("júnior", "junior", "pleno", "sênior", "senior")
CONTRATOS = ("clt", "pj", "cooperado")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS vagas (
  chave         TEXT PRIMARY KEY,
  fonte         TEXT NOT NULL,
  origem        TEXT,
  titulo        TEXT NOT NULL,
  url           TEXT,
  publicada     TEXT,
  modelo        TEXT,
  contrato      TEXT,
  nivel         TEXT,
  local         TEXT,
  texto         TEXT,
  vista_em      TEXT NOT NULL,
  aplicada_em   TEXT,
  respondida_em TEXT,
  estado        TEXT NOT NULL DEFAULT 'nova'
)
"""


def hoje():
    return datetime.now(timezone.utc).date().isoformat()


def limite(dias):
    return (datetime.now(timezone.utc).date() - timedelta(days=dias)).isoformat()


def perfil():
    with open(os.path.join(RAIZ, "perfil.json"), encoding="utf-8") as f:
        return json.load(f)


def abrir():
    os.makedirs(os.path.dirname(BANCO), exist_ok=True)
    con = sqlite3.connect(BANCO)
    con.row_factory = sqlite3.Row
    con.execute(ESQUEMA)
    return con


def pegar(url):
    req = urllib.request.Request(
        url, headers={"accept": "application/json", "user-agent": "peneira"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def limpar(html):
    texto = re.sub(r"<[^>]+>", " ", html)
    texto = texto.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
    return re.sub(r"\s+", " ", texto).strip()


def respostas():
    with open(RESPOSTAS, encoding="utf-8") as f:
        return json.load(f)


def apelido(v):
    pedacos = [v["publicada"] or "sem-data", v["origem"] or v["fonte"], v["titulo"]]
    bruto = "-".join(pedacos).lower()
    bruto = (bruto.replace("ç", "c").replace("ã", "a").replace("á", "a")
             .replace("é", "e").replace("ê", "e").replace("í", "i")
             .replace("ó", "o").replace("õ", "o").replace("ú", "u"))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", bruto)).strip("-")[:80]


def nivel_de(v):
    rotulado = (v["nivel"] or "").lower()
    for chave, nomes in (("senior", ("sênior", "senior", " sr", "specialist", "especialista")),
                         ("pleno", ("pleno", " pl", "mid")),
                         ("junior", ("júnior", "junior", " jr", "trainee"))):
        if any(n.strip() in rotulado for n in nomes if n.strip()):
            return chave
        if any(n in v["titulo"].lower() for n in nomes):
            return chave
    return "pleno"


def brl(valor):
    return "R$ " + f"{valor:,.0f}".replace(",", ".")


def pretensao(v, cfg):
    """Devolve (valor, origem do número). Faixa declarada na vaga vence a estimativa."""
    nivel = nivel_de(v)
    pj = (v["contrato"] or "").lower() == "pj"
    # ponytail: entre vários "R$" no texto, o maior costuma ser o salário —
    # vale-refeição e auxílio são menores. Se errar, o dossiê mostra o número.
    achados = [float(m.replace(".", "").replace(",", "."))
               for m in re.findall(r"R\$\s?([\d.]{4,}(?:,\d{2})?)", v["texto"] or "")]
    achados = [a for a in achados if a >= 1500]
    tabela = cfg["faixas_clt_mensal"].get(nivel, cfg["faixas_clt_mensal"]["pleno"])
    if pj:
        tabela *= cfg["multiplicador_pj"]
    # Valor declarado muito abaixo da faixa quase sempre é benefício capturado
    # por engano (vale, auxílio), não salário — a tabela vale mais que isso.
    if achados and max(achados) >= tabela * 0.6:
        base, origem = max(achados), "faixa declarada na vaga"
    else:
        base = tabela
        origem = f"estimativa de mercado para {nivel}" + (" em PJ" if pj else " em CLT")
        if achados:
            origem += f" (a vaga cita {brl(max(achados))}, abaixo da faixa)"
    pedido = base * (1 - cfg["desconto_pretensao"])
    desconto = int(cfg["desconto_pretensao"] * 100)
    return pedido, f"{origem}, {brl(base)} menos {desconto}%"


def extrair_contato(texto):
    achado = re.search(r"[\w.+-]+@[\w-]+\.[\w.]{2,}", texto or "")
    formulario = re.search(
        r"https?://[^\s)>\]]*(?:gupy|greenhouse|lever|workable|abler|solides|recrutei"
        r"|forms\.gle|forms\.office|forms\.cloud\.microsoft|docs\.google\.com/forms"
        r"|typeform|tally\.so|jotform)[^\s)>\]]*", texto or "", re.I)
    if not formulario:
        # Domínio de formulário muda toda semana; o que não muda é o link vir
        # logo depois de "como se candidatar".
        formulario = re.search(
            r"candidat\w*.{0,200}?(https?://[^\s)>\]]+)", texto or "", re.I | re.S)
        return (achado.group(0) if achado else "",
                formulario.group(1) if formulario else "")
    return (achado.group(0) if achado else "", formulario.group(0))


def _casar(rotulos, mapa):
    for r in rotulos:
        if r in mapa:
            return mapa[r] if isinstance(mapa, dict) else r
    return ""


def do_github(repos, paginas=3):
    for repo in repos:
        issues = []
        for pagina in range(1, paginas + 1):
            url = (f"https://api.github.com/repos/{repo}/issues"
                   f"?state=open&per_page=100&page={pagina}"
                   "&sort=created&direction=desc")
            try:
                lote = pegar(url)
            except urllib.error.HTTPError as e:
                extra = (" — limite de 60 req/h da API sem token; "
                         "reduza paginas_github ou espere a hora virar"
                         if e.code == 403 else "")
                print(f"aviso: {repo} respondeu {e.code}{extra}", file=sys.stderr)
                break
            if not lote:
                break
            issues += lote
        for i in issues:
            if "pull_request" in i:
                continue
            rotulos = [r["name"].lower() for r in i.get("labels", [])]
            yield {
                "chave": f"github:{repo}#{i['number']}",
                "fonte": "github",
                "origem": repo,
                "titulo": i["title"],
                "url": i["html_url"],
                "publicada": (i.get("created_at") or "")[:10],
                "modelo": _casar(rotulos, MODELO_LABEL),
                "contrato": _casar(rotulos, CONTRATOS),
                "nivel": _casar(rotulos, NIVEIS),
                "local": ", ".join(re.findall(r"\[([^\]]{2,40})\]", i["title"])),
                "texto": limpar(i.get("body") or ""),
            }


def do_gupy(buscas, paginas=5, limite=100):
    for termo in buscas:
        achados = []
        for pagina in range(paginas):
            consulta = {"jobName": termo, "offset": pagina * limite, "limit": limite}
            try:
                dados = pegar(f"{GUPY}?{urllib.parse.urlencode(consulta)}")
            except urllib.error.HTTPError as e:
                print(f"aviso: gupy '{termo}' respondeu {e.code}", file=sys.stderr)
                break
            lote = dados.get("data", [])
            achados += lote
            if len(lote) < limite:
                break
        for j in achados:
            onde = ", ".join(x for x in (j.get("city"), j.get("state")) if x)
            yield {
                "chave": f"gupy:{j['id']}",
                "fonte": "gupy",
                "origem": j.get("careerPageName") or "",
                "titulo": j["name"],
                "url": j.get("jobUrl") or "",
                "publicada": (j.get("publishedDate") or "")[:10],
                "modelo": MODELO_GUPY.get(j.get("workplaceType"), ""),
                "contrato": "clt" if j.get("type") == "vacancy_type_effective" else "",
                "nivel": "",
                "local": onde or j.get("country") or "",
                "texto": limpar(j.get("description") or ""),
            }


def _data_iso(bruto):
    if isinstance(bruto, (int, float)):
        return datetime.fromtimestamp(bruto, timezone.utc).date().isoformat()
    return str(bruto or "")[:10]


def _texto_local(bruto):
    if isinstance(bruto, list):
        return ", ".join(str(x) for x in bruto)
    return str(bruto or "")


def do_remotas(regioes):
    for fonte, c in REMOTAS.items():
        itens = []
        for url in c["urls"]:
            try:
                dados = pegar(url)
            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                print(f"aviso: {fonte} falhou ({e})", file=sys.stderr)
                continue
            itens += dados[c["lista"]] if c["lista"] else [
                x for x in dados if isinstance(x, dict) and x.get(c["titulo"])]
        for j in itens:
            onde = _texto_local(j.get(c["local"]))
            # Sem restrição declarada, a vaga remota vale; com restrição, ela
            # precisa citar uma região onde o candidato pode trabalhar.
            if onde and not any(r in onde.lower() for r in regioes):
                continue
            yield {
                "chave": f"{fonte}:{j.get(c['id'])}",
                "fonte": fonte,
                "origem": str(j.get(c["empresa"]) or "").strip(),
                "titulo": str(j.get(c["titulo"]) or "").strip(),
                "url": str(j.get(c["link"]) or ""),
                "publicada": _data_iso(j.get(c["data"])),
                "modelo": "remoto",
                "contrato": "",
                "nivel": "",
                "local": onde or "Remoto",
                "texto": limpar(j.get(c["texto"]) or ""),
            }


def avaliar(v, p):
    """Devolve o motivo da recusa, ou None quando a vaga passa."""
    titulo = v["titulo"].lower()
    # Exclusão olha só o título: "time de vendas" no corpo de uma vaga técnica
    # vetava a vaga inteira quando isso varria a descrição.
    for termo in p["excluir"]:
        if termo in titulo:
            return f"excluída por '{termo.strip()}'"
    if not any(c in titulo for c in p["cargos"]):
        return "cargo fora do alvo"
    # Tecnologia no título é a stack central da vaga, não um "desejável". O
    # lookaround (e não \b) é o que faz ".net" casar e "java" não pegar
    # "javascript": \b não vale antes de um ponto.
    for tec in p.get("stack_excluir", ()):
        if re.search(rf"(?<![a-z0-9]){tec}(?![a-z0-9])", titulo):
            return f"stack central fora do perfil ({tec.replace(chr(92) + chr(46), chr(46))})"
    corte = p.get("dias_max")
    if corte and v["publicada"] and v["publicada"] < limite(corte):
        return f"publicada em {v['publicada']}"
    if v["modelo"] and v["modelo"] not in p["modelos"]:
        return f"modelo {v['modelo']}"
    if v["modelo"] == "presencial":
        onde = f"{v['local']} {v['texto']}".lower()
        if not any(c in onde for c in p["cidades"]):
            return "presencial fora das cidades"
    return None


def nota(v, p):
    """Quantas tecnologias do candidato a vaga cita. Título pesa o dobro."""
    titulo, texto = v["titulo"].lower(), (v["texto"] or "").lower()
    casadas = {t for t in p["stack"] if t in texto}
    destaque = {t for t in p["stack"] if t in titulo}
    pontos = len(casadas) + len(destaque)
    # Vaga fora da faixa de senioridade perde metade, não é vetada: sênior que
    # casa muito ainda vale a tentativa, só não pode liderar a fila.
    if nivel_de(v) in p.get("niveis_aceitos", ()):
        pontos += p.get("bonus_nivel", 0)
    else:
        pontos //= 2
    if v["publicada"] and v["publicada"] >= limite(p.get("dias_recentes", 7)):
        pontos += p.get("bonus_recente", 0)
    return pontos


def do_linkedin(p, con):
    """Só Easy Apply; tenta 24 h e cai para 7 dias quando o dia não trouxe vaga que o perfil aceite."""
    linkedin.checar_sessao()
    # Compartilhado entre as janelas: a janela de 7 dias contém a de 24 h e não reabre a vaga.
    visitadas, achadas = set(), []
    for janela in ("r86400", "r604800"):
        for termo in sorted(set(p["cargos"])):
            time.sleep(PAUSA_BUSCA)
            for pagina in range(p.get("paginas_linkedin", 2)):
                try:
                    resultado = linkedin.buscar_pagina(termo, janela, pagina * linkedin.POR_PAGINA)
                except RuntimeError as erro:
                    print(f"aviso: busca '{termo}' no linkedin falhou ({erro})", file=sys.stderr)
                    break
                lote = linkedin.vagas_da_busca(resultado)
                if not lote:
                    break
                for job_id, titulo in lote:
                    if job_id in visitadas:
                        continue
                    visitadas.add(job_id)
                    chave = f"linkedin:{job_id}"
                    # Filtro pelo título antes de abrir a vaga: cada visita é uma
                    # chamada a mais na conta do usuário.
                    previa = {"titulo": titulo, "publicada": "", "modelo": "", "local": "", "texto": ""}
                    if avaliar(previa, p) or con.execute(
                            "SELECT 1 FROM vagas WHERE chave = ?", (chave,)).fetchone():
                        continue
                    try:
                        d = linkedin.detalhe_da_vaga(linkedin.pagina_da_vaga(job_id))
                    except RuntimeError as erro:
                        print(f"aviso: {chave} no linkedin falhou ({erro})", file=sys.stderr)
                        continue
                    if d:
                        achadas.append({"chave": chave, "fonte": "linkedin", "origem": d["empresa"],
                                        "titulo": titulo, "url": f"{linkedin.BASE}/jobs/view/{job_id}/",
                                        "publicada": hoje(), "modelo": d["modelo"], "contrato": "",
                                        "nivel": "", "local": d["local"], "texto": d["texto"]})
        # As recusadas seguem na lista para o guardar contá-las; só as aceitas encerram a busca.
        if any(avaliar(v, p) is None for v in achadas):
            break
    return achadas


def coletar(p):
    return (list(do_github(p["repos"], p.get("paginas_github", 3)))
            + list(do_gupy(p["buscas_gupy"], p.get("paginas_gupy", 5)))
            + list(do_remotas(p["regioes_aceitas"])))


def guardar(con, vagas, p):
    novas, repetidas, recusadas = [], 0, 0
    for v in vagas:
        if avaliar(v, p):
            recusadas += 1
            continue
        ja_vista = con.execute(
            "SELECT 1 FROM vagas WHERE chave = ?", (v["chave"],)).fetchone()
        # UPSERT só nos campos derivados da fonte: estado, vista_em e as datas de
        # candidatura são do usuário e um ajuste de coletor não pode reescrevê-los.
        con.execute(
            "INSERT INTO vagas (chave,fonte,origem,titulo,url,publicada,"
            "modelo,contrato,nivel,local,texto,vista_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(chave) DO UPDATE SET origem=excluded.origem, "
            "titulo=excluded.titulo, url=excluded.url, publicada=excluded.publicada, "
            "modelo=excluded.modelo, contrato=excluded.contrato, nivel=excluded.nivel, "
            "local=excluded.local, texto=excluded.texto",
            (v["chave"], v["fonte"], v["origem"], v["titulo"], v["url"], v["publicada"],
             v["modelo"], v["contrato"], v["nivel"], v["local"], v["texto"], hoje()))
        if ja_vista:
            repetidas += 1
        else:
            novas.append(v)
    con.commit()
    return novas, repetidas, recusadas


def mostrar(v, pontos=None):
    marcas = " · ".join(x for x in (v["modelo"], v["contrato"], v["nivel"], v["publicada"]) if x)
    selo = f"  (casa {pontos} techs)" if pontos is not None else ""
    print(f"[{v['fonte']}] {v['titulo']}{selo}")
    if v["origem"]:
        print(f"         {v['origem']}")
    print(f"         {marcas}")
    print(f"         {v['chave']}")
    print(f"         {v['url']}\n")


def cmd_cacar(args):
    p = perfil()
    con = abrir()
    vagas = do_linkedin(p, con) if args.fonte == "linkedin" else coletar(p)
    novas, repetidas, recusadas = guardar(con, vagas, p)
    for v in sorted(novas, key=lambda v: v["publicada"], reverse=True):
        mostrar(v)
    print(f"{len(novas)} novas · {repetidas} já vistas · {recusadas} recusadas pelo perfil")
    return 0


def melhores(con, p, quantas, fonte=None):
    sql, args = "SELECT * FROM vagas WHERE estado = 'nova'", ()
    if fonte:
        sql, args = sql + " AND fonte = ?", (fonte,)
    abertas = con.execute(sql, args).fetchall()
    ordenadas = sorted(abertas, key=lambda v: (nota(v, p), v["publicada"]), reverse=True)
    # A mesma vaga entra várias vezes quando a empresa abre um id por
    # localidade. Sem isso o lote gasta currículos iguais na mesma vaga.
    vistas, fila = set(), []
    for v in ordenadas:
        assinatura = (v["titulo"].strip().lower(), (v["origem"] or "").strip().lower())
        if assinatura in vistas:
            continue
        vistas.add(assinatura)
        fila.append(v)
        if len(fila) == quantas:
            break
    return fila


def cmd_listar(args):
    p = perfil()
    con = abrir()
    linhas = melhores(con, p, args.quantas)
    for v in linhas:
        mostrar(v, nota(v, p))
    abertas = con.execute(
        "SELECT COUNT(*) FROM vagas WHERE estado = 'nova'").fetchone()[0]
    print(f"{len(linhas)} de {abertas} vagas abertas, as que mais casam com a stack")
    return 0


def cmd_ver(args):
    con = abrir()
    v = con.execute("SELECT * FROM vagas WHERE chave = ?", (args.chave,)).fetchone()
    if not v:
        print(f"chave desconhecida: {args.chave}", file=sys.stderr)
        return 1
    print(f"# {v['titulo']}\n{v['origem']} · {v['local']} · {v['url']}\n")
    print(v["texto"])
    return 0


def cmd_preparar(args):
    con = abrir()
    v = con.execute("SELECT * FROM vagas WHERE chave = ?", (args.chave,)).fetchone()
    if not v:
        print(f"chave desconhecida: {args.chave}", file=sys.stderr)
        return 1
    r = respostas()
    email, formulario = extrair_contato(v["texto"])
    pedido, origem = pretensao(v, r)
    pasta = os.path.join(DOSSIES, apelido(v))
    os.makedirs(pasta, exist_ok=True)

    marcas = " · ".join(x for x in (v["modelo"], v["contrato"], v["nivel"]) if x)
    dossie = (f"# {v['titulo']}\n\n"
              f"- Empresa: {v['origem'] or '(não informada)'}\n"
              f"- Fonte: {v['fonte']} — `{v['chave']}`\n"
              f"- Local: {v['local']}\n"
              f"- Marcas: {marcas or '(não declaradas)'}\n"
              f"- Publicada: {v['publicada']}\n"
              f"- Candidatura: {v['url']}\n"
              f"- E-mail de contato: {email or '(não achado)'}\n"
              f"- Formulário: {formulario or '(não achado)'}\n"
              f"- Pretensão a informar: {brl(pedido)} — {origem}\n"
              f"- Telefone: {r['telefone']}\n\n"
              f"## Descrição\n\n{v['texto']}\n")
    with open(os.path.join(pasta, "vaga.md"), "w", encoding="utf-8") as f:
        f.write(dossie)

    if email:
        # ponytail: rascunho genérico de propósito. Quem personaliza com a
        # experiência que casa com a vaga é a skill, lendo candidato.md.
        corpo = (f"Para: {email}\n"
                 f"Assunto: Candidatura — {v['titulo']}\n\n"
                 f"Olá,\n\n"
                 f"Vi a vaga de {v['titulo']} e gostaria de me candidatar. "
                 f"Sou {r['nome']}, {r['titulo_profissional']}, "
                 f"com experiência em {r['stack_curta']}.\n\n"
                 f"Segue em anexo o currículo adaptado à vaga.\n\n"
                 f"{r['nome']}\n{r['email']}\n{r['linkedin']}\n")
        with open(os.path.join(pasta, "email.txt"), "w", encoding="utf-8") as f:
            f.write(corpo)

    print(f"dossiê: {pasta}/vaga.md")
    print(f"pretensão: {brl(pedido)} ({origem})")
    if email:
        print(f"e-mail: {pasta}/email.txt  (para {email})")
    if formulario:
        print(f"formulário: {formulario}")
    if not email and not formulario:
        print(f"sem canal direto — aplicar em {v['url']}")
    faltando = [k for k, x in r.items() if not k.startswith("_") and x == ""]
    if faltando:
        print(f"campos ainda vazios em respostas.json: {', '.join(faltando)}")
    return 0


def cmd_lote(args):
    p = perfil()
    con = abrir()
    escolhidas = melhores(con, p, args.quantas)
    if not escolhidas:
        print("nenhuma vaga aberta — rode `cacar` primeiro")
        return 0
    for v in escolhidas:
        print(f"\n### {v['titulo']}  (casa {nota(v, p)} techs)")
        cmd_preparar(argparse.Namespace(chave=v["chave"]))
    print(f"\n{len(escolhidas)} dossiês prontos. Falta o currículo de cada um: "
          f"gere com a skill curriculo-camaleao, um por pasta.")
    return 0


def dossie_linkedin(v):
    # Um arquivo por id: a mesma vaga publicada com vários ids tem o mesmo apelido,
    # e o currículo e a nota de um não valem para o outro.
    return os.path.join(DOSSIES, apelido(v), f"linkedin-{v['chave'].split(':', 1)[1]}.json")


def ler_dossie(v):
    try:
        with open(dossie_linkedin(v), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def gravar_dossie(v, dados):
    os.makedirs(os.path.dirname(dossie_linkedin(v)), exist_ok=True)
    with open(dossie_linkedin(v), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def preferenciais_no_mes():
    mes, total = hoje()[:7], 0
    for caminho in glob.glob(os.path.join(DOSSIES, "*", "linkedin-*.json")):
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
        total += bool(d.get("preferencial")) and (d.get("enviada_em") or "").startswith(mes)
    return total


def cortar(e, motivo):
    """Vaga sem saída: sai da fila, e o motivo no dossiê impede o `revisar` de reabri-la."""
    gravar_dossie(e["v"], dict(e["d"], motivo=motivo))
    cmd_marcar(argparse.Namespace(chave=e["v"]["chave"], estado="cortada"))
    return dict(e, situacao=f"cortada: {motivo}")


def liberar_corte(v):
    """Vaga reaberta à mão: o motivo velho não pode segurá-la fechada num `revisar` futuro."""
    d = ler_dossie(v) if v["fonte"] == "linkedin" else {}
    if "motivo" in d:
        gravar_dossie(v, {k: x for k, x in d.items() if k != "motivo"})


def preparar_linkedin(v, r):
    """Abre o formulário e decide se a vaga está pronta; nada é enviado aqui."""
    job, d = v["chave"].split(":", 1)[1], ler_dossie(v)
    e = {"v": v, "d": d, "job": job, "sr": None, "qs": [], "valores": {}, "pendencias": []}
    if d.get("ats", 85) < 85:
        return cortar(e, f"ATS {d['ats']} < 85")
    try:
        det = linkedin.detalhe_da_vaga(linkedin.pagina_da_vaga(job))
        if not det:
            return cortar(e, "não é Easy Apply")
        rsc = linkedin.abrir_formulario(job, det["empresa"], det["tracking"])
        e["sr"] = linkedin.pedido(rsc, "submit")
        if not e["sr"]:
            return dict(e, situacao="formulário não reconhecido")
        e["qs"] = linkedin.perguntas(e["sr"], rsc)
        # A pretensão é calculada por vaga; a pergunta escolhe CLT ou PJ pelo rótulo.
        pretensoes = {c: pretensao(dict(v, contrato=c), r)[0] for c in ("clt", "pj")}
        e["valores"], e["pendencias"] = linkedin.resolver(
            e["qs"], dict(r, pretensao=pretensoes), "(currículo)")
    # SessaoExpirada não herda destes: atravessa e o main sai com 2.
    except (RuntimeError, ValueError) as erro:
        return dict(e, situacao=f"erro: {str(erro)[:100]}")
    if any(p.startswith("tipo ") for p in e["pendencias"]):
        return cortar(e, "tipo de campo não mapeado")
    if e["pendencias"]:
        return dict(e, situacao="pendência")
    if not d.get("cv") or not os.path.isfile(d["cv"]):
        return dict(e, situacao="sem currículo")
    return dict(e, situacao="pronta")


def quer_preferencial(e, ja_no_mes=None):
    topo = e["sr"]["requestedArguments"]["payload"].get("topChoiceInfo") or {}
    if ja_no_mes is None:
        ja_no_mes = preferenciais_no_mes()
    return bool(e["d"].get("ats", 0) >= 90 and topo.get("isEligibleToSeeTopChoice")
                and not topo.get("isTopChoiceCreditLimitReached") and ja_no_mes < 2)


def estrelas_do_lote(lote):
    """{chave: ★} das prontas, somando as anteriores para não prometer a 3ª preferencial do mês."""
    ja_no_mes, estrelas = preferenciais_no_mes(), {}
    for e in lote:
        if e["situacao"] == "pronta":
            estrelas[e["v"]["chave"]] = quer_preferencial(e, ja_no_mes)
            ja_no_mes += estrelas[e["v"]["chave"]]
    return estrelas


def imprimir_lote(lote, estrelas):
    print(f"{'vaga':40} {'empresa':20} {'ATS':>4} {'respostas':>9}  pendências / situação")
    for e in lote:
        ats = e["d"].get("ats")
        estrela = " ★" if e["situacao"] == "pronta" and estrelas.get(e["v"]["chave"]) else ""
        print(f"{e['v']['titulo'][:40]:40} {(e['v']['origem'] or '')[:20]:20} "
              f"{ats if ats is not None else '—':>4} {len(e['valores']):>9}  {e['situacao']}{estrela}")
        for pendencia in e["pendencias"]:
            print(f"{'':42}- {pendencia}")


# Pendência e vaga cortada não gastam a cota de --quantas (senão a fila trava nelas),
# mas cada uma custa uma visita na conta do usuário: o teto evita varrer a fila inteira.
MAX_PULADAS = 10


def montar_lote(quantas, r):
    lote, puladas = [], 0
    for v in melhores(abrir(), perfil(), None, fonte="linkedin"):
        e = preparar_linkedin(v, r)
        lote.append(e)
        puladas += e["situacao"] == "pendência" or e["situacao"].startswith("cortada")
        if len(lote) - puladas >= quantas or puladas >= MAX_PULADAS:
            break
    return lote


def enviar_linkedin(e, r, estrela):
    """Sobe o currículo, envia e marca; devolve True só com confirmação do LinkedIn."""
    # A ★ é a que o --seco mostrou: recalcular a daria a uma vaga que o usuário viu sem ela.
    preferencial = estrela and quer_preferencial(e)
    mensagem = e["d"].get("mensagem", "") if preferencial else ""
    # Falha antes do upload: um submit que não sai não pode deixar PDF solto no perfil.
    linkedin.corpo_submit(e["sr"], e["valores"], seguir=False, preferencial=preferencial, mensagem=mensagem)
    if not os.path.isfile(e["d"]["cv"]):
        raise RuntimeError("o PDF do currículo sumiu")
    chave_cv = next((q["chave"] for q in e["qs"] if q["tipo"] in ("LARGER_RESUME", "RESUME")), None)
    cv_id = linkedin.enviar_cv(e["job"], chave_cv, e["d"]["cv"]) if chave_cv else ""
    valores, _ = linkedin.resolver(e["qs"], r, cv_id)
    corpo = linkedin.corpo_submit(e["sr"], valores, seguir=False, preferencial=preferencial,
                                  mensagem=mensagem)
    payload = e["sr"]["requestedArguments"]["payload"]
    if not linkedin.enviado(linkedin.post_servidor("submit", corpo), payload["jobId"]):
        # Cortada, não nova: recusa costuma ser candidatura feita por fora, e reenviar não muda isso.
        print(f"falhou: {e['v']['chave']} — o LinkedIn não confirmou o envio; vaga cortada",
              file=sys.stderr)
        cortar(e, "o LinkedIn não confirmou o envio")
        return False
    cmd_marcar(argparse.Namespace(chave=e["v"]["chave"], estado="aplicada"))
    gravar_dossie(e["v"], dict(e["d"], enviada_em=hoje(), preferencial=preferencial,
                               seguir=linkedin.valor_estado(corpo, payload["followCompany"]["key"])))
    return True


def arquivo_aprovado():
    # Ao lado do ledger, fora do repo: o ok do usuário não vai para o git.
    return os.path.join(os.path.dirname(BANCO), "lote_aprovado.json")


def apagar_aprovacao():
    try:
        os.remove(arquivo_aprovado())
    except FileNotFoundError:
        pass


def ler_aprovacao():
    """{chave: ★} das prontas que o --seco de hoje mostrou; None sem ok válido."""
    try:
        with open(arquivo_aprovado(), encoding="utf-8") as f:
            ok = json.load(f)
    except (FileNotFoundError, ValueError):
        return None
    if not isinstance(ok, dict) or ok.get("data") != hoje() or not isinstance(ok.get("chaves"), dict):
        return None
    return ok["chaves"]


def cmd_aplicar(args):
    aprovadas = None if args.seco else ler_aprovacao()
    if aprovadas is None and not args.seco:
        print("sem lote aprovado hoje: rode `aplicar --seco`, mostre a tabela ao usuário e espere o ok",
              file=sys.stderr)
        return 1
    # O ok vale uma execução: gasto aqui, o --seco grava outro no fim e uma queda no meio não o reaproveita.
    apagar_aprovacao()
    if aprovadas == {}:
        print("o --seco não aprovou nenhuma vaga: nada a enviar")
        return 0
    r = respostas()
    linkedin.checar_sessao()
    lote = montar_lote(args.quantas, r)
    estrelas = estrelas_do_lote(lote) if args.seco else aprovadas
    if args.seco:
        with open(arquivo_aprovado(), "w", encoding="utf-8") as f:
            json.dump({"data": hoje(), "chaves": estrelas}, f)
    if not lote:
        print("nenhuma vaga do LinkedIn na fila — rode `cacar --fonte linkedin`")
        return 0
    imprimir_lote(lote, estrelas)
    if args.seco:
        return 0
    prontas = [e for e in lote if e["situacao"] == "pronta"]
    for e in prontas:
        if e["v"]["chave"] not in aprovadas:
            print(f"fora do lote aprovado: {e['v']['chave']}")
    prontas = [e for e in prontas if e["v"]["chave"] in aprovadas]
    enviadas = 0
    for i, e in enumerate(prontas):
        if i:
            # Rajada de envios é o padrão que o LinkedIn pune; 30 s ± 5 imita gente.
            time.sleep(random.uniform(25, 35))
        try:
            enviadas += enviar_linkedin(e, r, aprovadas[e["v"]["chave"]])
        except RuntimeError as erro:
            print(f"falhou: {e['v']['chave']} — {erro}", file=sys.stderr)
    print(f"{enviadas} de {len(prontas)} candidaturas enviadas")
    return 0


def cmd_responder(args):
    r = respostas()
    # `linkedin` já guarda a URL do perfil: as respostas do formulário têm chave própria.
    r.setdefault("formulario_linkedin", {})[args.pergunta] = args.valor
    with open(RESPOSTAS, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"guardado: {args.pergunta} = {args.valor}")
    return 0


def cmd_curriculo(args):
    v = abrir().execute("SELECT * FROM vagas WHERE chave = ?", (args.chave,)).fetchone()
    if not v:
        print(f"chave desconhecida: {args.chave}", file=sys.stderr)
        return 1
    if not os.path.isfile(args.pdf):
        print(f"PDF não encontrado: {args.pdf}", file=sys.stderr)
        return 1
    if args.mensagem and not 20 <= len(args.mensagem) <= 400:
        print("a mensagem do preferencial precisa de 20 a 400 caracteres", file=sys.stderr)
        return 1
    d = dict(ler_dossie(v), chave=v["chave"], cv=os.path.abspath(args.pdf), ats=args.ats,
             mensagem=args.mensagem or "")
    gravar_dossie(v, d)
    print(f"{v['chave']}: currículo {d['cv']} · ATS {args.ats}")
    return 0


def cmd_revisar(args):
    """Reaplica o perfil às vagas já no ledger. Só mexe em quem nunca foi aplicada."""
    p = perfil()
    con = abrir()
    cortadas = devolvidas = 0
    for v in con.execute("SELECT * FROM vagas WHERE estado IN ('nova', 'cortada')"):
        # Corte do LinkedIn (formulário, ATS, recusa) não depende do perfil: o motivo no dossiê o mantém fechado.
        if v["estado"] == "cortada" and v["fonte"] == "linkedin" and ler_dossie(v).get("motivo"):
            continue
        motivo = avaliar(dict(v), p)
        alvo = "cortada" if motivo else "nova"
        if alvo != v["estado"]:
            con.execute("UPDATE vagas SET estado = ? WHERE chave = ?", (alvo, v["chave"]))
            if alvo == "cortada":
                cortadas += 1
            else:
                devolvidas += 1
    con.commit()
    abertas = con.execute("SELECT COUNT(*) FROM vagas WHERE estado='nova'").fetchone()[0]
    print(f"{cortadas} cortadas pelo perfil novo · {devolvidas} devolvidas à fila "
          f"· {abertas} abertas")
    return 0


def cmd_marcar(args):
    con = abrir()
    if args.estado not in ESTADOS:
        print(f"estado inválido: {args.estado} (use: {', '.join(ESTADOS)})", file=sys.stderr)
        return 1
    campo = {"aplicada": "aplicada_em"}.get(args.estado)
    if args.estado in ("resposta", "entrevista", "rejeitada"):
        campo = "respondida_em"
    sql = "UPDATE vagas SET estado = ?" + (f", {campo} = ?" if campo else "") + " WHERE chave = ?"
    valores = [args.estado] + ([hoje()] if campo else []) + [args.chave]
    if not con.execute(sql, valores).rowcount:
        print(f"chave desconhecida: {args.chave}", file=sys.stderr)
        return 1
    con.commit()
    if args.estado == "nova":
        liberar_corte(con.execute("SELECT * FROM vagas WHERE chave = ?", (args.chave,)).fetchone())
    print(f"{args.chave}: {args.estado}")
    return 0


def cmd_placar(args):
    con = abrir()
    linhas = con.execute("""
        SELECT fonte,
               COUNT(*)                                        AS vistas,
               SUM(aplicada_em IS NOT NULL)                    AS aplicadas,
               SUM(estado IN ('resposta', 'entrevista'))       AS respostas,
               SUM(estado = 'entrevista')                      AS entrevistas
          FROM vagas GROUP BY fonte ORDER BY fonte""").fetchall()
    print(f"{'fonte':10} {'vistas':>7} {'aplicadas':>10} {'respostas':>10} {'entrevistas':>12} {'taxa':>7}")
    for r in linhas:
        taxa = f"{100 * r['respostas'] / r['aplicadas']:.0f}%" if r["aplicadas"] else "—"
        print(f"{r['fonte']:10} {r['vistas']:>7} {r['aplicadas']:>10} "
              f"{r['respostas']:>10} {r['entrevistas']:>12} {taxa:>7}")
    if not linhas:
        print("(ledger vazio — rode `cacar` primeiro)")
    return 0


def inteiro_positivo(texto):
    n = int(texto)
    if n < 1:
        raise argparse.ArgumentTypeError("precisa ser 1 ou mais")
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_cacar = sub.add_parser("cacar", help="coleta as fontes e grava as vagas novas")
    p_cacar.add_argument("--fonte", choices=("publicas", "linkedin"), default="publicas",
                         help="linkedin usa a sessão linkedin do playwright-cli")

    p_list = sub.add_parser("listar", help="vagas aprovadas ainda sem candidatura")
    p_list.add_argument("--quantas", type=int, default=20)

    p_ver = sub.add_parser("ver", help="descrição completa, para alimentar o currículo")
    p_ver.add_argument("chave")

    p_prep = sub.add_parser("preparar", help="monta o dossiê e o rascunho de e-mail")
    p_prep.add_argument("chave")

    sub.add_parser("revisar", help="reaplica o perfil às vagas já guardadas")

    p_lote = sub.add_parser("lote", help="prepara as N vagas que mais casam com a stack")
    p_lote.add_argument("--quantas", type=int, default=5)

    p_mar = sub.add_parser("marcar", help=f"muda o estado ({', '.join(ESTADOS)})")
    p_mar.add_argument("chave")
    p_mar.add_argument("estado")

    sub.add_parser("placar", help="taxa de resposta por fonte")

    p_apl = sub.add_parser("aplicar", help="LinkedIn Easy Apply: prepara o lote e envia")
    p_apl.add_argument("--quantas", type=inteiro_positivo, default=5)
    p_apl.add_argument("--seco", action="store_true", help="só mostra o lote, não envia")

    p_resp = sub.add_parser("responder", help="guarda a resposta de uma pergunta de formulário")
    p_resp.add_argument("pergunta")
    p_resp.add_argument("valor")

    p_cv = sub.add_parser("curriculo", help="liga o PDF do Camaleão e a nota ATS à vaga")
    p_cv.add_argument("chave")
    p_cv.add_argument("--pdf", required=True)
    p_cv.add_argument("--ats", type=int, required=True)
    p_cv.add_argument("--mensagem", default="", help="20 a 400 caracteres, só para ATS >= 90")

    args = ap.parse_args(argv)
    try:
        return {"cacar": cmd_cacar, "listar": cmd_listar, "ver": cmd_ver,
                "preparar": cmd_preparar, "lote": cmd_lote, "revisar": cmd_revisar,
                "marcar": cmd_marcar, "aplicar": cmd_aplicar, "responder": cmd_responder,
                "curriculo": cmd_curriculo,
                "placar": cmd_placar}[args.cmd](args)
    except linkedin.SessaoExpirada as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
