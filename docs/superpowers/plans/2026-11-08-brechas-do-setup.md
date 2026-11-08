# Brechas do setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Varredura que pega correção entre turnos e por subagente, caveman no modo padrão sem o plugin, e acervo com as skills fora da lista.

**Architecture:** O `hooks/varredura.py` passa a olhar o turno atual e o anterior, e lê transcript de subagente sem descartar `isSidechain`. O caveman vira 3 hooks no `settings.json` que leem `hooks/caveman.md`. O acervo é uma pasta do repo que o `install.sh` não liga, indexada numa linha do `CLAUDE.global.md`.

**Tech Stack:** Python 3 stdlib (hooks e testes, sem pytest), JSON do Claude Code 2.1.319, shell.

**Spec:** `docs/superpowers/specs/2026-11-08-brechas-do-setup-design.md`

## Global Constraints

- Texto de doc, comentário e commit em pt-BR. Commit em Conventional Commits, identidade local do repo (`dv-dev1`), sem assinatura do Claude.
- Hook nunca trava nem quebra o turno: qualquer exceção sai sem imprimir.
- Teste roda com `python3 tests/<arquivo>.py`, no runner de `tests/test_varredura.py`.
- Compactação intocada: `autoCompactWindow: 550000` e `hooks/compactar.txt` ficam como estão.
- Não tocar em `skills/blackboard/mapa.md` (mudança do usuário, fora de commit).
- Fonte do acervo antigo: `benchmark/antigo/repo` em `76acf5e`. Fonte do caveman: `~/.claude/plugins/cache/caveman/caveman/4.0.1`.

## Review Focus

1. Transcript real de subagente marca toda entrada com `isSidechain: true`: edição e debug lá dentro precisam contar. Hoje o `ferramentas()` descarta essas entradas e o teste passa só porque a fixture não tem a flag (Task 1, fixture realista).
2. Debug carregado por slash command digitado no turno anterior (carga `isMeta`), edição agora: varre (Task 1).
3. Feedback de varredura no turno anterior fecha a janela: não varre duas vezes a mesma correção (Task 1).
4. `caveman.md` tem aspas, crases, travessão e quebras de linha: o JSON do `SubagentStart` continua válido (Task 2 roda o comando real).
5. `~/.claude/settings.json` com `"caveman@caveman": true`: depois do `install.sh` vira `false`, porque o merge funde dicts e o valor do repo vence (Task 5 confere).

---

### Task 1: Varredura entre turnos e dentro de subagente

**Files:**
- Modify: `hooks/varredura.py`
- Test: `tests/test_varredura.py`

**Interfaces:**
- Produces: `precisa_varrer(entradas: list[dict], caminho: str | None = None) -> bool` (mesma assinatura); `ferramentas(entrada: dict, subagente: bool = False) -> list[dict]`; `sinais(entradas: list[dict], caminho: str | None) -> tuple[bool, bool]` (debug, editou) das entradas e dos subagentes lançados nelas, que só são lidos quando há `caminho`; `sinais_do_subagente(caminho: str, agente: str) -> tuple[bool, bool]`, que substitui `subagente_editou`. `OSError` ao ler o subagente devolve `(False, False)`.

- [ ] **Step 1: Fixture realista e testes novos**

No `gravar`, cada linha de subagente ganha `"isSidechain": True`. Troque `test_debug_em_turno_anterior_nao_bloqueia` por estes e acrescente os demais:

```python
def test_correcao_no_turno_seguinte_ao_debug_bloqueia():
    assert varredura.precisa_varrer([humano("bug"), debug(), resultado(), humano("pode corrigir"), edit()]) is True

def test_debug_dois_turnos_atras_nao_bloqueia():
    assert varredura.precisa_varrer([humano("bug"), debug(), humano("e o log?"), ferramenta("Read"),
                                     humano("agora troca o texto"), edit()]) is False

def test_debug_anterior_que_ja_editou_nao_bloqueia():
    assert varredura.precisa_varrer([humano("bug"), debug(), edit(), humano("agora troca o texto"), edit()]) is False

def test_debug_anterior_por_slash_command_conta():
    comando = humano("<command-message>superpowers:systematic-debugging</command-message>\n"
                     "<command-name>/superpowers:systematic-debugging</command-name>")
    carga = meta("Base directory for this skill: /c/superpowers/7.0.1/skills/systematic-debugging\n\n# Systematic Debugging")
    assert varredura.precisa_varrer([comando, carga, humano("pode corrigir"), edit()]) is True

def test_varredura_no_turno_anterior_fecha_a_janela():
    feedback = {"type": "user", "isMeta": True, "message": {"content": "Stop hook feedback:\n" + varredura.MOTIVO}}
    assert varredura.precisa_varrer([humano("bug"), debug(), feedback, humano("e agora?"), edit()]) is False

def test_debug_e_edicao_dentro_do_subagente_bloqueia():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("corrige o bug"), *delegou("abc")], {"abc": [humano("corrige"), debug(), edit()]})
        assert varredura.precisa_varrer(varredura.ler(caminho), caminho) is True

def test_subagente_com_debug_sem_edicao_nao_bloqueia():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = gravar(pasta, [humano("investiga"), *delegou("abc")], {"abc": [humano("investiga"), debug()]})
        assert varredura.precisa_varrer(varredura.ler(caminho), caminho) is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 tests/test_varredura.py`
