# Corte de overhead Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tirar do setup o desperdício medido em 2026-11-11 sem perder o que tem benefício medido.

**Architecture:** As mudanças ficam todas no repo `~/new-claude-setup`, que é a fonte. O `install.sh` aplica no `~/.claude`:
- arquivos de `hooks/` por symlink;
- o `settings.json` por merge recursivo: dicts se fundem chave a chave, e listas e valores do repo vencem.

Inclui um hook Python novo, valores novos no `settings.json`, texto novo no `compactar.txt` e no `CLAUDE.global.md`, e um script de medição em `benchmark/`.

**Tech Stack:** Python 3 só com a stdlib e JSON do Claude Code 2.1.322. Os testes rodam como script, sem pytest (`python3 tests/<arquivo>.py`).

**Spec:** `docs/superpowers/specs/2026-11-11-corte-de-overhead-design.md`

## Global Constraints

- Os 3 lembretes do `UserPromptSubmit` ficam palavra por palavra como estão hoje no `settings.json`.
- O `skillOverrides` não esconde skill de plugin na 2.1.322 (testado em 2026-11-11). As 5 de plugin da spec (`ponytail:ponytail-help`, `ponytail:ponytail-gain`, `ponytail:ponytail-debt`, `ponytail:ponytail-review`, `superpowers:using-superpowers`) ficam fora.
- Conectores saem por `permissions.deny`, que foi testado: Drive fica e Docs/Calendar saem. Não usar `disableClaudeAiConnectors`, que derruba o Drive.
- `modelSettings`: `claude-opus-5-5` em `high`, `claude-sonnet-5-5` em `high`, `claude-fable-5-2` em `medium`.
- `autoCompactWindow: 350000`.
- O `compactar.txt` não passa de 10.000 caracteres (limite do PreCompact).
- Commit com a identidade do `origin` (`dv-dev1`), push direto na `main`, sem assinatura do Claude.

## Review Focus

1. Entrada do hook sem `prompt` ou com JSON inválido: o lembrete continua saindo. Falhar aberto, nunca travar o prompt.
2. `prompt` com espaço ou quebra de linha antes de `<task-notification>`: fica calado.
3. Prompt humano que só cita `<task-notification>` no meio do texto: recebe o lembrete, porque só o prefixo conta.
4. `settings.json` local com chaves velhas (`sonnet: xhigh`, os 3 hooks `echo`): depois do `install.sh` vale o valor do repo. O repo precisa declarar o Sonnet e o Fable de forma explícita, porque o merge de dict mantém as chaves locais.
5. Transcript com linha corrompida, resumo de compactação com `content` em lista ou sessão sem compactação: o script de cobertura pula a linha ou a sessão sem quebrar.

---

### Task 1: Lembretes só em prompt humano

**Files:**
- Create: `hooks/lembretes.py`
- Modify: `settings.json` (`hooks.UserPromptSubmit`: os 3 `echo` viram 1 comando)
- Test: `tests/test_setup.py`

**Interfaces:**
- Produces: o comando `python3 "$HOME/.claude/hooks/lembretes.py"`. Ele lê o JSON do hook no stdin e imprime 1 linha `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext": "<os 3 textos, separados por \n\n>"}}` ou não imprime nada.

- [ ] **Step 1: Ajustar o helper de teste para mandar stdin e ligar `lembretes.py` no HOME de mentira**

Em `tests/test_setup.py`, `saidas(evento, entrada="")`:
- copia `hooks/lembretes.py` para `<home>/.claude/hooks/`, ao lado do `caveman.md`;
- passa `input=entrada` no `subprocess.run`.

- [ ] **Step 2: Escrever os testes que falham**

```python
def lembretes(prompt=None, cru=None):
    entrada = cru if cru is not None else json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt})
    return [json.loads(s)["hookSpecificOutput"]["additionalContext"] for s in saidas("UserPromptSubmit", entrada) if s.strip()]

def test_lembrete_caveman_por_mensagem():  # substitui o atual
    textos = lembretes("corrige o bug")
    assert len(textos) == 1 and LEMBRETE in textos[0]
    assert "SUPERPOWERS: as unicas skills" in textos[0] and "PONYTAIL: ao escrever codigo" in textos[0]

def test_lembrete_calado_em_aviso_de_tarefa():
    assert lembretes("<task-notification>\n<task-id>a1</task-id>") == []
    assert lembretes("  \n<task-notification><task-id>a1</task-id>") == []
    assert lembretes("<local-command-stdout>ok</local-command-stdout>") == []

def test_lembrete_sai_em_fala_que_so_cita_o_aviso():
    assert len(lembretes("o que é <task-notification>?")) == 1

def test_lembrete_falha_aberto():
    assert len(lembretes(cru="nao e json")) == 1
    assert len(lembretes(cru="{}")) == 1
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python3 tests/test_setup.py`
Expected: FALHA em `test_lembrete_calado_em_aviso_de_tarefa` (os `echo` ignoram o stdin) e em `test_lembrete_caveman_por_mensagem` (hoje saem 3 saídas, não 1).

