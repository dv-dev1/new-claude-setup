#!/usr/bin/env python3
"""Verifica o roteiro com um histórico git descartável."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("roteiro.py")


def ambiente():
    return dict(os.environ, GIT_AUTHOR_NAME="Teste", GIT_AUTHOR_EMAIL="teste@example.com",
                GIT_COMMITTER_NAME="Teste", GIT_COMMITTER_EMAIL="teste@example.com",
                GIT_AUTHOR_DATE="2020-01-01T12:00:00+00:00",
                GIT_COMMITTER_DATE="2020-01-01T12:00:00+00:00",
                GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off",
                           "-c", "commit.gpgsign=false", *args], env=ambiente(),
                          capture_output=True, encoding="utf-8", errors="replace",
                          check=True).stdout.strip()


def rodar(repo, *args, entrada=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args, "--repo", str(repo)],
                          input=entrada, env=ambiente(), capture_output=True,
                          encoding="utf-8", errors="replace")


def salvar_commit(repo, caminho, texto, assunto, corpo=None):
    alvo = repo / caminho
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(texto, encoding="utf-8")
    git(repo, "add", "--", caminho)
    mensagem = ["-m", assunto] + (["-m", corpo] if corpo else [])
    git(repo, "commit", "-q", *mensagem)
    return git(repo, "log", "-1", "--format=%h")


def ler_estado(caminho):
    return json.loads(caminho.read_text(encoding="utf-8"))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp, "repo")
        repo.mkdir()
        git(repo, "init", "-q", "-b", "principal")
        salvar_commit(repo, "test_motor.py", "assert True\n", "Testar motor")
        teste = git(repo, "log", "-1", "--format=%h")
        fonte = salvar_commit(repo, "motor.py", "\n".join("valor_%d = %d" % (i, i)
                              for i in range(12)) + "\n", "Construir motor",
                              "Corpo: preservar a decisão registrada.")
        documento = salvar_commit(repo, "guia.md", "CONTEUDO_DOCUMENTO_EXCLUSIVO\n", "Explicar uso")
        git(repo, "checkout", "-q", "-b", "peca")
        ramo = salvar_commit(repo, "peça nova.py", "ramo = True\n", "Adicionar peça")
        git(repo, "checkout", "-q", "principal")
        git(repo, "merge", "--no-ff", "--no-gpg-sign", "-m", "Merge excluído", "peca")
        shas = [teste, fonte, documento, ramo]
        comum = Path(git(repo, "rev-parse", "--git-common-dir"))
        estado = (comum if comum.is_absolute() else repo / comum) / "do-zero.json"

        resultado = rodar(repo, "commits")
        assert resultado.returncode == 0 and [l.split()[0] for l in resultado.stdout.splitlines()] == shas, resultado
        assert "Merge excluído" not in resultado.stdout, resultado.stdout
        assert all("  2020-01-01 12:00  +" in l and "  | " in l
                   for l in resultado.stdout.splitlines()), resultado.stdout
        resultado = rodar(repo, "capitulo")
        assert resultado.returncode == 1 and "sem roteiro" in resultado.stderr, resultado

        incompleto = "Motor | %s %s\nfora: texto | %s\n" % (fonte, teste, documento)
        resultado = rodar(repo, "gravar", entrada=incompleto)
        assert resultado.returncode == 1 and ramo in resultado.stderr and not estado.exists(), resultado
        for entrada, erro in [("Motor | %s %s\n" % (fonte, fonte), "repetido"),
                              ("Motor | zzzzzzz\n", "desconhecido"),
                              ("Sem separador\n", "linha 1"),
                              ("fora: tudo | %s\n" % " ".join(shas), "nenhum capítulo")]:
            resultado = rodar(repo, "gravar", entrada=entrada)
            assert resultado.returncode == 1 and erro in resultado.stderr and not estado.exists(), resultado

        agrupamento = "# roteiro\n\nMotor | %s %s\nPeça | %s\nfora: texto | %s\n" % (fonte, teste, ramo, documento)
        resultado = rodar(repo, "gravar", entrada=agrupamento)
        assert resultado.returncode == 0 and ler_estado(estado)["proximo"] == 1, resultado
        assert ler_estado(estado)["capitulos"][0]["commits"] == [teste, fonte], ler_estado(estado)
        assert "1  Motor  (2 commits, 2020-01-01 a 2020-01-01)" in resultado.stdout and "fora: 1 commits" in resultado.stdout, resultado.stdout

        inicial = ler_estado(estado)
        resultado = rodar(repo, "capitulo")
        saida = resultado.stdout
        assert resultado.returncode == 0 and "Capítulo 1 de 2: Motor" in saida and "Corpo: preservar" in saida and "+valor_0 = 0" in saida and ler_estado(estado)["proximo"] == 2, resultado
        assert saida.index("--- %s motor.py" % fonte) < saida.index("--- %s test_motor.py" % teste), saida
        assert saida.splitlines()[-1] == "próximo: capítulo 2 de 2: Peça", saida
        assert ler_estado(estado) == dict(inicial, proximo=2), ler_estado(estado)

        resultado = rodar(repo, "capitulo", "1", "--linhas", "5")
        assert "cortado: git show %s -- motor.py  (13 linhas)" % fonte in resultado.stdout and "cortado: git show %s -- test_motor.py" % teste in resultado.stdout, resultado.stdout
        trecho = resultado.stdout.split("--- %s motor.py\n" % fonte)[1].split("cortado:")[0]
        assert len(trecho.splitlines()) == 5, resultado.stdout
        anterior = estado.read_text(encoding="utf-8")
        resultado = rodar(repo, "capitulo", "99")
        assert "roteiro terminado: 2 capítulos" in resultado.stdout and estado.read_text(encoding="utf-8") == anterior, resultado
        for args in [("capitulo", "0"), ("capitulo", "1", "--linhas", "-1"), ("capitulo", "x")]:
            resultado = rodar(repo, *args)
            assert resultado.returncode == 1 and resultado.stderr and estado.read_text(encoding="utf-8") == anterior, resultado

        novo = salvar_commit(repo, "extra.py", "extra = True\n", "Nova entrega")
        resultado = rodar(repo, "capitulo", "1")
        assert "sem capítulo" in resultado.stdout and "%s Nova entrega" % novo in resultado.stdout, resultado.stdout
        agrupamento = "Motor | %s %s %s\nPeça | %s %s\n" % (fonte, teste, documento, ramo, novo)
        resultado = rodar(repo, "gravar", entrada=agrupamento)
        assert resultado.returncode == 0 and ler_estado(estado)["proximo"] == 2, resultado
        resultado = rodar(repo, "capitulo", "1")
        assert "guia.md" in resultado.stdout and "CONTEUDO_DOCUMENTO_EXCLUSIVO" not in resultado.stdout, resultado.stdout
        resultado = rodar(repo, "capitulo", "2")
        assert "Antes: 1 Motor" in resultado.stdout and resultado.stdout.splitlines()[-1] == "último capítulo", resultado.stdout
        resultado = rodar(repo, "gravar", entrada="Tudo | %s\n" % " ".join(shas + [novo]))
        assert resultado.returncode == 0 and ler_estado(estado)["proximo"] == 2, resultado

        repetido = rodar(repo, "gravar", entrada="Um | %s\nDois | %s\n" % (teste, teste))
        assert repetido.returncode == 1 and "repetido" in repetido.stderr, repetido
        anteriores = git(repo, "log", "--no-merges", "--format=%h").splitlines()
        while len({s[0] for s in anteriores}) == len(anteriores):
            git(repo, "commit", "--allow-empty", "-q", "-m", "Buscar colisão %d" % len(anteriores))
            anteriores.append(git(repo, "log", "-1", "--format=%h"))
        prefixo = next(s[0] for s in anteriores if sum(outro.startswith(s[0]) for outro in anteriores) > 1)
        resultado = rodar(repo, "gravar", entrada="Tudo | %s\n" % prefixo)
        assert resultado.returncode == 1 and "ambíguo" in resultado.stderr, resultado

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp, "repo")
        repo.mkdir()
        git(repo, "init", "-q", "-b", "principal")
        for numero in range(1, 7):
            (repo / ("fonte%d.py" % numero)).write_text("valor = 1\n" * numero, encoding="utf-8")
        (repo / "binario.py").write_bytes(b"\x00\xff\x01")
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "Arquivos ordenados")
        sha = git(repo, "log", "-1", "--format=%h")
        resultado = rodar(repo, "commits")
        assert "+21 -0" in resultado.stdout and resultado.stdout.rstrip().endswith("fonte6.py,fonte5.py,fonte4.py,fonte3.py +3"), resultado.stdout
        resultado = rodar(repo, "gravar", entrada="Fontes | %s\n" % sha)
        assert resultado.returncode == 0, resultado
        resultado = rodar(repo, "capitulo", "1", "--linhas", "0")
        assert "--- " not in resultado.stdout and "cortado:" in resultado.stdout and "-- binario.py" not in resultado.stdout, resultado.stdout
        arvore = Path(tmp, "arvore")
        git(repo, "worktree", "add", "-q", "--detach", str(arvore), "HEAD")
        resultado = rodar(arvore, "capitulo", "1")
        assert resultado.returncode == 0 and "Capítulo 1 de 1: Fontes" in resultado.stdout, resultado
        resultado = rodar(arvore, "gravar", entrada="Reagrupado | %s\n" % sha)
        assert resultado.returncode == 0 and ler_estado(repo / ".git" / "do-zero.json")["capitulos"][0]["titulo"] == "Reagrupado", resultado
    print("ok")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
