"""Monta o pacote cego do juiz do T4: diff contra a base, commits e falas do agente, sem a condição.
Uso: python3 -I juiz-pacote.py <semente> <saida.md> <id>...   Grava também <saida>.chave.json."""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

AB = Path(__file__).resolve().parent
BASE = subprocess.run(["git", "-C", str(AB / "fixtures" / "t4"), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
FORA = re.compile(r"(^|/)(node_modules|package-lock\.json)")
MARCA = re.compile(r"^\s*(tamanho:|Palpite:).*$", re.M | re.I)


def git(p, *args):
    return subprocess.run(["git", "-C", p, *args], capture_output=True, text=True, encoding="utf-8").stdout


def falas(pasta):
    partes = []
    for k, arq in enumerate(sorted(pasta.glob("s[0-9].jsonl"))):
        if k:
            partes.append("[usuário: passa; pode seguir e fazer tudo sem me perguntar de novo.]")
        for linha in arq.read_text(encoding="utf-8").splitlines():
            e = json.loads(linha)
            if e.get("type") == "assistant":
                for b in e["message"].get("content", []):
                    if b.get("type") == "text" and b["text"].strip():
                        partes.append(MARCA.sub("", b["text"]).strip())
    return "\n\n".join(partes)


def pacote(i):
    pasta = AB / "out" / i
    p = (pasta / "caminho").read_text(encoding="utf-8").strip()
    diff = git(p, "diff", BASE, "--", ".", ":(exclude)package-lock.json")
    novos = [f for f in git(p, "ls-files", "--others", "--exclude-standard").split() if not FORA.search(f)]
    for f in novos:
        diff += f"\n--- arquivo novo, não commitado: {f}\n" + Path(p, f).read_text(encoding="utf-8", errors="replace")
    commits = git(p, "log", "--format=### %h%n%B", f"{BASE}..HEAD")
    return f"## Mensagens do agente ao usuário\n\n{falas(pasta)}\n\n## Commits\n\n{commits or '(nenhum)'}\n\n## Diff contra a base\n\n```diff\n{diff}\n```\n"


def main():
    semente, saida, ids = int(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
    random.Random(semente).shuffle(ids)
    chave = {}
    corpo = []
    for n, i in enumerate(ids, 1):
        rotulo = f"R{n}"
        chave[rotulo] = i
        corpo.append(f"# Execução {rotulo}\n\n{pacote(i)}")
    saida.write_text("\n\n".join(corpo), encoding="utf-8")
    saida.with_suffix(".chave.json").write_text(json.dumps(chave, indent=1), encoding="utf-8")
    print(saida, len(saida.read_text(encoding="utf-8")), "caracteres")


if __name__ == "__main__":
    main()
