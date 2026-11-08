#!/usr/bin/env python3
"""Ledger financeiro pessoal: ingere CSV do Nubank, acumula, resume, simula compra."""

import csv
import hashlib
import re
import statistics
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

ESTADO = Path.home() / ".claude" / "consultor-financeiro"
LEDGER = ESTADO / "ledger.csv"
CATEGORIAS = ESTADO / "categorias.csv"
PERFIL = ESTADO / "perfil.md"

COLUNAS = ["data", "valor", "origem", "competencia", "id", "descricao",
           "categoria", "parcela_n", "parcela_total"]

# Movimento que é o mesmo dinheiro aparecendo duas vezes, ou poupança indo e
# voltando. Somar como gasto ou como renda infla os dois lados do balanço.
CATEGORIAS_PADRAO = [
    ("resgate rdb", "interno"),
    ("aplicacao rdb", "interno"),
    ("aplicação rdb", "interno"),
    ("pagamento de fatura", "interno"),
    ("pagamento recebido", "interno"),
    ("ifood", "delivery"),
    ("uber", "transporte"),
    ("99app", "transporte"),
    ("pague menos", "farmacia"),
    ("drogaria", "farmacia"),
    ("posto", "combustivel"),
    ("netflix", "assinatura"),
    ("spotify", "assinatura"),
]

# Renda entra pelo extrato como transferência igual a qualquer outra. Sem
# separar, pensão vira "volta de terceiros" e abate gasto em vez de somar.
RENDA = ("salario", "pensao")

MIUDO_TETO = Decimal("30.00")
FUGA_PCT = Decimal("30")
FUGA_REAIS = Decimal("100")

RE_PARCELA = re.compile(r"(?:parcela\s+)?(\d{1,2})\s*/\s*(\d{1,2})\b", re.I)
RE_SUFIXO_PARCELA = re.compile(r"\s*-?\s*PARCELA\s+\d{1,2}\s*/\s*\d{1,2}\s*$", re.I)
PREFIXOS_EXTRATO = (
    "TRANSFERÊNCIA", "TRANSFERENCIA", "COMPRA NO DÉBITO", "COMPRA NO DEBITO",
    "PAGAMENTO", "RECEBIMENTO", "ESTORNO", "VALOR ADICIONADO", "DÉBITO EM CONTA",
)
RE_NUMERO = re.compile(r"^\s*[-*]?\s*\*{0,2}([a-z_]+)\*{0,2}\s*:\s*\*{0,2}R?\$?\s*([\d.,]+)")


def norm(texto):
    return re.sub(r"\s+", " ", texto.strip()).upper()


def contraparte(descricao):
    """Quem recebeu ou pagou. O prefixo do Nubank é igual em centenas de linhas."""
    texto = RE_SUFIXO_PARCELA.sub("", norm(descricao)).strip(" -")
    partes = [p for p in texto.split(" - ") if p]
    # Só o extrato usa " - " para separar prefixo de contraparte. Na fatura o
    # traço é do nome da loja, e cortar ali devolve "PARCELA 9/12" como se
    # fosse quem recebeu.
    if len(partes) >= 2 and partes[0].startswith(PREFIXOS_EXTRATO):
        return partes[1]
    return partes[0] if partes else "?"


