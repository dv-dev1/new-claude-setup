# Setup do amigo: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar no `new-claude-setup` o hook de varredura, a instrução de compactação, a janela de 550k, o orçamento de skills em 3%, o acervo, a regra de subagentes e o output style padrão.

**Architecture:** Tudo vive no repo e chega ao `~/.claude` pelo `install.sh`, que liga `hooks/*` por symlink e funde o `settings.json` por chave. Um hook novo em Python (`Stop`), um texto lido por `cat` (`PreCompact`) e chaves novas no `settings.json`.

**Tech Stack:** Python 3 só com a biblioteca padrão, JSON de settings do Claude Code 2.1.318, bash.

**Spec:** `docs/superpowers/specs/2026-11-05-setup-do-amigo-design.md`

## Global Constraints

- Texto que fica no repo (código, comentário, docs, commit) em pt-BR, sem assinatura do Claude.
- Commit com a identidade do `origin` (`dv-dev1`), nunca `git config --global`.
- Saída de cada hook `PreCompact`: no máximo 10.000 caracteres (limite do Claude Code, `kHe=1e4`). A primeira versão deste plano dizia 500, leitura errada do binário.
- `autoCompactWindow`: `550000` (55% da janela de 1M; começou em `600000`). `skillListingBudgetFraction`: `0.03`. `outputStyle`: `"default"`.
- O `install.sh` não apaga chave do `~/.claude/settings.json`: toda mudança precisa de valor explícito no repo.

## Review Focus

- Transcript ausente, vazio ou com linha quebrada: o hook de varredura sai com 0 e não imprime nada.
- `stop_hook_active: true`: o hook não bloqueia de novo (evita laço).
- `systematic-debugging` rodou num turno anterior, não no atual: não bloqueia.
- Debugging sem edição (só diagnóstico): não bloqueia.
- `hooks/compactar.txt` com mais de 10.000 caracteres: seria cortado; o teste fixa o tamanho.

---

### Task 1: Hook de varredura

**Files:**
- Create: `hooks/varredura.py`
- Test: `tests/test_varredura.py`

**Interfaces:**
- Produces: `precisa_varrer(entradas: list[dict], caminho: str | None = None) -> bool` (o `caminho` do transcript acha os subagentes) e `main()`, que lê o JSON do `Stop` no stdin (`transcript_path`, `stop_hook_active`) e imprime `{"decision": "block", "reason": MOTIVO}` ou nada.

- [ ] **Step 1: Escrever os testes**, rodáveis com `python3 tests/test_varredura.py` (asserts, sem pytest), importando `hooks/varredura.py` por caminho. Transcript fake em JSONL com entradas `{"type": "user"|"assistant", "message": {"content": ...}}`:
  - `test_debug_e_edicao_no_turno_bloqueia`: prompt humano, `Skill` com `{"skill": "superpowers:systematic-debugging"}`, `Edit` → `precisa_varrer` é `True`.
  - `test_debug_sem_edicao_nao_bloqueia` → `False`.
  - `test_edicao_sem_debug_nao_bloqueia` → `False`.
  - `test_debug_em_turno_anterior_nao_bloqueia`: debugging antes do último prompt humano, `Edit` depois → `False`.
  - `test_tool_result_e_meta_nao_abrem_turno`: entre o `Skill` e o `Edit` vêm um `user` com `tool_result` e um `user` com `isMeta: true` → `True`.
  - `test_main_stop_hook_active_nao_imprime` e `test_main_transcript_inexistente_nao_imprime`: `main()` com stdin fake não imprime e não levanta exceção.
  - `test_main_bloqueia_imprime_json`: saída é JSON com `decision == "block"` e `"raiz" in reason`.