- [ ] **Step 4: Implementar `hooks/lembretes.py` e trocar o hook no `settings.json`**

- `NAO_HUMANO = ("<local-command-", "<system-reminder>", "<task-notification>")`, a mesma tupla do `varredura.py`.
- Se `prompt.lstrip().startswith(NAO_HUMANO)`, sai calado.
- Em qualquer erro de leitura, `prompt = ""`, e o lembrete sai.
- Os 3 textos vêm palavra por palavra dos `echo` atuais, na ordem SUPERPOWERS, PONYTAIL, CAVEMAN.
- `settings.json`: `hooks.UserPromptSubmit` passa a ser `[{"hooks":[{"type":"command","command":"python3 \"$HOME/.claude/hooks/lembretes.py\""}]}]`.

- [ ] **Step 5: Rodar e ver passar**

Run: `python3 tests/test_setup.py && python3 tests/test_varredura.py`
Expected: todas as linhas com `ok`, exit 0.

- [ ] **Step 6: Commit**

```bash
git add hooks/lembretes.py settings.json tests/test_setup.py
git commit -m "fix(hooks): lembretes do UserPromptSubmit só em fala humana, não em aviso de tarefa"
```

### Task 2: Valores do settings, regra de re-review e README

**Files:**
- Modify: `settings.json`, `CLAUDE.global.md`, `README.md`
- Test: `tests/test_setup.py`

**Interfaces:**
- Consumes: o `settings.json` da Task 1.

- [ ] **Step 1: Escrever o teste que falha**

```python
def test_settings_corte_de_overhead():
    with open(os.path.join(RAIZ, "settings.json"), encoding="utf-8") as fh:
        s = json.load(fh)
    assert s["autoCompactWindow"] == 350000
    assert s["modelSettings"] == {"claude-opus-5-5": {"effortLevel": "high"},
                                  "claude-sonnet-5-5": {"effortLevel": "high"},
                                  "claude-fable-5-2": {"effortLevel": "medium"}}
    escondidas = ["code-review", "simplify", "loop", "schedule", "init", "security-review",
                  "fewer-permission-prompts", "keybindings-help", "plugin-authoring", "run",
                  "anthropic-skills:skill-creator", "anthropic-skills:docs", "anthropic-skills:docx",
                  "anthropic-skills:pptx"]
    assert all(s["skillOverrides"][n] == "user-invocable-only" for n in escondidas)
    assert s["skillOverrides"]["anthropic-skills:morning"] == "off"
    assert set(s["permissions"]["deny"]) == {"mcp__claude_ai_Gmail", "mcp__claude_ai_Google_Calendar",
                                             "mcp__claude_ai_Claude_Docs"}
    with open(os.path.join(RAIZ, "CLAUDE.global.md"), encoding="utf-8") as fh:
        assert "- Re-review" in fh.read()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 tests/test_setup.py`
Expected: FALHA em `test_settings_corte_de_overhead` (`KeyError` ou `550000 != 350000`).

- [ ] **Step 3: Editar `settings.json`, `CLAUDE.global.md` e `README.md`**

- `settings.json`: os valores do teste. Os 5 `"off"` atuais do `skillOverrides` ficam.
- `CLAUDE.global.md`: uma linha logo depois da linha `- Code review:`, com este texto exato:

```
- Re-review (rodada de correção do review): subagente em Sonnet, nunca em Haiku; no máximo 2 rodadas, depois pare e chame o usuário. Review inicial, revisão final e thermos ficam em Opus.
```

