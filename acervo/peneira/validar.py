#!/usr/bin/env python3
"""Pipeline de validação: mede cada afirmação sobre a Peneira e diz passa ou falha.

Rode depois de mexer no perfil, nos coletores ou no cron. Cada verificação
imprime a evidência que a sustenta, para o resultado poder ser conferido em vez
de acreditado.
"""

import collections
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import buscar

DOSSIES = os.path.expanduser("~/Documents/peneira")
CRON_LOG = os.path.expanduser("~/.local/share/peneira/cron.log")

# Cargo que não é de tecnologia e já apareceu na fila por engano.
FORA_DE_AREA = ("departamento pessoal", "recursos humanos", "administrativo",
                "prevenção a fraudes", "product manager", "product owner",
                "comercial", "vendas", "atendimento", "recepção", "financeiro",
                "contábil", "jurídico", "marketing", "designer", "recrutamento")

resultados = []


def checa(nome, condicao, evidencia, pendencia=False):
    """pendencia=True marca o que falta acontecer, não o que quebrou: não
    derruba a pipeline, mas continua visível."""
    ok = bool(condicao)
    selo = "PASSA" if ok else ("PENDENTE" if pendencia else "FALHA")
    resultados.append((nome, ok, pendencia))
    print(f"[{selo:8}] {nome}\n           {evidencia}")
    return ok