Expected: `FALHA` em `test_edicao_feita_por_subagente_conta`, `test_main_bloqueia_com_edicao_de_subagente` (o bug real: a flag `isSidechain`), `test_correcao_no_turno_seguinte_ao_debug_bloqueia`, `test_debug_anterior_por_slash_command_conta` e `test_debug_e_edicao_dentro_do_subagente_bloqueia`; exit 1.

- [ ] **Step 3: Implementar em `hooks/varredura.py`**

`ferramentas(entrada, subagente=False)` só descarta `isSidechain` quando `subagente` é falso. `sinais_do_subagente` lê o transcript com `ferramentas(..., subagente=True)` e procura debug (ferramenta `Skill` ou carga `isMeta`, como hoje) e edição. `precisa_varrer`:

```python
atual, anterior = [], []
alvo = atual
for entrada in reversed(entradas):
    if entrada.get("isMeta") and MOTIVO[:40] in texto(entrada):
        break  # varredura anterior fecha a janela
    if abre_turno(entrada):
        if alvo is anterior:
            break
        alvo = anterior
        continue
    alvo.append(entrada)
debug, editou = sinais(atual, caminho)        # turno + subagentes lançados nele
if editou and not debug:
    debug_ant, editou_ant = sinais(anterior, caminho)
    debug = debug_ant and not editou_ant      # debug sem correção no turno anterior: esta edição é a correção
return debug and editou
```

Atualize a docstring do módulo: o turno anterior e o subagente contam.

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 tests/test_varredura.py`
Expected: só linhas `ok`, nenhuma `FALHA`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add hooks/varredura.py tests/test_varredura.py
git commit -m "fix(varredura): conta subagente de verdade, debug dentro dele e correção no turno seguinte"
```

---

### Task 2: Caveman no modo padrão, sem plugin

**Files:**
- Create: `hooks/caveman.md`
- Modify: `settings.json` (`enabledPlugins`, `hooks.SessionStart`, `hooks.SubagentStart`, `hooks.UserPromptSubmit`)
- Test: `tests/test_setup.py` (novo, mesmo runner do `test_varredura.py`)

**Interfaces:**
- Produces: `hooks/caveman.md`, lido por `$HOME/.claude/hooks/caveman.md` depois do `install.sh`. Constante `LEMBRETE` em `tests/test_setup.py` com o texto exato do lembrete.

- [ ] **Step 1: Testes**

Helper `rodar(comando, home) -> str`: `subprocess.run(["sh", "-c", comando], env={**os.environ, "HOME": home}, capture_output=True, text=True, check=True).stdout`, com `home/.claude/hooks/caveman.md` copiado do repo. Os comandos vêm do `settings.json` do repo.

```python
LEMBRETE = ("CAVEMAN MODE ACTIVE (caveman). Respond terse like smart caveman. All technical substance stay. "
            "Only fluff die. Answer only what was asked: no unrequested background, lists, examples, walkthroughs, "
            "or follow-up offers; give code, steps, or warnings when the task needs them. Security warnings, "
            "irreversible actions, multi-step order: normal prose. Technical terms, code, commands, paths, "
            "and errors stay exact.")

def test_caveman_plugin_desligado():            # settings["enabledPlugins"]["caveman@caveman"] is False
def test_sessionstart_imprime_o_caveman():      # saída do comando == conteúdo de hooks/caveman.md
def test_subagentstart_emite_json_do_caveman(): # json.loads(saída)["hookSpecificOutput"] == {"hookEventName": "SubagentStart", "additionalContext": conteúdo}
def test_lembrete_caveman_por_mensagem():       # algum comando de UserPromptSubmit emite additionalContext == LEMBRETE
def test_caveman_md_sem_troca_de_modo():        # contém "CAVEMAN MODE ACTIVE — mode: caveman", "## Rules", "## Pre-send check";
                                                # não contém "ultracave", "megacave", "/caveman status", "stop caveman"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 tests/test_setup.py`