- `README.md`:
  - linha `settings.json`: trocar "Opus 5.5 em xhigh" por "Opus 5.5 e Sonnet 5.5 em high (Fable em medium)" e "550k, 55% da janela" por "350k, 35% da janela";
  - na mesma linha, acrescentar "conectores Gmail, Calendar e Claude Docs negados (`permissions.deny`)" e "14 skills sem uso escondidas do modelo (`skillOverrides: "user-invocable-only"`, `/nome` funciona)";
  - linha do plugin `superpowers`: "lembrete no `UserPromptSubmit`" passa a citar `hooks/lembretes.py`, "só em fala humana";
  - linha `CLAUDE.global.md`: acrescentar "regra de re-review".

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 tests/test_setup.py`
Expected: todas `ok`.

- [ ] **Step 5: Commit**

```bash
git add settings.json CLAUDE.global.md README.md tests/test_setup.py
git commit -m "perf(setup): esforço high, compactação em 350k, skills e conectores sem uso fora do contexto, re-review em Sonnet"
```

### Task 3: Compactação mais forte para resumo de resumo

**Files:**
- Modify: `hooks/compactar.txt`, `README.md` (linha do `compactar.txt`)
- Test: `tests/test_varredura.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
def test_compactar_segura_compactacao_repetida():
    texto = open(os.path.join(RAIZ, "hooks", "compactar.txt"), encoding="utf-8").read()
    for trecho in ("Inputs the user already provided",
                   "The user's last 3 messages verbatim.",
                   "Sources of truth on disk",
                   "Subagents and background tasks in flight",
                   "If a previous summary exists, carry its User Instructions & Preferences and PENDING items forward",
                   "Before finishing: re-scan every user message since the last summary",
                   "User-Provided Inputs"):
        assert trecho in texto, trecho
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 tests/test_varredura.py`
Expected: FALHA em `test_compactar_segura_compactacao_repetida` com `AssertionError('Inputs the user already provided')`.

- [ ] **Step 3: Editar `hooks/compactar.txt`**

- Na lista "Preserve…", logo depois de "The user's latest request and the exact next action.":

```
Inputs the user already provided (files, paths, pasted data, answers to questions) and where they are — never ask for them again.
The user's last 3 messages verbatim.
```

- Logo depois de "External state: …":

```
Sources of truth on disk: plan, spec, ledger and report paths, and the active skill's current step (e.g. SDD Task 4, re-review round 1). Point to them; re-read them before resuming.
Subagents and background tasks in flight: ID, what each does, what to do when it finishes.
If a previous summary exists, carry its User Instructions & Preferences and PENDING items forward unchanged unless resolved.
```

- Em "Structure the summary as", logo depois de "User Instructions & Preferences": `User-Provided Inputs`.
- Antes da última linha ("Err on the side…"): `Before finishing: re-scan every user message since the last summary and confirm each instruction, correction and provided input appears.`
- README, linha `hooks/compactar.txt`: acrescentar "dados já entregues, últimas 3 falas, fontes de verdade no disco, trabalho em andamento, herança do resumo anterior e checagem final".

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 tests/test_varredura.py`
Expected: todas `ok`. Inclui `test_compactar_cabe_no_limite_do_precompact`, ≤ 10.000.

- [ ] **Step 5: Commit**

```bash
git add hooks/compactar.txt tests/test_varredura.py README.md
git commit -m "feat(compactar): guarda dados entregues, últimas falas e herda o resumo anterior"
```

### Task 4: Medidor de cobertura da compactação

**Files:**
- Create: `benchmark/compactacao/cobertura.py`
- Modify: `benchmark/RESULTADOS.md` (seção 2026-11-11 com a base), `benchmark/README.md` (uma linha de uso)
- Test: `tests/test_cobertura.py`

**Interfaces:**
- Produces: `cobertura(caminhos: list[str], desde: str) -> dict`, com as chaves `compactacoes`, `arquivos` `(preservados, total)` e `shas` `(preservados, total)`. A CLI é `python3 benchmark/compactacao/cobertura.py [--desde 2026-11-11] [--raiz ~/.claude/projects]` e imprime as 3 linhas com %.

- [ ] **Step 1: Escrever os testes que falham**

O arquivo `tests/test_cobertura.py` segue o padrão dos outros: carrega o módulo por `importlib` e tem o runner no `__main__`. A fixture grava um `.jsonl` temporário com:
- um assistente que faz `Edit` em `/r/a.py` e em `/r/b.py` e escreve "commit 1a2b3c4";
- uma linha corrompida;
- um resumo `{"type":"user","isCompactSummary":true,"timestamp":"2026-11-12T00:00:00Z","message":{"content":[{"type":"text","text":"mexi em a.py no 1a2b3c4"}]}}`;
- depois do resumo, um `Edit` em `/r/c.py`, que não pode contar.

```python
def test_cobertura_conta_so_o_trecho_antes_do_resumo():
    r = cobertura.cobertura([fixture], "2026-11-11")
    assert r["compactacoes"] == 1
    assert r["arquivos"] == (1, 2)   # a.py sim, b.py não; c.py é depois do resumo
    assert r["shas"] == (1, 1)

def test_cobertura_ignora_resumo_antes_da_data_e_sessao_sem_resumo():
    assert cobertura.cobertura([fixture], "2026-11-13")["compactacoes"] == 0
    assert cobertura.cobertura([sem_resumo], "2026-11-11")["compactacoes"] == 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 tests/test_cobertura.py`
Expected: erro de import (`FileNotFoundError`/`No such file`), porque o módulo ainda não existe.

- [ ] **Step 3: Implementar `benchmark/compactacao/cobertura.py`**