def testes_unitarios():
    r = subprocess.run([sys.executable, "test_peneira.py"],
                       cwd=os.path.dirname(os.path.abspath(__file__)),
                       capture_output=True, text=True)
    checa("testes unitários", r.returncode == 0,
          (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else "sem saída")


def fontes_respondem(p):
    vivas, mortas, limitadas = [], [], []
    for fonte, c in buscar.REMOTAS.items():
        try:
            d = buscar.pegar(c["urls"][0])
            n = len(d[c["lista"]]) if c["lista"] else len(d)
            vivas.append(f"{fonte}={n}")
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            mortas.append(f"{fonte} ({e})")
    try:
        g = buscar.pegar(f"{buscar.GUPY}?jobName=desenvolvedor&offset=0&limit=1")
        vivas.append(f"gupy={g['pagination']['total']}")
    except Exception as e:
        mortas.append(f"gupy ({e})")
    try:
        n = len(buscar.pegar(
            f"https://api.github.com/repos/{p['repos'][0]}/issues?per_page=5"))
        vivas.append(f"github={n}")
    except urllib.error.HTTPError as e:
        # 403 aqui é a cota de 60 req/h sem token, que volta sozinha na virada
        # da hora — não é a fonte fora do ar.
        (limitadas if e.code == 403 else mortas).append(f"github ({e})")
    except Exception as e:
        mortas.append(f"github ({e})")
    checa("fontes respondem sem login", not mortas,
          " · ".join(vivas) + (f" | MORTAS: {', '.join(mortas)}" if mortas else "")
          + (f" | cota estourada (volta na virada da hora): {', '.join(limitadas)}"
             if limitadas else ""))


def assertividade(p, con):
    """Mede a fila inteira, não uma amostra."""
    abertas = con.execute("SELECT * FROM vagas WHERE estado='nova'").fetchall()
    fora_area, stack_errada, antigas, nivel_fora = [], [], [], []
    for v in abertas:
        t = v["titulo"].lower()
        cargo = re.split(r"[(|\[]| - | — ", t)[0]
        if any(x in cargo for x in FORA_DE_AREA):
            fora_area.append(v["titulo"])
        if any(re.search(rf"(?<![a-z0-9]){tec}(?![a-z0-9])", t)
               for tec in p.get("stack_excluir", ())):
            stack_errada.append(v["titulo"])
        if v["publicada"] and v["publicada"] < buscar.limite(p["dias_max"]):
            antigas.append(v["publicada"])
        if buscar.nivel_de(v) not in p["niveis_aceitos"]:
            nivel_fora.append(v["titulo"])

    total = len(abertas) or 1
    sujeira = len(fora_area) + len(stack_errada) + len(antigas)
    checa("fila sem cargo fora de área", not fora_area,
          f"{len(fora_area)} de {total}" + (f" — ex.: {fora_area[:2]}" if fora_area else ""))
    checa("fila sem stack excluída no título", not stack_errada,
          f"{len(stack_errada)} de {total}" + (f" — ex.: {stack_errada[:2]}" if stack_errada else ""))
    checa("fila sem vaga vencida", not antigas,
          f"{len(antigas)} de {total} publicadas antes de {buscar.limite(p['dias_max'])}")
    checa("precisão da fila >= 95%", sujeira / total <= 0.05,
          f"{100 * (1 - sujeira / total):.1f}% limpa ({sujeira} problemas em {total})")
    print(f"         (sênior na fila: {len(nivel_fora)} — penalizados no ranking, não vetados)")


def lote_sem_repetir(p, con):
    fila = buscar.melhores(con, p, 20)
    assinaturas = [(v["titulo"].strip().lower(), (v["origem"] or "").lower()) for v in fila]
    repetidas = [x for x, n in collections.Counter(assinaturas).items() if n > 1]
    checa("lote de 20 sem vaga repetida", not repetidas,
          f"{len(fila)} vagas, {len(set(assinaturas))} distintas")
    niveis = collections.Counter(buscar.nivel_de(v) for v in fila)
    na_faixa = sum(niveis[n] for n in p["niveis_aceitos"])
    checa("lote majoritariamente na faixa júnior/pleno", na_faixa >= len(fila) * 0.7,
          f"{na_faixa} de {len(fila)} — {dict(niveis)}")
    recentes = [v for v in fila if v["publicada"] >= buscar.limite(p["dias_recentes"])]
    checa("lote prioriza os últimos 7 dias", len(recentes) >= len(fila) * 0.5,
          f"{len(recentes)} de {len(fila)} publicadas em {p['dias_recentes']} dias")


def dossies_completos(r):
    achados = []
    for raiz, _, arquivos in os.walk(DOSSIES):
        if "vaga.md" in arquivos:
            achados.append(os.path.join(raiz, "vaga.md"))
    sem_campo, pretensao_torta = [], []
    piso = min(r["faixas_clt_mensal"].values()) * (1 - r["desconto_pretensao"]) * 0.5
    for caminho in achados:
        with open(caminho, encoding="utf-8") as f:
            texto = f.read()
        if not all(c in texto for c in ("- Empresa:", "- Candidatura:",
                                        "- Pretensão a informar:", "- Telefone:",
                                        "## Descrição")):
            sem_campo.append(caminho)
        m = re.search(r"Pretensão a informar: R\$ ([\d.]+)", texto)
        if m and float(m.group(1).replace(".", "")) < piso:
            pretensao_torta.append((os.path.basename(os.path.dirname(caminho)), m.group(1)))
    checa("dossiês com todos os campos", not sem_campo,
          f"{len(achados)} dossiês, {len(sem_campo)} incompletos")
    checa("nenhuma pretensão abaixo do piso", not pretensao_torta,
          f"piso R$ {piso:.0f}" + (f" — fora: {pretensao_torta[:2]}" if pretensao_torta else ""))
    return achados


def ledger_ponta_a_ponta():
    """Roda a máquina de estados num banco descartável."""
    original = buscar.BANCO
    try:
        with tempfile.TemporaryDirectory() as tmp:
            buscar.BANCO = os.path.join(tmp, "t.db")
            con = buscar.abrir()
            con.execute("INSERT INTO vagas (chave,fonte,titulo,vista_em,estado) "
                        "VALUES ('x:1','gupy','V','2026-09-06','nova')")
            con.commit()
            import argparse
            buscar.cmd_marcar(argparse.Namespace(chave="x:1", estado="aplicada"))
            buscar.cmd_marcar(argparse.Namespace(chave="x:1", estado="resposta"))
            r = con.execute("SELECT aplicada_em, respondida_em, estado FROM vagas").fetchone()
            ok = bool(r["aplicada_em"]) and bool(r["respondida_em"]) and r["estado"] == "resposta"
            checa("ledger registra aplicação e resposta", ok, dict(r))
    finally:
        buscar.BANCO = original


def linkedin_regras():
    """Lê o que de fato foi enviado: ATS, preferencial e "seguir empresa" de cada envio."""
    envios, corrompidos = [], []
    for caminho in glob.glob(os.path.join(DOSSIES, "*", "linkedin-*.json")):
        try:
            with open(caminho, encoding="utf-8") as f:
                d = json.load(f)
        except (ValueError, OSError):
            corrompidos.append(caminho)
            continue
        if isinstance(d, dict) and d.get("enviada_em"):
            envios.append(d)
    if corrompidos:
        checa("LinkedIn: dossiês legíveis", False,
              f"{len(corrompidos)} ilegíveis — ex.: {corrompidos[:2]}")
    if not envios:
        checa("LinkedIn: regras de envio", False,
              "nenhuma candidatura enviada pelo LinkedIn ainda", pendencia=True)
        return
    seguiu = [d.get("chave") for d in envios if d.get("seguir") is not False]
    baixo = [d.get("chave") for d in envios if (d.get("ats") or 0) < 85]
    pref_torto = [d.get("chave") for d in envios
                  if d.get("preferencial") and (d.get("ats") or 0) < 90]
    por_mes = collections.Counter(d["enviada_em"][:7] for d in envios if d.get("preferencial"))
    checa("LinkedIn: nunca segue a empresa", not seguiu,
          f"{len(envios)} envios" + (f" — seguiu: {seguiu[:2]}" if seguiu else ""))
    checa("LinkedIn: só envia com ATS >= 85", not baixo,
          f"{len(envios)} envios" + (f" — abaixo: {baixo[:2]}" if baixo else ""))
    checa("LinkedIn: preferencial com ATS >= 90 e até 2 por mês",
          not pref_torto and all(n <= 2 for n in por_mes.values()),
          f"por mês: {dict(por_mes) or 'nenhum'}" + (f" — torto: {pref_torto[:2]}" if pref_torto else ""))


def cron_disparou():
    linha = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    instalado = [l for l in linha.splitlines() if "# peneira" in l and "teste" not in l]
    checa("cron instalado para as 8h", len(instalado) == 1,
          instalado[0][:70] if instalado else "NENHUMA linha instalada")

    prova = "/tmp/cron-fire.log"
    if os.path.exists(prova):
        with open(prova, encoding="utf-8") as f:
            saida = f.read()
        checa("cron disparado pelo daemon (teste ao vivo)",
              "dossiê:" in saida,
              f"{prova}: " + (saida.strip().splitlines() or ["vazio"])[-1][:70])
    else:
        checa("cron disparado pelo daemon (teste ao vivo)", False,
              f"{prova} não existe — teste ao vivo ainda não rodou")


def curriculos(dossies):
    com_pdf = [d for d in dossies
               if any(a.endswith(".pdf") for a in os.listdir(os.path.dirname(d)))]
    checa("todo dossiê tem currículo", len(com_pdf) == len(dossies),
          f"{len(com_pdf)} de {len(dossies)} — o lote para no dossiê, o PDF ainda é manual",
          pendencia=True)


def placar_real(con):
    r = con.execute("SELECT SUM(aplicada_em IS NOT NULL) a, "
                    "SUM(estado IN ('resposta','entrevista')) r FROM vagas").fetchone()
    checa("placar com amostra suficiente (>=20 aplicações)", (r["a"] or 0) >= 20,
          f"{r['a'] or 0} aplicadas, {r['r'] or 0} respostas — taxa por canal exige envio real",
          pendencia=True)


def main():
    p, con = buscar.perfil(), buscar.abrir()
    print("=" * 72)
    testes_unitarios()
    fontes_respondem(p)
    assertividade(p, con)
    lote_sem_repetir(p, con)
    dossies = dossies_completos(buscar.respostas())
    ledger_ponta_a_ponta()
    linkedin_regras()
    cron_disparou()
    curriculos(dossies)
    placar_real(con)
    print("=" * 72)
    falhas = [n for n, ok, pend in resultados if not ok and not pend]
    pendentes = [n for n, ok, pend in resultados if not ok and pend]
    passaram = sum(1 for _, ok, _ in resultados if ok)
    print(f"{passaram}/{len(resultados)} passaram · {len(falhas)} falhas · "
          f"{len(pendentes)} pendências")
    for n in falhas:
        print(f"  FALHA:    {n}")
    for n in pendentes:
        print(f"  PENDENTE: {n}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