Expected: `FALHA` nos 5, exit 1.

- [ ] **Step 3: Criar `hooks/caveman.md`**

Linha 1: `<!-- Adaptado de JuliusBrussee/caveman 4.0.1 (Apache-2.0), skills/caveman/SKILL.md: sem frontmatter e sem troca de modo. -->`. Linha 2: `CAVEMAN MODE ACTIVE — mode: caveman`. Linha em branco. Depois as linhas 9–89 do `SKILL.md` do plugin, com duas mudanças: a linha 17 vira `Every response, whole session. Unsure if still on? It is.` e a linha 19 (aliases `/caveman ultra`, `/caveman wenyan` e `/caveman status`) sai junto com a linha em branco que a segue.

- [ ] **Step 4: `settings.json`**

`enabledPlugins`: `"caveman@caveman": false` (o `false` é explícito: o `install.sh` funde dicts e manteria o `true`). `extraKnownMarketplaces.caveman` fica. Hooks novos, nesta forma exata:

```json
"SessionStart": [{"hooks": [{"type": "command", "command": "cat \"$HOME/.claude/hooks/caveman.md\""}]}],
"SubagentStart": [{"hooks": [{"type": "command", "command": "python3 -c 'import json,os;print(json.dumps({\"hookSpecificOutput\":{\"hookEventName\":\"SubagentStart\",\"additionalContext\":open(os.path.expanduser(\"~/.claude/hooks/caveman.md\"),encoding=\"utf-8\").read()}}))'"}]}]
```

Em `UserPromptSubmit`, terceiro hook do grupo existente, depois do PONYTAIL: `echo '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"<LEMBRETE>"}}'`, com o texto de `LEMBRETE`.

- [ ] **Step 5: Rodar e ver passar**

Run: `python3 tests/test_setup.py && python3 -I -c 'import json;json.load(open("settings.json"))'`
Expected: só `ok`, exit 0, JSON válido.

- [ ] **Step 6: Commit**

```bash
git add hooks/caveman.md settings.json tests/test_setup.py
git commit -m "feat(caveman): modo padrão por hooks próprios, sem o plugin e suas 21 skills na lista"
```

---

### Task 3: Acervo

**Files:**
- Create: `acervo/<23 skills>/`, `acervo/caveman/<21 skills>/`, `acervo/caveman/caveman-init/SKILL.md`, `acervo/caveman/cavecrew/agents/cavecrew-{builder,investigator,reviewer}.md`, `acervo/caveman/LICENSE`, `acervo/caveman/NOTICE`
- Modify: `CLAUDE.global.md` (linha `- Acervo:`)
- Test: `tests/test_setup.py`

**Interfaces:**
- Consumes: runner e helpers de `tests/test_setup.py` (Task 2).

- [ ] **Step 1: Testes**

```python
CICLO_ANTIGO = ("ciclo", "clean-code-guard", "diagnosing-bugs", "finishing-a-development-branch",
                "open-code-review-delegate", "revisao-dois-eixos", "subagent-driven-development",
                "test-driven-development", "writing-plans")

def test_acervo_listado_no_claude_global():
    # cada pasta de acervo/ (menos "caveman") e de acervo/caveman/ tem SKILL.md e aparece como palavra inteira
    # na linha que começa com "- Acervo:" do CLAUDE.global.md: re.search(rf"(?<![\w-]){re.escape(nome)}(?![\w-])", linha)

def test_acervo_sem_caminho_de_skill_ativa():
    # nenhum arquivo de texto sob acervo/ contém "~/.claude/skills/" (ler com errors="ignore")

def test_acervo_sem_ciclo_antigo():
    # nenhum nome de CICLO_ANTIGO existe como pasta em acervo/
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 tests/test_setup.py`
Expected: `FALHA` em `test_acervo_listado_no_claude_global` (pasta não existe); exit 1.

- [ ] **Step 3: Copiar**