- O trecho de cada resumo vai do resumo anterior, ou do começo do arquivo, até ele.
- Arquivos: `file_path` de `Edit`, `Write` e `MultiEdit` do assistente. Conta como preservado se o `basename` aparece no texto do resumo.
- SHAs: `\b[0-9a-f]{7,10}\b` no texto do assistente, com pelo menos uma letra e um dígito. Conta como preservado se aparece exato.
- O `content` do resumo pode ser string ou lista de blocos `text`.
- Linha que não é JSON é pulada.
- Na CLI, a raiz padrão é `~/.claude/projects/*/*.jsonl`: só sessões principais, sem `subagents/`.

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 tests/test_cobertura.py && python3 benchmark/compactacao/cobertura.py --desde 2026-11-08`
Expected: testes `ok`. A CLI mostra perto da base medida: 14 compactações, arquivos 79/83 (95%), SHAs 41/52 (79%). Pode haver diferença pequena se houve compactação nova desde então.

- [ ] **Step 5: Registrar a base**

Em `benchmark/RESULTADOS.md`, nova seção "11/11/2026 — base da compactação (550k)":
- as 3 linhas da Step 4;
- a regra: rodar `--desde <data do deploy>` daqui a ~1 semana; se arquivos ou SHAs caírem abaixo da base, `autoCompactWindow` volta para 550000.

Em `benchmark/README.md`, uma linha de uso.

- [ ] **Step 6: Commit**

```bash
git add benchmark/compactacao/cobertura.py tests/test_cobertura.py benchmark/RESULTADOS.md benchmark/README.md
git commit -m "feat(benchmark): medidor de cobertura da compactação e base de 11/11"
```

### Task 5: Aplicar no local, conferir ao vivo e subir

**Files:**
- Nenhum arquivo novo. Roda `install.sh` e confere o `~/.claude`.

- [ ] **Step 1: Aplicar**

Run: `bash install.sh`
Expected: termina sem erro. Depois, `python3 -c 'import json;d=json.load(open("/Users/dvdev/.claude/settings.json"));print(d["autoCompactWindow"],d["modelSettings"],d["permissions"]["deny"],len(d["hooks"]["UserPromptSubmit"][0]["hooks"]))'` imprime:
- `350000`;
- os 3 modelos com o esforço da Global Constraints;
- os 3 deny;
- `1`.

`ls -la ~/.claude/hooks/lembretes.py` mostra um symlink para o repo.

- [ ] **Step 2: Conferir as skills escondidas (Haiku, pasta vazia do scratchpad)**

Run: `claude -p 'Liste, separados por vírgula e sem mais nada, os nomes exatos das skills da sua lista cujo nome contém "code-review", "simplify", "skill-creator", "docx" ou "brainstorming".' --model haiku --no-session-persistence --max-turns 1 --strict-mcp-config`
Expected: só `superpowers:brainstorming`.

- [ ] **Step 3: Conferir o lembrete calado em aviso de tarefa**

Run: `claude -p '<task-notification><task-id>teste</task-id></task-notification>' --model haiku --max-turns 1 --session-id <uuid novo> --strict-mcp-config`. Depois, procurar `hook_additional_context` com `UserPromptSubmit` no transcript `~/.claude/projects/<pasta>/<uuid>.jsonl`.
Expected: 0 ocorrências. Repetir com o prompt `oi`: 1 ocorrência.

- [ ] **Step 4: Conferir os conectores (até 3 tentativas, porque o carregamento é assíncrono)**

Run: `claude -p 'Liste, separados por vírgula, os servidores MCP nos nomes das suas ferramentas (inclusive adiadas), formato mcp__<servidor>.' --model haiku --no-session-persistence --max-turns 1`
Expected: na tentativa em que os conectores carregarem, aparece `mcp__claude_ai_Google_Drive` e não aparecem Gmail, Calendar nem Claude Docs.

- [ ] **Step 5: Rodar a suíte inteira**

Run: `python3 tests/test_setup.py && python3 tests/test_varredura.py && python3 tests/test_cobertura.py`
Expected: tudo `ok`, exit 0.

- [ ] **Step 6: Subir**

```bash
git add docs/superpowers/specs/2026-11-11-corte-de-overhead-design.md docs/superpowers/plans/2026-11-11-corte-de-overhead.md
git commit -m "docs: spec e plano do corte de overhead"
git push origin main
```

Expected: o push aceito em `main`, e `git status -sb` mostra `## main...origin/main` sem ahead.

- [ ] **Step 7: Avisar sobre as sessões abertas**

As 3 sessões abertas desde 9:29 (car-dealer-crm, etros-n8n, jarvis) seguem com a config antiga até reiniciar. O hook novo e o `autoCompactWindow` só valem em sessão nova ou depois de `/clear`.
