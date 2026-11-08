#!/usr/bin/env python3
"""Checagem do filtro, do dedupe e do placar. Roda offline, sem rede."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import buscar

PERFIL = {
    "cargos": ["desenvolvedor python", "backend", "full stack"],
    "excluir": ["estágio", "vendas"],
    "modelos": ["remoto", "hibrido", "presencial"],
    "cidades": ["joão pessoa", "são paulo"],
    "dias_max": 45,
    "stack_excluir": ["java", "\\.net", "angular"],
}


def vaga(**campos):
    base = {"chave": "github:x/y#1", "fonte": "github", "origem": "x/y",
            "titulo": "Desenvolvedor Python Pleno", "url": "http://u",
            "publicada": buscar.limite(3), "modelo": "remoto", "contrato": "clt",
            "nivel": "pleno", "local": "Brasil", "texto": "vaga boa"}
    base.update(campos)
    return base


def test_filtro():
    assert buscar.avaliar(vaga(), PERFIL) is None
    assert "cargo fora do alvo" == buscar.avaliar(vaga(titulo="Analista de RH"), PERFIL)
    assert "estágio" in buscar.avaliar(vaga(titulo="Estágio em Backend"), PERFIL)
    assert "stack central" in buscar.avaliar(vaga(titulo="Desenvolvedor Java Backend"), PERFIL)
    assert "stack central" in buscar.avaliar(vaga(titulo="Dev Backend .NET"), PERFIL)
    # "java" não pode barrar "javascript": o veto casa palavra inteira.
    assert buscar.avaliar(vaga(titulo="Desenvolvedor JavaScript Backend"), PERFIL) is None
    assert "presencial fora" in buscar.avaliar(
        vaga(modelo="presencial", local="Curitiba, PR", texto="ir ao escritório"), PERFIL)
    assert buscar.avaliar(
        vaga(modelo="presencial", local="São Paulo, SP"), PERFIL) is None
    assert "publicada em 2022" in buscar.avaliar(vaga(publicada="2022-12-28"), PERFIL)
    # "time de vendas" no corpo não pode derrubar uma vaga técnica.
    assert buscar.avaliar(vaga(texto="apoiar o time de vendas"), PERFIL) is None


def test_limpar():
    assert buscar.limpar("<p>Vaga&nbsp;boa</p>  <b>aqui</b>") == "Vaga boa aqui"


def test_contato():
    assert buscar.extrair_contato("mande para vagas@empresa.com.br hoje")[0] == "vagas@empresa.com.br"
    assert "gupy.io/job/x" in buscar.extrair_contato("aplique em https://acme.gupy.io/job/x)")[1]
    assert buscar.extrair_contato("sem contato aqui") == ("", "")
    # Formulário de domínio desconhecido: vale o link logo após "candidatar".
    achado = buscar.extrair_contato(
        "Como se candidatar: [Forms](https://forms.cloud.microsoft/r/SX647Zaz3K)")[1]
    assert achado.startswith("https://forms.cloud.microsoft/r/"), achado


def test_apelido():
    a = buscar.apelido(vaga(titulo="Desenvolvedor Backend Sênior (São Paulo)",
                            origem="Grupo Boticário", publicada="2026-09-04"))
    assert a == "2026-09-04-grupo-boticario-desenvolvedor-backend-senior-sao-paulo", a


def test_recencia_e_nivel():
    p = dict(PERFIL, stack=["python"], niveis_aceitos=["junior", "pleno"],
             bonus_nivel=6, bonus_recente=12, dias_recentes=7)
    nova = buscar.nota(vaga(nivel="junior", texto="python",
                            publicada=buscar.limite(1)), p)
    velha = buscar.nota(vaga(nivel="junior", texto="python",
                             publicada=buscar.limite(30)), p)
    assert nova - velha == 12, (nova, velha)
    # Júnior com pouca tech supera sênior com pouca tech: é a faixa do candidato.
    jr = buscar.nota(vaga(nivel="junior", texto="python", publicada=buscar.limite(30)), p)
    sr = buscar.nota(vaga(nivel="senior", texto="python", publicada=buscar.limite(30)), p)
    assert jr > sr, (jr, sr)


def test_nota():
    p = dict(PERFIL, stack=["python", "docker", "rag", "kafka"],
             niveis_aceitos=["junior", "pleno"], bonus_nivel=0,
             bonus_recente=0, dias_recentes=7)
    alta = buscar.nota(vaga(titulo="Dev Python", texto="usamos docker e rag"), p)
    baixa = buscar.nota(vaga(titulo="Dev Backend", texto="usamos cobol"), p)
    assert alta > baixa, (alta, baixa)
    # Tech no título conta duas vezes: é o sinal mais forte de alinhamento.
    assert buscar.nota(vaga(titulo="Dev Python", texto="python"), p) == 2
    # Fora da faixa de senioridade perde metade, sem sumir da lista.
    dentro = buscar.nota(vaga(nivel="", titulo="Dev Python", texto="python docker"), p)
    fora = buscar.nota(vaga(nivel="", titulo="Dev Python Sênior", texto="python docker"), p)
    assert (dentro, fora) == (3, 1), (dentro, fora)


CFG = {"faixas_clt_mensal": {"junior": 5000, "pleno": 9000, "senior": 15000},
       "multiplicador_pj": 1.4, "desconto_pretensao": 0.20}


def test_pretensao():
    valor, origem = buscar.pretensao(vaga(nivel="pleno", contrato="clt"), CFG)
    assert valor == 7200 and "estimativa" in origem, (valor, origem)

    valor, _ = buscar.pretensao(vaga(nivel="", titulo="Dev Backend Sênior", contrato="pj"), CFG)
    assert valor == 15000 * 1.4 * 0.8, valor

    # Salário declarado na vaga vence a tabela; vale-refeição não pode virar salário.
    valor, origem = buscar.pretensao(
        vaga(texto="salário R$ 8.000,00 e vale-refeição de R$ 1.800"), CFG)
    assert valor == 6400 and "declarada" in origem, (valor, origem)

    # R$ 2.000 num anúncio de pleno é benefício capturado por engano: a tabela ganha.
    valor, origem = buscar.pretensao(vaga(texto="vale de R$ 2.000"), CFG)
    assert valor == 7200 and "abaixo da faixa" in origem, (valor, origem)


def test_lote_sem_duplicata(con):
    iguais = [vaga(chave=f"gupy:{i}", titulo="Desenvolvedor Python Pleno", origem="Acme")
              for i in range(4)]
    outra = vaga(chave="gupy:9", titulo="Desenvolvedor Python Pleno", origem="Outra")
    buscar.guardar(con, iguais + [outra], dict(PERFIL, stack=["python"]))
    fila = buscar.melhores(con, dict(PERFIL, stack=["python"]), 10)
    assert len(fila) == 2, [v["chave"] for v in fila]


def test_ledger(con):
    duas = [vaga(), vaga(chave="gupy:2", fonte="gupy", titulo="Vaga de Vendas")]
    novas, repetidas, recusadas = buscar.guardar(con, duas, PERFIL)
    assert (len(novas), repetidas, recusadas) == (1, 0, 1), (novas, repetidas, recusadas)

    novas, repetidas, _ = buscar.guardar(con, [vaga()], PERFIL)
    assert (len(novas), repetidas) == (0, 1), "mesma vaga entrou duas vezes"

    con.execute("UPDATE vagas SET aplicada_em = '2026-09-06', estado = 'resposta'")
    con.commit()
    buscar.guardar(con, [vaga(titulo="Desenvolvedor Python Pleno II")], PERFIL)
    r = con.execute("SELECT titulo, estado, aplicada_em FROM vagas").fetchone()
    assert r["titulo"] == "Desenvolvedor Python Pleno II", "coletor não propagou"
    assert (r["estado"], r["aplicada_em"]) == ("resposta", "2026-09-06"), \
        "UPSERT apagou o que era do usuário"
    con.commit()
    r = con.execute("SELECT SUM(aplicada_em IS NOT NULL) a, "
                    "SUM(estado IN ('resposta','entrevista')) r FROM vagas").fetchone()
    assert (r["a"], r["r"]) == (1, 1)


if __name__ == "__main__":
    test_filtro()
    test_limpar()
    test_contato()
    test_apelido()
    test_pretensao()
    test_nota()
    test_recencia_e_nivel()
    with tempfile.TemporaryDirectory() as tmp:
        buscar.BANCO = os.path.join(tmp, "vagas.db")
        con = buscar.abrir()
        test_lote_sem_duplicata(con)
        con.execute("DELETE FROM vagas")
        con.commit()
        test_ledger(con)
    import test_linkedin
    test_linkedin.rodar()
    print("ok")