def para_decimal(bruto):
    s = str(bruto).strip().replace(" ", "").replace("R$", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    return Decimal(s or "0")


def para_iso(bruto):
    s = bruto.strip()
    if "/" in s:
        d, m, a = s.split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    return s


def achar_parcela(titulo):
    for n, total in RE_PARCELA.findall(titulo):
        n, total = int(n), int(total)
        # 12/2026 é data, não parcela; e ninguém parcela em mais de 36x.
        if 1 <= n <= total <= 36:
            return n, total
    return None, None


def mes_de(iso):
    return iso[:7]


def somar_meses(competencia, n):
    ano, mes = int(competencia[:4]), int(competencia[5:7])
    total = (ano * 12 + mes - 1) + n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def detectar_formato(cabecalho):
    campos = {c.strip().lower().lstrip("﻿") for c in cabecalho}
    if "identificador" in campos:
        return "extrato"
    if "amount" in campos or "title" in campos:
        return "fatura"
    raise SystemExit(f"cabeçalho não reconhecido: {cabecalho}")


def coluna(linha, *nomes):
    for chave, valor in linha.items():
        if chave and chave.strip().lower().lstrip("﻿") in nomes:
            return valor or ""
    return ""


def ler_csv(caminho, competencia_forcada=None):
    with open(caminho, newline="", encoding="utf-8-sig") as fh:
        leitor = csv.DictReader(fh)
        origem = detectar_formato(leitor.fieldnames or [])
        vistos = defaultdict(int)
        for linha in leitor:
            if origem == "extrato":
                data = para_iso(coluna(linha, "data"))
                valor = para_decimal(coluna(linha, "valor"))
                descricao = coluna(linha, "descrição", "descricao").strip()
                ident = coluna(linha, "identificador").strip()
                competencia = competencia_forcada or mes_de(data)
            else:
                data = para_iso(coluna(linha, "date", "data"))
                # Na fatura o valor positivo é compra; no ledger saída é sempre
                # negativa, senão soma de fatura e extrato não fecha.
                valor = -para_decimal(coluna(linha, "amount", "valor"))
                descricao = coluna(linha, "title", "titulo", "descrição").strip()
                competencia = competencia_forcada or mes_de(data)
                bruto = f"{competencia}|{data}|{valor}|{norm(descricao)}"
                ident = "fatura:" + hashlib.sha1(bruto.encode()).hexdigest()[:12]
            if not data or not descricao:
                continue
            vistos[ident] += 1
            # Dois cafés iguais no mesmo dia geram a mesma chave; sem desempate
            # um deles some do ledger em silêncio.
            if vistos[ident] > 1:
                ident = f"{ident}#{vistos[ident]}"
            n, total = achar_parcela(descricao)
            yield {
                "data": data, "valor": str(valor), "origem": origem,
                "competencia": competencia, "id": ident, "descricao": descricao,
                "categoria": "", "parcela_n": n or "", "parcela_total": total or "",
            }


def carregar_categorias():
    if not CATEGORIAS.exists():
        CATEGORIAS.parent.mkdir(parents=True, exist_ok=True)
        with open(CATEGORIAS, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["padrao", "categoria"])
            w.writerows(CATEGORIAS_PADRAO)
    with open(CATEGORIAS, newline="", encoding="utf-8") as fh:
        return [(r["padrao"].upper(), r["categoria"]) for r in csv.DictReader(fh)
                if r.get("padrao")]


def categorizar(descricao, regras):
    alvo = norm(descricao)
    for padrao, categoria in regras:
        if padrao in alvo:
            return categoria
    return "?"


def carregar_ledger():
    if not LEDGER.exists():
        return []
    with open(LEDGER, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def gravar_ledger(linhas):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    linhas.sort(key=lambda r: (r["data"], r["origem"], r["id"]))
    with open(LEDGER, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)


def ingerir(caminhos, competencia=None, substituir=False):
    regras = carregar_categorias()
    ledger = carregar_ledger()
    por_id = {r["id"]: r for r in ledger}
    chegando, escopo = {}, set()
    for caminho in caminhos:
        for linha in ler_csv(caminho, competencia):
            linha["categoria"] = categorizar(linha["descricao"], regras)
            chegando[linha["id"]] = linha
            escopo.add((linha["competencia"], linha["origem"]))

    # Regra nova só valeria para linha nova; sem isto, ensinar uma categoria não
    # conserta o passado e o balde `?` nunca esvazia.
    recategorizadas = 0
    for linha in ledger:
        if linha["categoria"] in ("", "?"):
            achou = categorizar(linha["descricao"], regras)
            if achou != "?":
                linha["categoria"] = achou
                recategorizadas += 1

    novas = [r for i, r in chegando.items() if i not in por_id]
    duplicadas = len(chegando) - len(novas)
    sumidas = [r for r in ledger
               if (r["competencia"], r["origem"]) in escopo and r["id"] not in chegando]

    if sumidas and not substituir:
        print(f"novas {len(novas)} | duplicadas {duplicadas} | desaparecidas {len(sumidas)}")
        print("PARE: linhas no ledger sumiram do arquivo — fatura reemitida?")
        print("Confira e rode de novo com --substituir para trocar a competência inteira.")
        return 1

    if substituir:
        ledger = [r for r in ledger if (r["competencia"], r["origem"]) not in escopo]
        por_id = {r["id"]: r for r in ledger}
        novas = list(chegando.values())

    # Categoria já corrigida à mão vence a regra automática na reingestão.
    for linha in novas:
        antiga = por_id.get(linha["id"])
        if antiga and antiga.get("categoria") not in ("", "?"):
            linha["categoria"] = antiga["categoria"]

    gravar_ledger(ledger + novas)
    print(f"novas {len(novas)} | duplicadas {duplicadas} | desaparecidas {len(sumidas)}")
    sem_categoria = [r for r in novas if r["categoria"] == "?"]
    print(f"ledger: {len(ledger) + len(novas)} linhas | sem categoria nesta carga: {len(sem_categoria)}"
          f" | recategorizadas: {recategorizadas}")
    return 0


def meses_cobertos(ledger):
    meses = sorted({r["competencia"] for r in ledger})
    if not meses:
        return [], []
    buracos, atual = [], meses[0]
    while atual < meses[-1]:
        atual = somar_meses(atual, 1)
        if atual not in meses and atual < meses[-1]:
            buracos.append(atual)
    return meses, buracos


def parcelas_por_mes(ledger):
    """Uma parcela n/total vista na competência C já cobrou desde C-(n-1) e
    cobra até C+(total-n). Serve para os dois lados do tempo: projetar o que
    falta e reconstruir quanto da fatura de um mês cego já era compromisso
    velho — sem precisar do CSV daquele mês, que o app pode nem oferecer mais."""
    span = defaultdict(Decimal)
    for r in ledger:
        if not r["parcela_total"]:
            continue
        n, total = int(r["parcela_n"]), int(r["parcela_total"])
        inicio = somar_meses(r["competencia"], -(n - 1))
        for i in range(total):
            span[somar_meses(inicio, i)] += abs(Decimal(r["valor"]))
    return dict(sorted(span.items()))


def parcelas_a_vencer(ledger, hoje=None):
    hoje = hoje or date.today().strftime("%Y-%m")
    return {m: v for m, v in parcelas_por_mes(ledger).items() if m >= hoje}


def gasto_por_mes(ledger):
    saida, entrada, interno = defaultdict(Decimal), defaultdict(Decimal), defaultdict(Decimal)
    renda = defaultdict(Decimal)
    for r in ledger:
        valor, mes = Decimal(r["valor"]), r["competencia"]
        if r["categoria"] == "interno":
            interno[mes] += valor
        elif r["categoria"] in RENDA:
            renda[mes] += valor
        elif valor < 0:
            saida[mes] += -valor
        else:
            entrada[mes] += valor
    return saida, entrada, interno, renda


def pagamento_fatura(ledger, mes):
    return sum(-Decimal(r["valor"]) for r in ledger if r["competencia"] == mes
               and "PAGAMENTO DE FATURA" in r.get("descricao", "").upper())


def meses_cegos(ledger):
    """Mês que pagou fatura mas não tem CSV de fatura importado. O gasto do
    cartão ali é invisível, e ignorá-lo inventa uma sobra que não existe."""
    com_fatura = {r["competencia"] for r in ledger if r.get("origem") == "fatura"}
    meses = {r["competencia"] for r in ledger}
    return sorted(m for m in meses - com_fatura if pagamento_fatura(ledger, m) > 0)


def variavel_liquido(ledger, meses):
    """Ele paga a conta e os amigos devolvem por Pix. Contar só a saída bruta
    infla o gasto dele em mais de 3x e reprova compra que cabe."""
    saida, entrada, _, _ = gasto_por_mes(ledger)
    cegos = set(meses_cegos(ledger))
    fechados = meses[:-1] or meses
    liquidos = []
    for m in fechados:
        liq = saida[m] - entrada[m]
        if m in cegos:
            liq += pagamento_fatura(ledger, m)
        liquidos.append(max(Decimal("0"), liq))
    return statistics.median(liquidos) if liquidos else Decimal("0")


def ler_perfil():
    numeros = {}
    if PERFIL.exists():
        for linha in PERFIL.read_text(encoding="utf-8").splitlines():
            achou = RE_NUMERO.match(linha.lower())
            if achou:
                numeros[achou.group(1)] = para_decimal(achou.group(2))
    return numeros


def resumo(meses_pedidos=None):
    ledger = carregar_ledger()
    if not ledger:
        print("ledger vazio. Rode `ingerir` primeiro.")
        return 1
    meses, buracos = meses_cobertos(ledger)
    print(f"COBERTURA: {len(meses)} meses — {', '.join(meses)}")
    if buracos:
        print(f"  BURACO na série: {', '.join(buracos)} — mediana sobre série furada mente.")
    if len(meses) < 3:
        print("  Menos de 3 meses: sem base para fuga de padrão. Não invente tendência.")

    cegos = meses_cegos(ledger)
    if cegos:
        print(f"  CEGO em {', '.join(cegos)}: pagou fatura mas o CSV da fatura não foi\n"
              f"  importado. O gasto do cartão nesses meses só aparece como o total pago.")

    futuro = parcelas_a_vencer(ledger)
    total_futuro = sum(futuro.values())
    print(f"\nPARCELAS A VENCER: R$ {total_futuro:.2f} já comprometidos")
    for mes, valor in list(futuro.items())[:12]:
        print(f"  {mes}  R$ {valor:>9.2f}")
    if not futuro:
        print("  nenhuma parcela detectada (você importou fatura de cartão?)")

    cegos = meses_cegos(ledger)
    if cegos:
        passado = parcelas_por_mes(ledger)
        print("\nMÊS CEGO reconstruído pelas parcelas que ainda aparecem na fatura:")
        print(f"  {'mês':<9}{'fatura paga':>13}{'era parcela':>13}{'gasto novo':>12}")
        for m in cegos:
            pago = pagamento_fatura(ledger, m)
            parc = passado.get(m, Decimal("0"))
            print(f"  {m:<9}{pago:>13.2f}{parc:>13.2f}{pago - parc:>12.2f}")
        print("  Parcela encerrada antes da fatura mais nova é invisível: o")
        print("  'gasto novo' é teto, não número exato.")

    saida, entrada, interno, renda = gasto_por_mes(ledger)
    print("\nPOR MÊS (interno fora; entrada de terceiros abate a saída):")
    for mes in meses:
        print(f"  {mes}  renda R$ {renda[mes]:>8.2f}  saída R$ {saida[mes]:>8.2f}"
              f"  volta de terceiros R$ {entrada[mes]:>8.2f}"
              f"  | líquido R$ {saida[mes] - entrada[mes]:>8.2f}")

    por_cat = defaultdict(lambda: defaultdict(Decimal))
    for r in ledger:
        if Decimal(r["valor"]) < 0 and r["categoria"] != "interno":
            por_cat[r["categoria"]][r["competencia"]] += -Decimal(r["valor"])
    atual = meses[-1]
    anteriores = meses[:-1]
    print(f"\nCATEGORIA — {atual} contra mediana dos anteriores:")
    for cat, porm in sorted(por_cat.items(), key=lambda kv: -kv[1][atual]):
        base = [porm[m] for m in anteriores if m in porm]
        mediana = statistics.median(base) if base else Decimal("0")
        agora = porm[atual]
        marca = ""
        if mediana and len(anteriores) >= 2:
            delta = agora - mediana
            pct = delta / mediana * 100
            if pct >= FUGA_PCT and delta >= FUGA_REAIS:
                marca = f"  FUGA +R$ {delta:.2f} (+{pct:.0f}%)"
        print(f"  {cat:<14} R$ {agora:>9.2f}  mediana R$ {mediana:>9.2f}{marca}")

    print("\nMIÚDOS (abaixo de R$ 30, o gasto que não se sente):")
    for mes in meses:
        pequenos = [Decimal(r["valor"]) for r in ledger
                    if r["competencia"] == mes and r["categoria"] != "interno"
                    and Decimal("0") > Decimal(r["valor"]) >= -MIUDO_TETO]
        if pequenos:
            print(f"  {mes}  {len(pequenos):>3} lançamentos  R$ {-sum(pequenos):>9.2f}")

    vistos = defaultdict(set)
    for r in ledger:
        if Decimal(r["valor"]) < 0 and r["categoria"] != "interno":
            vistos[contraparte(r["descricao"])[:30]].add(r["competencia"])
    recorrentes = {k: v for k, v in vistos.items() if len(v) >= 3}
    if recorrentes:
        print("\nRECORRENTES (mesmo lugar em 3+ meses):")
        for chave, m in sorted(recorrentes.items(), key=lambda kv: -len(kv[1]))[:10]:
            print(f"  {len(m)}x  {chave}")

    duvidas = defaultdict(Decimal)
    for r in ledger:
        if r["categoria"] == "?" and Decimal(r["valor"]) < 0:
            duvidas[contraparte(r["descricao"])[:34]] += -Decimal(r["valor"])
    if duvidas:
        gasto_total = sum(saida.values())
        pct = sum(duvidas.values()) / gasto_total * 100 if gasto_total else Decimal("0")
        print(f"\nSEM CATEGORIA: {pct:.0f}% do valor gasto. Maiores:")
        for chave, valor in sorted(duvidas.items(), key=lambda kv: -kv[1])[:5]:
            print(f"  R$ {valor:>9.2f}  {chave}")
    return 0


def simular(preco, parcelas):
    ledger = carregar_ledger()
    perfil = ler_perfil()
    salario = perfil.get("salario_liquido")
    pensao = perfil.get("pensao", Decimal("0"))
    fixos = perfil.get("gastos_fixos")
    reserva = perfil.get("reserva_minima", Decimal("0"))
    if salario is not None:
        salario += pensao
    if salario is None or fixos is None:
        print("PARE: perfil.md sem `salario_liquido` ou `gastos_fixos`. Não dá para simular.")
        return 1

    meses, _ = meses_cobertos(ledger)
    variavel = max(Decimal("0"), variavel_liquido(ledger, meses) - fixos)

    futuro = parcelas_a_vencer(ledger)
    parcela_nova = (preco / parcelas).quantize(Decimal("0.01"))
    inicio = date.today().strftime("%Y-%m")

    cegos = meses_cegos(ledger)
    if cegos:
        # Sem o CSV da fatura, o pagamento dela entra inteiro no variável — e as
        # parcelas já estão dentro dele. Somá-las de novo conta duas vezes, então
        # o veredito erra para o lado apertado. Errar apertado é o lado seguro.
        print(f"AVISO: {len(cegos)} meses sem CSV de fatura ({', '.join(cegos)}).")
        print("O gasto do cartão e as parcelas se sobrepõem, então este resultado é")
        print("mais pessimista que a realidade. Importe as faturas para fechar a conta.\n")

    print(f"Compra R$ {preco:.2f} em {parcelas}x de R$ {parcela_nova:.2f}")
    print(f"Base: renda R$ {salario:.2f} (salário + pensão) | fixos R$ {fixos:.2f} "
          f"| variável mediano R$ {variavel:.2f} | reserva R$ {reserva:.2f}\n")
    pior = None
    for i in range(parcelas):
        mes = somar_meses(inicio, i)
        comprometido = futuro.get(mes, Decimal("0"))
        sobra = salario - fixos - variavel - comprometido
        com_x = sobra - parcela_nova
        if pior is None or com_x < pior[1]:
            pior = (mes, com_x)
        print(f"  {mes}  parcelas atuais R$ {comprometido:>8.2f}  sobra R$ {sobra:>9.2f}"
              f"  com a compra R$ {com_x:>9.2f}")

    mes_pior, folga = pior
    print()
    if folga < 0:
        print(f"NÃO CABE. Em {mes_pior} falta R$ {-folga:.2f}.")
    elif folga < reserva:
        print(f"CABE APERTADO. Em {mes_pior} sobra R$ {folga:.2f}, abaixo da reserva de R$ {reserva:.2f}.")
    else:
        print(f"CABE. Pior mês é {mes_pior}, com R$ {folga:.2f} de folga.")
    if futuro:
        ultimo = max(futuro)
        print(f"Carga atual de parcelas termina em {ultimo}.")
    return 0


def self_check():
    extrato ="Data,Valor,Identificador,Descrição\n14/08/2026,-150.00,abc-1,Compra no débito - PADARIA\n"
    fatura = "date,title,amount\n2026-08-14,Uber* Trip Parcela 3/12,23.90\n2026-08-15,Estorno,-50.00\n"

    def parse(texto, competencia=None):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                        encoding="utf-8", newline="") as fh:
            fh.write(texto)
            nome = fh.name
        try:
            return list(ler_csv(nome, competencia))
        finally:
            Path(nome).unlink()

    e = parse(extrato)
    assert len(e) == 1 and e[0]["origem"] == "extrato", e
    assert e[0]["data"] == "2026-08-14", e[0]["data"]
    assert Decimal(e[0]["valor"]) == Decimal("-150.00"), e[0]["valor"]

    f = parse(fatura)
    assert f[0]["origem"] == "fatura", f[0]
    assert Decimal(f[0]["valor"]) == Decimal("-23.90"), f[0]["valor"]
    assert Decimal(f[1]["valor"]) == Decimal("50.00"), f[1]["valor"]
    assert (f[0]["parcela_n"], f[0]["parcela_total"]) == (3, 12), f[0]
    assert (f[1]["parcela_n"], f[1]["parcela_total"]) == ("", ""), f[1]

    dobrado = parse("date,title,amount\n2026-08-14,CAFE,7.00\n2026-08-14,CAFE,7.00\n")
    assert len({r["id"] for r in dobrado}) == 2, "duas compras iguais viraram uma"

    assert contraparte("Rebill do Brasil - Parcela 9/12") == "REBILL DO BRASIL"
    assert contraparte("Transferência enviada pelo Pix - LARA SILVA - •••.666.964-••") == "LARA SILVA"
    assert contraparte("Resgate RDB") == "RESGATE RDB"

    assert achar_parcela("Compra 12/2026") == (None, None)
    assert somar_meses("2026-11", 3) == "2027-02"
    assert somar_meses("2026-12", 1) == "2027-01"

    fake = [{"competencia": "2026-08", "valor": "-1200.00", "parcela_n": "3",
             "parcela_total": "12", "categoria": "casa", "data": "2026-08-14",
             "origem": "fatura", "id": "x", "descricao": "CADEIRA"}]
    fut = parcelas_a_vencer(fake, hoje="2026-09")
    assert len(fut) == 9, fut
    assert sum(fut.values()) == Decimal("10800.00"), sum(fut.values())

    # Racha de conta: gasta 1000, amigos devolvem 700. O líquido é 300, e usar
    # os 1000 brutos reprova compra que cabe.
    racha = [
        {"competencia": "2026-07", "valor": "-1000.00", "categoria": "compras"},
        {"competencia": "2026-07", "valor": "700.00", "categoria": "?"},
        {"competencia": "2026-08", "valor": "-500.00", "categoria": "compras"},
        {"competencia": "2026-08", "valor": "2613.00", "categoria": "salario"},
        {"competencia": "2026-08", "valor": "500.00", "categoria": "pensao"},
    ]
    assert variavel_liquido(racha, ["2026-07", "2026-08"]) == Decimal("300.00")

    cego = [
        {"competencia": "2026-07", "valor": "-100.00", "categoria": "compras",
         "descricao": "MERCADO", "origem": "extrato"},
        {"competencia": "2026-07", "valor": "-800.00", "categoria": "interno",
         "descricao": "Pagamento de fatura", "origem": "extrato"},
    ]
    assert meses_cegos(cego) == ["2026-07"]
    assert variavel_liquido(cego, ["2026-07"]) == Decimal("900.00")

    assert para_decimal("1.234,56") == Decimal("1234.56")
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
    print("self-check ok")
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("uso: financas.py ingerir <csv...> [--competencia AAAA-MM] [--substituir]")
        print("     financas.py resumo")
        print("     financas.py simular --preco 2500 --parcelas 10")
        print("     financas.py --self-check")
        return 0
    verbo = argv[0]
    if verbo == "--self-check":
        return self_check()
    if verbo == "ingerir":
        competencia = None
        if "--competencia" in argv:
            competencia = argv[argv.index("--competencia") + 1]
        # O valor da flag não é arquivo; sem excluir, o parser tenta abrir "2026-09".
        arquivos = [a for a in argv[1:] if not a.startswith("--") and a != competencia]
        if not arquivos:
            print("nenhum arquivo")
            return 1
        return ingerir(arquivos, competencia, "--substituir" in argv)
    if verbo == "resumo":
        return resumo()
    if verbo == "simular":
        preco = para_decimal(argv[argv.index("--preco") + 1])
        parcelas = int(argv[argv.index("--parcelas") + 1]) if "--parcelas" in argv else 1
        return simular(preco, parcelas)
    print(f"verbo desconhecido: {verbo}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
