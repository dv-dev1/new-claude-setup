#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from decisoes import decisoes, sessoes, janela, _ler

AGORA = datetime.now(timezone.utc)
T = AGORA.strftime("%Y-%m-%dT%H:%M:%S.000Z")
PLAN = "## PLAN\n\nFaço: troco X\nEncaixa em: y\nAlternativa: SVG à mão, caro\nMexe em: z\n\nok?"


def humano(texto, **extra):
    return {"type": "user", "timestamp": T, "origin": {"kind": "human"}, "message": {"content": texto}, **extra}


def assistente(*blocos):
    return {"type": "assistant", "timestamp": T, "message": {"content": list(blocos)}}


def resultado(id_, conteudo, extra=None):
    bloco = {"type": "tool_result", "tool_use_id": id_, "content": conteudo}
    return {"type": "user", "timestamp": T, "message": {"content": [bloco]},
            "toolUseResult": conteudo if extra is None else extra}


def texto(registros):
    return "\n".join(decisoes(registros))


def main():
    saida = texto([
        humano("Melhora essa porra aí"),
        {"type": "user", "timestamp": T, "isMeta": True,
         "message": {"content": [{"type": "text", "text": "Base directory for this skill"}]}},
        {"type": "user", "timestamp": T, "origin": {"kind": "task-notification"},
         "message": {"content": "<task-notification>x</task-notification>"}},
        humano("<command-message>explain-project</command-message>\n<command-name>/explain-project</command-name>\n"
               "<command-args>entender o projeto</command-args>"),
        assistente({"type": "tool_use", "id": "q1", "name": "AskUserQuestion", "input": {}}),
        resultado("q1", "answered", {"questions": [], "answers": {"Qual desenho?": "Os dois\r(Recommended)"}}),
        {"type": "user", "timestamp": T, "isSidechain": True, "origin": {"kind": "human"},
         "message": {"content": "do subagente"}},
    ])
    assert '[você disse] "Melhora essa porra aí"' in saida, saida
    for ruido in ("Base directory", "task-notification", "do subagente"):
        assert ruido not in saida, saida
    assert '[você disse] "entender o projeto"' in saida, saida
    assert '[você escolheu] "Qual desenho?" → "Os dois (Recommended)"' in saida, saida
    assert len(texto([humano("x" * 500)]).split('"')[1]) == 300

    com_ok = texto([assistente({"type": "text", "text": PLAN}), humano("ok")])
    assert '[você aprovou] Faço: troco X · Alternativa: SVG à mão, caro → "ok"' in com_ok, com_ok
    assert "[você disse]" not in com_ok, com_ok

    pelo_plano = texto([
        assistente({"type": "text", "text": PLAN}, {"type": "tool_use", "id": "p1", "name": "ExitPlanMode", "input": {}}),
        resultado("p1", "User has approved your plan. You can now start coding."),
    ])
    assert "[você aprovou] Faço: troco X · Alternativa: SVG à mão, caro" in pelo_plano, pelo_plano

    recusado = texto([assistente({"type": "text", "text": PLAN}), humano("não, faz com Y"), humano("ok")])
    assert "[você aprovou]" not in recusado, recusado

    with tempfile.TemporaryDirectory() as tmp:
        alvo = Path(tmp, "repo", "a.py")
        alvo.parent.mkdir()
        alvo.write_text("x = 1\n", encoding="utf-8")
        projeto = Path(tmp, "projetos", "-repo")
        projeto.mkdir(parents=True)
        edicao = {"type": "tool_use", "id": "e1", "name": "Edit", "input": {"file_path": str(alvo)}}
        antiga = dict(humano("antes da janela"), timestamp=(AGORA - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
        linhas = [antiga, humano("faz assim"), assistente(edicao)]
        (projeto / "boa.jsonl").write_text("\n".join(map(json.dumps, linhas)) + '\n{"trunc', encoding="utf-8")
        (projeto / "outra.jsonl").write_text(json.dumps(humano("outra coisa")) + "\n", encoding="utf-8")
        atalho = Path(tmp, "atalho")
        try:
            atalho.symlink_to(alvo.parent, target_is_directory=True)
            por_atalho = dict(edicao, input={"file_path": str(atalho / "a.py")})
            (projeto / "linkada.jsonl").write_text(json.dumps(assistente(por_atalho)) + "\n", encoding="utf-8")
        except OSError:
            pass  # Windows sem permissão de symlink
        achadas = {j.stem: regs for j, regs in sessoes(Path(tmp, "projetos"), {str(alvo.resolve())}, set(),
                                                       AGORA - timedelta(hours=1), AGORA + timedelta(hours=1))}
        assert "boa" in achadas and "outra" not in achadas, achadas.keys()
        assert atalho.exists() == ("linkada" in achadas), achadas.keys()
        assert "antes da janela" not in json.dumps(achadas["boa"]), achadas["boa"]

    exit_plan_sem_pendente = texto([
        assistente({"type": "tool_use", "id": "p2", "name": "ExitPlanMode", "input": {}}),
        resultado("p2", [{"type": "text", "text": "User has approved your plan. You can now start coding.\n\n## Approved Plan:\n# Meu plano\n\n## Contexto\nx"}]),
    ])
    assert '[você aprovou] plano "Meu plano"' in exit_plan_sem_pendente, exit_plan_sem_pendente

    # item 5: resumo de compactação é ignorado
    compact = texto([
        {"type": "user", "timestamp": T, "isCompactSummary": True,
         "message": {"content": "This session is being continued"}},
    ])
    assert compact == "", compact

    # item 6: título do ExitPlanMode vence um pendente velho
    titulo_vence = texto([
        assistente({"type": "text", "text": PLAN.replace("troco X", "velho")}),
        assistente({"type": "tool_use", "id": "p3", "name": "ExitPlanMode", "input": {}}),
        resultado("p3", "User has approved your plan. You can now start coding.\n\n"
                        "## Approved Plan:\n# Plano novo"),
    ])
    assert '[você aprovou] plano "Plano novo"' in titulo_vence, titulo_vence
    assert "Faço: velho" not in titulo_vence, titulo_vence

    # item 7: aprovação exige começar com a palavra e ter no máximo 3 palavras
    nao_aprovacao = texto([assistente({"type": "text", "text": PLAN}), humano("ok, mas usa a lib Y")])
    assert "[você aprovou]" not in nao_aprovacao, nao_aprovacao
    assert '[você disse] "ok, mas usa a lib Y"' in nao_aprovacao, nao_aprovacao

    # item 8: "## PLAN" fora de uma linha própria não vira pendente
    sem_pendente = texto([
        assistente({"type": "text", "text": "vou mostrar o ## PLAN depois"}),
        humano("pode rodar os testes"),
    ])
    assert "[você aprovou]" not in sem_pendente, sem_pendente

    with tempfile.TemporaryDirectory() as tmp:
        alvo = Path(tmp, "repo", "alvo.py")
        alvo.parent.mkdir()
        alvo.write_text("x = 1\n", encoding="utf-8")
        projeto = Path(tmp, "projetos", "-repo")
        projeto.mkdir(parents=True)

        # item 1: edição do subagente conta, mas os registros devolvidos são os do pai
        pai = [humano("só o usuário fala aqui")]
        (projeto / "pai.jsonl").write_text("\n".join(map(json.dumps, pai)) + "\n", encoding="utf-8")
        sub_dir = projeto / "pai" / "subagents"
        sub_dir.mkdir(parents=True)
        edicao_sub = assistente({"type": "tool_use", "id": "es1", "name": "Edit",
                                  "input": {"file_path": str(alvo)}})
        (sub_dir / "agent-x.jsonl").write_text(json.dumps(edicao_sub) + "\n", encoding="utf-8")
        achadas = {j.stem: regs for j, regs in sessoes(Path(tmp, "projetos"), {str(alvo.resolve())}, set(),
                                                        AGORA - timedelta(hours=1), AGORA + timedelta(hours=1))}
        assert "pai" in achadas, achadas.keys()
        assert achadas["pai"] == pai, achadas["pai"]

        # item 2: tool_use Bash cujo command cita o caminho relativo também conta como toque
        bash_call = assistente({"type": "tool_use", "id": "b1", "name": "Bash",
                                 "input": {"command": "sed -i 's/x/y/' sub/b.py"}})
        (projeto / "bash.jsonl").write_text(json.dumps(bash_call) + "\n", encoding="utf-8")
        achadas2 = {j.stem: regs for j, regs in sessoes(Path(tmp, "projetos"), set(), {"sub/b.py"},
                                                         AGORA - timedelta(hours=1), AGORA + timedelta(hours=1))}
        assert "bash" in achadas2, achadas2.keys()

    # item 9: byte UTF-8 cortado não derruba a leitura
    with tempfile.TemporaryDirectory() as tmp:
        ruim = Path(tmp, "ruim.jsonl")
        ruim.write_bytes(json.dumps(humano("ok")).encode("utf-8") + b"\n" + b"\xc3")
        registros = _ler(ruim)
        assert len(registros) == 1, registros

    # itens 3 e 4: "..." usa merge-base, e a janela usa data de autor (sobrevive a rebase/amend)
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp, "gitrepo")
        repo.mkdir()

        def git(*args, data=None):
            env = os.environ.copy()
            if data:
                env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = data
            subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)

        git("init", "-q")
        git("config", "user.name", "t")
        git("config", "user.email", "t@t.com")
        (repo / "sub").mkdir()
        (repo / "sub" / "a.txt").write_text("1", encoding="utf-8")
        d1 = "2020-01-01T00:00:00+00:00"
        git("add", "sub/a.txt")
        git("commit", "-q", "-m", "c1", data=d1)
        git("tag", "c1")
        (repo / "outro.txt").write_text("1", encoding="utf-8")
        d2 = "2020-01-02T00:00:00+00:00"
        git("add", "outro.txt")
        git("commit", "-q", "-m", "c2", data=d2)
        git("tag", "c2")
        (repo / "sub" / "a.txt").write_text("2", encoding="utf-8")
        d3 = "2020-01-03T00:00:00+00:00"
        git("add", "sub/a.txt")
        git("commit", "-q", "-m", "c3", data=d3)
        git("tag", "c3")

        arquivos, relativos, inicio, fim = janela(str(repo), "c3")
        assert inicio == datetime.fromisoformat(d1), (inicio, d1)

        arquivos2, relativos2, inicio2, fim2 = janela(str(repo), "c1...c3")
        assert arquivos2, "c1...c3 devia achar arquivos mudados"

    print("ok")


if __name__ == "__main__":
    main()
