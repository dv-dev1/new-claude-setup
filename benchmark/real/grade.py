#!/usr/bin/env python3
"""Corrige as execuções de bug real: teste escondido do commit de correção sobre a árvore do agente, suíte inteira e custo.
Uso: python3 -I grade.py [id ...]"""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

R = Path(__file__).resolve().parent
sys.path.insert(0, str(R.parent / "ab"))
import grade as g  # noqa: E402
from grade import sessoes, ciclo, rodar, git  # noqa: E402

g.TESTOU = re.compile(g.TESTOU.pattern + r"|go\s+test|pytest")  # o lancer é Go

TAREFAS = {l.split()[0]: l.split()[1:] for l in (R / "tarefas.txt").read_text().splitlines() if l.strip()}
EH_TESTE = re.compile(r"(^|/)(test|tests)/|\.test\.|_test\.go$|test_.*\.py$")
T = ["node", "--test", "--test-reporter=tap"]
SUITE = {"pinch": [*T, "--test-concurrency=1", "test/**/*.test.ts"], "brim": [*T, "test/*.test.ts"], "lancer": ["go", "test", "-count=1", "-v", "./..."],
         "quehorasvoto": [*T, "test/"], "etros-n8n": [*T, "regras/"]}
# shortcut: teste de desempenho ("em menos de 50 ms") cai com a máquina carregada pelas execuções em paralelo; não conta como regressão
TEMPO = re.compile(r"\d+\s*ms\b|painel a frio")  # os 2 do painel a frio caem até no commit da correção


def regressoes(repo, pasta):
    rc, s = rodar(SUITE[repo], cwd=pasta)
    falhas = re.findall(r"^\s*--- FAIL: (\S+)", s, re.M) if repo == "lancer" else re.findall(r"^\s*not ok \d+ - (.+)$", s, re.M)
    if rc and not falhas:
        return ["(suíte não rodou)"]
    return [f for f in falhas if not TEMPO.search(f)]


def escondido(repo, testes, pasta):
    if repo == "lancer":
        pacotes = sorted({"./" + str(Path(t).parent) + "/" for t in testes})
        rc, s = rodar(["go", "test", "-count=1", "-v", *pacotes], cwd=pasta)
        return rc == 0, len(re.findall(r"^\s*--- PASS", s, re.M)), len(re.findall(r"^\s*--- FAIL", s, re.M))
    extra = ["--test-concurrency=1"] if repo == "pinch" else []
    rc, s = rodar(["node", "--test", *extra, "--test-reporter=tap", *testes], cwd=pasta)
    n = lambda k: int(m.group(1)) if (m := re.search(rf"^# {k} (\d+)", s, re.M)) else 0
    return rc == 0, n("pass"), n("fail")


def corrigir(id_):
    out = R / "out" / id_
    repo, fix = TAREFAS[id_.split("-")[0]]
    run = Path((out / "caminho").read_text().strip())
    testes = [f for f in git(Path.home() / repo, "diff-tree", "--no-commit-id", "--name-only", "-r", fix).splitlines() if EH_TESTE.search(f)]
    with tempfile.TemporaryDirectory(dir=R) as tmp:
        copia = Path(tmp) / repo
        subprocess.run(["cp", "-cR", str(run), str(copia)], check=True)
        for t in testes:  # o teste escondido sobrescreve o que o agente deixou no mesmo arquivo
            (copia / t).write_bytes(subprocess.run(["git", "-C", str(Path.home() / repo), "show", f"{fix}:{t}"], capture_output=True).stdout)
        ok, ps, fs = escondido(repo, testes, copia)
        regr = regressoes(repo, copia)
        suite = not regr
    s = sessoes(out)
    skills = sorted({json.loads(l)["message"]["content"][i]["input"].get("skill", "")
                     for f in sorted(out.glob("s*.jsonl")) for l in f.read_text().splitlines() if '"name":"Skill"' in l
                     for i, b in enumerate(json.loads(l)["message"]["content"]) if b.get("name") == "Skill"})
    pai = git(Path.home() / repo, "rev-parse", f"{fix}^")
    nota = {"id": id_, "escondido_ok": ok, "pass": ps, "fail": fs, "suite_ok": suite, "regressoes": regr, "custo": s["custo"], "ms": s["ms"],
            "turnos": s["turnos"], "tokens_saida": s["tokens_saida"], "sessoes": s["sessoes"], "erros": s["erros"], "skills": skills,
            "commits": len(git(run, "rev-list", f"{pai}..HEAD").split()),
            "parede_s": int((out / "parede_s").read_text()) if (out / "parede_s").exists() else None,
            "diff": git(run, "diff", "--shortstat", pai), **ciclo(s["passos"])}
    (out / "nota.json").write_text(json.dumps(nota, ensure_ascii=False, indent=1))
    return nota


def main():
    ids = sys.argv[1:] or sorted(p.name for p in (R / "out").iterdir() if p.is_dir())
    ns = [corrigir(i) for i in ids]
    print("| id | escondido | suíte | custo | parede s | turnos | testou depois | skills | commits | diff |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for n in ns:
        print(f"| {n['id']} | {n['pass']}/{n['pass'] + n['fail']} {'ok' if n['escondido_ok'] else 'FALHA'} | {'ok' if n['suite_ok'] else 'FALHA'} | "
              f"{n['custo']:.2f} | {n['parede_s']} | {n['turnos']} | {'sim' if n['testou_depois_da_ultima_edicao'] else 'não'} | "
              f"{','.join(x.split(':')[-1] for x in n['skills']) or '-'} | {n['commits']} | {n['diff']} |")
    for c in sorted({n["id"].split("-")[1] for n in ns}):
        g = [n for n in ns if n["id"].split("-")[1] == c]
        print(f"{c}: escondido {sum(n['escondido_ok'] for n in g)}/{len(g)}; suíte {sum(n['suite_ok'] for n in g)}/{len(g)}; "
              f"US$ {sum(n['custo'] for n in g):.2f}; parede {sum(n['parede_s'] or 0 for n in g) / 60:.1f} min; "
              f"testou depois {sum(n['testou_depois_da_ultima_edicao'] for n in g)}/{len(g)}; perguntas {sum(n['sessoes'] - 1 for n in g)}")


if __name__ == "__main__":
    main()
