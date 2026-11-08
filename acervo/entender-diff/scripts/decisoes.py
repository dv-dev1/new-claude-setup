#!/usr/bin/env python3
"""O que o usuário disse, escolheu e aprovou nas sessões do Claude Code que editaram um diff.
Uso: decisoes.py --repo CAMINHO --rev A..B|SHA"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EDITORES = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
MAX = 300
_APROVACAO = re.compile(r"(ok|sim|pode|manda|aprovado|bora)\b", re.I)


def _aprovacao(texto):
    return bool(_APROVACAO.match(texto)) and len(texto.split()) <= 3
_COMANDO = re.compile(r"<command-(name|message)>.*?</command-\1>", re.S)
_TAG_ARGS = re.compile(r"</?command-args>")
_TITULO_PLANO = re.compile(r"## Approved Plan:\s*#\s*(.+)")
_LINHA_PLAN = re.compile(r"^## PLAN\s*$", re.M)
_LINHA_FACO = re.compile(r"^Faço:", re.M)


def _quando(texto):
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def _linha(texto):
    return " ".join(texto.split())[:MAX]


def _blocos(r):
    conteudo = (r.get("message") or {}).get("content")
    return [b for b in conteudo if isinstance(b, dict)] if isinstance(conteudo, list) else []


def _texto(r):
    conteudo = (r.get("message") or {}).get("content")
    if isinstance(conteudo, str):
        return conteudo
    return " ".join(b.get("text", "") for b in _blocos(r) if b.get("type") == "text")


def _digitado(r):
    if r.get("type") != "user" or r.get("isMeta") or "toolUseResult" in r:
        return None
    texto = _texto(r)
    origem = r.get("origin")
    if origem is not None:
        humano = origem.get("kind") == "human"
    else:
        # Transcript antigo, sem origin: o que o harness injeta começa com tag.
        humano = not texto.lstrip().startswith("<")
    if not humano:
        return None
    return _linha(_TAG_ARGS.sub("", _COMANDO.sub("", texto))) or None


def _plano(texto):
    partes = [l.strip() for l in texto.splitlines() if l.strip().startswith(("Faço:", "Alternativa:"))]
    return _linha(" · ".join(partes)) or "PLAN"


def _texto_resultado(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def decisoes(registros):
    saida, ferramentas, pendente = [], {}, None
    for r in registros:
        if r.get("isSidechain") or r.get("isCompactSummary"):
            continue
        hora = _quando(r["timestamp"]).astimezone().strftime("%d/%m %H:%M") if r.get("timestamp") else "?"
        if r.get("type") == "assistant":
            for b in _blocos(r):
                if b.get("type") == "tool_use":
                    ferramentas[b.get("id")] = b.get("name")
                elif b.get("type") == "text" and _LINHA_PLAN.search(b.get("text", "")) \
                        and _LINHA_FACO.search(b.get("text", "")):
                    pendente = _plano(b["text"])
            continue
        for b in _blocos(r):
            ferramenta = ferramentas.get(b.get("tool_use_id"))
            resultado = r.get("toolUseResult")
            if ferramenta == "AskUserQuestion" and isinstance(resultado, dict):
                for pergunta, resposta in resultado.get("answers", {}).items():
                    saida.append('- %s [você escolheu] "%s" → "%s"' % (hora, _linha(pergunta), _linha(resposta)))
            elif ferramenta == "ExitPlanMode" and "approved your plan" in str(b.get("content")):
                texto_resultado = _texto_resultado(b.get("content"))
                if "approved your plan" in texto_resultado:
                    titulo_match = _TITULO_PLANO.search(texto_resultado)
                    titulo = _linha(titulo_match.group(1)) if titulo_match else None
                    if titulo:
                        saida.append('- %s [você aprovou] plano "%s"' % (hora, titulo))
                    elif pendente:
                        saida.append("- %s [você aprovou] %s" % (hora, pendente))
                    else:
                        saida.append("- %s [você aprovou] plano do ExitPlanMode" % hora)
                    pendente = None
        texto = _digitado(r)
        if texto is None:
            continue
        if pendente and _aprovacao(texto):
            saida.append('- %s [você aprovou] %s → "%s"' % (hora, pendente, texto))
        else:
            saida.append('- %s [você disse] "%s"' % (hora, texto))
        pendente = None
    return saida


def _editou(r, arquivos, relativos):
    for b in _blocos(r):
        if b.get("type") != "tool_use":
            continue
        entrada = b.get("input") if isinstance(b.get("input"), dict) else {}
        caminho = entrada.get("file_path") or entrada.get("notebook_path")
        if b.get("name") in EDITORES and caminho and os.path.realpath(caminho) in arquivos:
            return True
        if entrada:
            # Bash (sed -i, cat > arq, git add) não passa file_path: casa o caminho no texto do input.
            texto_entrada = json.dumps(entrada)
            if any(rel in texto_entrada for rel in relativos) or any(abs_ in texto_entrada for abs_ in arquivos):
                return True
    return False


def _ler(jsonl):
    registros = []
    with jsonl.open(encoding="utf-8", errors="replace") as f:
        for linha in f:
            try:
                registros.append(json.loads(linha))
            except json.JSONDecodeError:
                continue  # sessão aberta pode estar no meio de uma linha
    return registros


def _tocou(jsonl, arquivos, relativos, inicio, fim):
    registros = [r for r in _ler(jsonl) if r.get("timestamp") and inicio < _quando(r["timestamp"]) <= fim]
    return any(_editou(r, arquivos, relativos) for r in registros)


def sessoes(projetos, arquivos, relativos, inicio, fim):
    # ponytail: janela de tempo entre os commits é heurística; filtrar pelo SHA citado se casar sessão errada.
    for jsonl in sorted(Path(projetos).glob("*/*.jsonl")):
        subagentes = sorted((jsonl.parent / jsonl.stem / "subagents").glob("*.jsonl"))
        mais_novo = max([jsonl.stat().st_mtime] + [s.stat().st_mtime for s in subagentes])
        if datetime.fromtimestamp(mais_novo, timezone.utc) < inicio:
            continue
        registros = [r for r in _ler(jsonl) if r.get("timestamp") and inicio < _quando(r["timestamp"]) <= fim]
        # a sessão-pai não edita quando o trabalho vai por subagente: o toque pode estar só lá.
        tocou = any(_editou(r, arquivos, relativos) for r in registros) or \
            any(_tocou(s, arquivos, relativos, inicio, fim) for s in subagentes)
        if tocou:
            yield jsonl, registros


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout.strip()


def _horario_autor(repo, ref):
    return _quando(_git(repo, "log", "-1", "--format=%aI", ref))


def janela(repo, rev):
    if "..." in rev:
        a, b = rev.split("...", 1)
        base, fim = _git(repo, "merge-base", a, b), b
    elif ".." in rev:
        base, fim = rev.split("..", 1)
    else:
        base, fim = rev + "^", rev
    raiz = Path(_git(repo, "rev-parse", "--show-toplevel"))
    linhas = _git(repo, "diff", "--name-only", base, fim).splitlines()
    arquivos = {os.path.realpath(raiz / a) for a in linhas}
    relativos = {a for a in linhas if "/" in a}
    # rebase/amend reescreve a data do committer; a de autor sobrevive.
    inicio_str = _git(repo, "log", "-1", "--format=%aI", base, "--", *linhas) if linhas else ""
    inicio = _quando(inicio_str) if inicio_str else _horario_autor(repo, base)
    return arquivos, relativos, inicio, _horario_autor(repo, fim)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True)
    p.add_argument("--rev", required=True)
    p.add_argument("--projetos", default=str(Path.home() / ".claude" / "projects"))
    a = p.parse_args()
    try:
        arquivos, relativos, inicio, fim = janela(a.repo, a.rev)
    except subprocess.CalledProcessError as erro:
        print("git falhou: %s" % erro.stderr.strip(), file=sys.stderr)
        return 2
    achou = False
    for jsonl, registros in sessoes(a.projetos, arquivos, relativos, inicio, fim):
        achou = True
        print("## sessão %s" % jsonl.stem)
        print("\n".join(decisoes(registros)) or "(nada dito, escolhido ou aprovado)")
    if not achou:
        print("sem transcript: porquê vem de commit/spec/pergunta")
    return 0


if __name__ == "__main__":
    sys.exit(main())
