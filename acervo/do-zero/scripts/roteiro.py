#!/usr/bin/env python3
"""Lista o histórico, valida capítulos e imprime material para narrar um repositório."""
import argparse
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath


SO_STAT = {".md", ".txt", ".rst", ".pdf", ".png", ".jpg", ".jpeg", ".gif",
           ".svg", ".ico", ".lock", ".csv", ".json", ".snap", ".map"}
NOMES_STAT = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock",
              "poetry.lock", "Cargo.lock", "go.sum"}


class Argumentos(argparse.ArgumentParser):
    def error(self, mensagem):
        raise ValueError(mensagem)


def git(repo, *args):
    resultado = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *args],
                               capture_output=True, encoding="utf-8", errors="replace")
    if resultado.returncode:
        raise ValueError("git falhou: " + resultado.stderr.strip())
    return resultado.stdout


def historico(repo):
    campos = git(repo, "log", "--no-merges", "--reverse", "--topo-order", "-z",
                 "--date=format:%Y-%m-%d %H:%M", "--format=%H%x00%h%x00%ad%x00%s").split("\0")
    return [dict(zip(("completo", "sha", "data", "assunto"), campos[i:i + 4]))
            for i in range(0, len(campos) - 1, 4)]


def arquivos(repo, sha):
    texto = git(repo, "show", "--numstat", "-z", "--format=", "--no-renames",
                "--no-ext-diff", "--no-textconv", sha, "--")
    saida = []
    for registro in texto.split("\0"):
        if not registro:
            continue
        inseridas, removidas, caminho = registro.split("\t", 2)
        binario = inseridas == "-" or removidas == "-"
        saida.append({"caminho": caminho, "inseridas": 0 if binario else int(inseridas),
                      "removidas": 0 if binario else int(removidas), "binario": binario})
    return saida


def listar_commits(repo, commits):
    for commit in commits:
        alterados = arquivos(repo, commit["completo"])
        maiores = sorted(alterados, key=lambda a: -(a["inseridas"] + a["removidas"]))
        caminhos = ",".join(a["caminho"] for a in maiores[:4])
        if len(maiores) > 4:
            caminhos += " +%d" % (len(maiores) - 4)
        print("%s  %s  +%d -%d  %s  | %s" %
              (commit["sha"], commit["data"], sum(a["inseridas"] for a in alterados),
               sum(a["removidas"] for a in alterados), commit["assunto"], caminhos))


def caminho_estado(repo):
    comum = Path(git(repo, "rev-parse", "--git-common-dir").strip())
    return (comum if comum.is_absolute() else Path(repo) / comum) / "do-zero.json"


def ler_estado(caminho):
    if not caminho.exists():
        return None
    estado = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(estado, dict) or type(estado.get("proximo")) is not int or estado["proximo"] < 1:
        raise ValueError("estado inválido: proximo")
    for chave, rotulo in (("capitulos", "titulo"), ("fora", "motivo")):
        grupos = estado.get(chave)
        if not isinstance(grupos, list) or (chave == "capitulos" and not grupos):
            raise ValueError("estado inválido: " + chave)
        for grupo in grupos:
            if (not isinstance(grupo, dict) or not isinstance(grupo.get(rotulo), str)
                    or not grupo[rotulo].strip() or not isinstance(grupo.get("commits"), list)
                    or not grupo["commits"] or any(not isinstance(s, str) or not s for s in grupo["commits"])):
                raise ValueError("estado inválido: " + chave)
    return estado