- [ ] **Step 2: Rodar e ver falhar.** `python3 tests/test_varredura.py` → falha por `hooks/varredura.py` inexistente.
- [ ] **Step 3: Implementar `hooks/varredura.py`.** O turno começa no último `user` que é fala humana: não `isMeta`, não `isSidechain`, não resumo de compactação (`isCompactSummary`), com texto que não comece por `<local-command-`, `<system-reminder>` ou `<task-notification>`; eco de slash command abre turno; o feedback anterior da própria varredura fecha a janela. No turno: algum `tool_use` `Skill` cujo `input.skill` termina em `systematic-debugging` (ou a carga `isMeta` "Base directory for this skill: …/systematic-debugging", que cobre o slash command digitado) e algum `tool_use` em `Edit`, `Write`, `MultiEdit` ou `NotebookEdit`, no turno ou no transcript de subagente lançado nele (`<sessão>/subagents/agent-<agentId>.jsonl`, com o `agentId` vindo do `toolUseResult`). Qualquer exceção → sai 0 sem imprimir. MOTIVO (pt-BR): varrer o repo inteiro a partir da raiz (`git rev-parse --show-toplevel`; fora de git, subir até a raiz do projeto), com `rg` sem filtro de pasta, variações (caixa, sinônimos, chamadas indiretas, `rg -uu` quando fizer sentido), corrigir o que achar e dizer a contagem final e onde buscou; se não houver mais nenhuma, dizer isso em uma linha.
- [ ] **Step 4: Rodar e ver passar.** `python3 tests/test_varredura.py` → todos passam.

### Task 2: Instrução de compactação

**Files:**
- Create: `hooks/compactar.txt`
- Test: `tests/test_varredura.py` (mesmo runner) ganha `test_compactar_cabe_no_limite_do_precompact` e `test_compactar_e_o_prompt_integral_do_colega`.

- [ ] **Step 1: Teste** `test_compactar_cabe_no_limite_do_precompact`: `len(open("hooks/compactar.txt").read().strip()) <= 10000` e o texto contém `PENDING`, `Context & Goal` e `Open Questions`.
- [ ] **Step 2: Rodar e ver falhar** (arquivo inexistente).
- [ ] **Step 3: Escrever `hooks/compactar.txt`**: o prompt do colega íntegro, em inglês, como ele mandou.
- [ ] **Step 4: Rodar e ver passar.**

### Task 3: settings, CLAUDE.global.md, README e instalação

**Files:**
- Modify: `settings.json`, `CLAUDE.global.md`, `README.md`
- Modify (fora do repo): `~/.claude/settings.local.json` (tira `outputStyle`)

- [ ] **Step 1: `settings.json`**: `autoCompactWindow: 550000`, `skillListingBudgetFraction: 0.03`, `outputStyle: "default"`; `hooks.Stop` com `python3 "$HOME/.claude/hooks/varredura.py"`; `hooks.PreCompact` sem matcher com `cat "$HOME/.claude/hooks/compactar.txt"`; `skillOverrides` com `"off"` para os 5 do claude.ai (`anthropic-skills:morning`, `import-memory`, `google-workspace`, `built-in-browser`, `computer-use`). Os extras do caveman e do ponytail ficam de fora: o Claude Code 2.1.318 ignora `skillOverrides` em skill de plugin de terceiros.
- [ ] **Step 2: `CLAUDE.global.md`**: uma linha de subagentes (mapear dependências, contrato entre eles, um worktree para cada subagente que edita código, com arquivos e venv próprios, merge e teste de tudo no fim) e uma linha de acervo (as 5 do claude.ai desligadas, ler o `SKILL.md` sob demanda em `~/.claude/skills/synced/*/<nome>/`).
- [ ] **Step 3: `README.md`**: linhas da tabela para `hooks/varredura.py`, `hooks/compactar.txt`, acervo; descrição do `settings.json` sem "output style Concise".
- [ ] **Step 4: Instalar.** `bash install.sh`; tirar `outputStyle` do `~/.claude/settings.local.json`.
- [ ] **Step 5: Verificar.** `python3 -c` confirma no `~/.claude/settings.json` as chaves da Task 3 Step 1; `~/.claude/hooks/varredura.py` e `~/.claude/hooks/compactar.txt` são symlinks válidos; `echo '{"stop_hook_active":false,"transcript_path":"/nao/existe"}' | python3 ~/.claude/hooks/varredura.py` sai 0 sem saída; `claude -p` numa sessão nova lista as skills disponíveis e nenhuma das 5 desligadas aparece.

### Task 4: Commit e push

- [ ] **Step 1:** `git add` dos arquivos das Tasks 1 a 3, spec e plano; commit em pt-BR com a identidade do `origin`, sem assinatura.
- [ ] **Step 2:** `git push origin HEAD`.