```bash
mkdir -p acervo/caveman/caveman-init acervo/caveman/cavecrew/agents
for n in composition-patterns consultor-financeiro do-zero entender-diff explain-project grilling impeccable \
         learning-concept livro-certo motion-design peneira pesquisa-web pick-ui-library post-linkedin \
         projeto-publico prototype react-best-practices react-view-transitions readme-padrao \
         reverse-engineer-anything web-design-guidelines writing-for-agents writing-guidelines; do
  git -C benchmark/antigo/repo archive 76acf5e "skills/$n" | tar -x -C acervo --strip-components=1
done
P="$HOME/.claude/plugins/cache/caveman/caveman/4.0.1"
for n in cavecrew caveman-commit caveman-compress caveman-discover caveman-evidence-review caveman-explore \
         caveman-help caveman-learn caveman-manage caveman-optimize caveman-review caveman-setup caveman-stats \
         investigate-first lean-build megacave migration safe-refactor surgical-patch ultracave verify-and-stop; do
  cp -R "$P/skills/$n" acervo/caveman/
done
cp "$P/commands/caveman-init.md" acervo/caveman/caveman-init/SKILL.md
cp "$P"/agents/cavecrew-*.md acervo/caveman/cavecrew/agents/
cp "$P/LICENSE" "$P/NOTICE" acervo/caveman/
grep -rl '~/.claude/skills/' acervo | xargs sed -i '' 's|~/\.claude/skills/|~/new-claude-setup/acervo/|g'
```

- [ ] **Step 4: Linha do acervo no `CLAUDE.global.md`**

Substitui a linha `- Acervo:` atual por esta, numa linha só:

`- Acervo: skills fora da lista, lidas sob demanda: se a tarefa pedir uma, leia o `SKILL.md` dela (a pasta dela é o base directory). `~/new-claude-setup/acervo/<nome>/`: composition-patterns, consultor-financeiro, do-zero, entender-diff, explain-project, grilling, impeccable, learning-concept, livro-certo, motion-design, peneira, pesquisa-web, pick-ui-library, post-linkedin, projeto-publico, prototype, react-best-practices, react-view-transitions, readme-padrao, reverse-engineer-anything, web-design-guidelines, writing-for-agents, writing-guidelines. `~/new-claude-setup/acervo/caveman/<nome>/` (as que chamam script do plugin caveman não rodam sem ele): cavecrew, caveman-commit, caveman-compress, caveman-discover, caveman-evidence-review, caveman-explore, caveman-help, caveman-init, caveman-learn, caveman-manage, caveman-optimize, caveman-review, caveman-setup, caveman-stats, investigate-first, lean-build, megacave, migration, safe-refactor, surgical-patch, ultracave, verify-and-stop. `~/.claude/skills/synced/*/<nome>/`: morning, import-memory, google-workspace, built-in-browser, computer-use.`

- [ ] **Step 5: Rodar e ver passar**

Run: `python3 tests/test_setup.py && ls acervo | wc -l && ls acervo/caveman | wc -l`
Expected: só `ok`, exit 0; `24` (23 skills + `caveman`); `24` (22 pastas + `LICENSE` + `NOTICE`).

- [ ] **Step 6: Commit**

```bash
git add acervo CLAUDE.global.md tests/test_setup.py
git commit -m "feat(acervo): skills do setup antigo e extras do caveman fora da lista, indexadas no CLAUDE global"
```

---

### Task 4: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Atualizar linhas da tabela**

`settings.json`: cita os hooks `SessionStart`/`SubagentStart` do caveman. `acervo`: pasta `acervo/` (23 do setup antigo, 22 do caveman) e as 5 do claude.ai, índice no `CLAUDE.global.md`. `hooks/varredura.py`: conta debug do turno anterior e de subagente. Nova linha `hooks/caveman.md`: estilo caveman no modo padrão, sem o plugin (sem troca de modo nem "stop caveman"). Linha do plugin `caveman` sai. Nova linha `tests/test_setup.py`: `python3 tests/test_setup.py`.

- [ ] **Step 2: Rodar tudo**

Run: `python3 tests/test_varredura.py && python3 tests/test_setup.py`
Expected: só `ok`, exit 0.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): caveman por hooks, acervo e varredura entre turnos"
```

---

### Task 5: Instalar e conferir (depois do merge na `main`, em `~/new-claude-setup`)

- [ ] **Step 1:** `bash install.sh` → exit 0.
- [ ] **Step 2:** `python3 -I -c 'import json;s=json.load(open("/Users/dvdev/.claude/settings.json"));print(s["enabledPlugins"]["caveman@caveman"], sorted(s["hooks"]))'` → `False [...'PreCompact', 'PreToolUse', 'SessionStart', 'Stop', 'SubagentStart', 'UserPromptSubmit']`; `ls -la ~/.claude/hooks/caveman.md` → symlink para o repo.
- [ ] **Step 3:** Sessão nova sem interação: `env -u CLAUDECODE claude -p --model haiku "Liste os nomes exatos das skills da sua lista que comecem com 'caveman:' ou contenham 'surgical-patch'. Se nenhuma, escreva NENHUMA."` → `NENHUMA`. E `env -u CLAUDECODE claude -p --model haiku "Responda só SIM ou NAO: seu contexto tem a linha 'CAVEMAN MODE ACTIVE — mode: caveman'?"` → `SIM`.