def salvar_estado(caminho, estado):
    caminho.write_text(json.dumps(estado, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def resolver_sha(prefixo, commits):
    encontrados = [c for c in commits if c["completo"].startswith(prefixo)]
    if len(encontrados) != 1:
        raise ValueError("sha %s: %s" % ("ambíguo" if encontrados else "desconhecido", prefixo))
    return encontrados[0]["sha"]


def agrupar(texto, commits):
    capitulos, fora, usados = [], [], set()
    for numero, linha in enumerate(texto.splitlines(), 1):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if "|" not in linha:
            raise ValueError("linha %d sem |" % numero)
        titulo, prefixos = (parte.strip() for parte in linha.split("|", 1))
        descarte = titulo.startswith("fora:")
        rotulo = titulo[5:].strip() if descarte else titulo
        if not rotulo or not prefixos:
            raise ValueError("linha %d: título/motivo ou commits vazios" % numero)
        selecionados = set()
        for prefixo in prefixos.split():
            sha = resolver_sha(prefixo, commits)
            if sha in usados:
                raise ValueError("sha repetido: " + sha)
            usados.add(sha)
            selecionados.add(sha)
        grupo = {"motivo" if descarte else "titulo": rotulo,
                 "commits": [c["sha"] for c in commits if c["sha"] in selecionados]}
        (fora if descarte else capitulos).append(grupo)
    faltando = [c for c in commits if c["sha"] not in usados]
    if faltando:
        raise ValueError("commits sem agrupamento:\n" + "\n".join(c["sha"] + " " + c["assunto"] for c in faltando))
    if not capitulos:
        raise ValueError("nenhum capítulo")
    return {"proximo": 1, "capitulos": capitulos, "fora": fora}


def gravar(repo, commits):
    estado = agrupar(sys.stdin.read(), commits)
    caminho = caminho_estado(repo)
    antigo = ler_estado(caminho)
    if antigo:
        estado["proximo"] = min(antigo["proximo"], len(estado["capitulos"]) + 1)
    salvar_estado(caminho, estado)
    datas = {c["sha"]: c["data"][:10] for c in commits}
    for numero, capitulo in enumerate(estado["capitulos"], 1):
        dias = [datas[s] for s in capitulo["commits"]]
        print("%d  %s  (%d commits, %s a %s)" %
              (numero, capitulo["titulo"], len(dias), min(dias), max(dias)))
    if estado["fora"]:
        print("fora: %d commits" % sum(len(g["commits"]) for g in estado["fora"]))


def classe(arquivo):
    caminho = PurePosixPath(arquivo["caminho"])
    nome = caminho.name
    if arquivo["binario"] or caminho.suffix.lower() in SO_STAT or nome in NOMES_STAT:
        return "stat"
    if (any(p in {"test", "tests", "__tests__", "spec"} for p in caminho.parts)
            or nome.startswith("test_") or any(p in nome for p in ("_test.", ".test.", ".spec."))):
        return "teste"
    return "fonte"


def hunks(repo, sha, caminho):
    diff = git(repo, "show", "--format=", "--unified=3", "--no-color", "--no-renames",
               "--no-ext-diff", "--no-textconv", sha, "--", ":(literal)" + caminho)
    saida, dentro = [], False
    for linha in diff.splitlines():
        if linha.startswith("@@"):
            dentro = True
            saida.append(linha)
        elif dentro and linha.startswith((" ", "+", "-")):
            saida.append(linha)
    return saida


def imprimir_diffs(repo, selecionados, limite):
    pendentes = []
    for commit in selecionados:
        for arquivo in arquivos(repo, commit["completo"]):
            tipo = classe(arquivo)
            if tipo != "stat":
                pendentes.append((tipo, commit["sha"], commit["completo"], arquivo["caminho"]))
    cortados = []
    for _, sha, completo, caminho in sorted(pendentes, key=lambda a: a[0] == "teste"):
        linhas = hunks(repo, completo, caminho)
        quantidade = min(limite, len(linhas))
        if quantidade:
            print("--- %s %s" % (sha, caminho))
            print("\n".join(linhas[:quantidade]))
        if quantidade < len(linhas):
            cortados.append((sha, caminho, len(linhas)))
        limite -= quantidade
    for sha, caminho, quantidade in cortados:
        print("cortado: git show %s -- %s  (%d linhas)" % (sha, caminho, quantidade))


def imprimir_capitulo(repo, commits, estado, numero, limite):
    capitulos = estado["capitulos"]
    capitulo = capitulos[numero - 1]
    selecionados = [c for c in commits if c["sha"] in capitulo["commits"]]
    if len(selecionados) != len(capitulo["commits"]):
        raise ValueError("capítulo com sha ausente ou repetido: rode gravar de novo")
    print("Capítulo %d de %d: %s" % (numero, len(capitulos), capitulo["titulo"]))
    if numero > 1:
        print("Antes: " + "; ".join("%d %s" % (i, c["titulo"])
                                      for i, c in enumerate(capitulos[:numero - 1], 1)))
    if numero < len(capitulos):
        print("Depois: " + capitulos[numero]["titulo"])
    for commit in selecionados:
        print("== %s  %s  %s" % (commit["sha"], commit["data"], commit["assunto"]))
        corpo = git(repo, "show", "-s", "--format=%b", commit["completo"]).strip()
        if corpo:
            print(corpo)
        stat = git(repo, "show", "--stat", "--format=", "--no-color", "--no-ext-diff",
                   "--no-textconv", commit["completo"], "--").rstrip("\n")
        if stat:
            print(stat)
    imprimir_diffs(repo, selecionados, limite)
    usados = {s for g in capitulos + estado["fora"] for s in g["commits"]}
    faltando = [c for c in commits if c["sha"] not in usados]
    if faltando:
        print("ATENÇÃO: %d commits sem capítulo, rode gravar de novo:" % len(faltando))
        for commit in faltando:
            print(commit["sha"] + " " + commit["assunto"])
    if numero < len(capitulos):
        print("próximo: capítulo %d de %d: %s" % (numero + 1, len(capitulos), capitulos[numero]["titulo"]))
    else:
        print("último capítulo")


def capitulo(repo, numero, limite):
    if numero is not None and numero < 1:
        raise ValueError("capítulo deve ser maior que zero")
    if limite < 0:
        raise ValueError("--linhas deve ser maior ou igual a zero")
    caminho = caminho_estado(repo)
    estado = ler_estado(caminho)
    if estado is None:
        raise ValueError("sem roteiro: rode `commits` e depois `gravar`")
    numero = estado["proximo"] if numero is None else numero
    if numero > len(estado["capitulos"]):
        print("roteiro terminado: %d capítulos" % len(estado["capitulos"]))
        return
    imprimir_capitulo(repo, historico(repo), estado, numero, limite)
    estado["proximo"] = numero + 1
    salvar_estado(caminho, estado)


def main():
    argumentos = Argumentos(description=__doc__)
    comandos = argumentos.add_subparsers(dest="comando", required=True)
    for nome in ("commits", "gravar", "capitulo"):
        comando = comandos.add_parser(nome)
        comando.add_argument("--repo", default=".")
        if nome == "capitulo":
            comando.add_argument("numero", nargs="?", type=int)
            comando.add_argument("--linhas", type=int, default=400)
    try:
        args = argumentos.parse_args()
        if args.comando == "capitulo":
            capitulo(args.repo, args.numero, args.linhas)
        elif args.comando == "commits":
            listar_commits(args.repo, historico(args.repo))
        else:
            gravar(args.repo, historico(args.repo))
    except (ValueError, OSError) as erro:
        print(str(erro), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    sys.exit(main())
