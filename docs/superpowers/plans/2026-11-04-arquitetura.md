# Arquitetura antes de codar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Skill `arquitetura` que faz projeto novo e feature com porta de mão única pararem para a escolha do usuário e registrarem a decisão.

**Architecture:** Skill pessoal em `skills/arquitetura/`, ligada ao `~/.claude` pelo `install.sh`. Uma linha no `CLAUDE.global.md` e no lembrete `UserPromptSubmit` garante o disparo. O plugin superpowers e os lembretes passam a morar no `settings.json` do repo.

**Tech Stack:** Markdown (skill), JSON (settings), bash (`install.sh`), harness de benchmark em `/private/tmp/claude-501/-Users-dvdev/9d0cd299-38ea-4156-b8b3-955c8cc18fd4/scratchpad/ab`.

**Spec:** `docs/superpowers/specs/2026-11-04-arquitetura-design.md`

## Global Constraints

- Texto da skill e das regras em pt-BR.
- Commit com a identidade do `origin` (`dv-dev1 <196990984+dv-dev1@users.noreply.github.com>`), sem assinatura do Claude; sem push até o usuário pedir.
- Não incluir nos commits `skills/blackboard/mapa.md` nem `skills/curriculo-camaleao/references/candidato.md` (mudanças do usuário).
- Não editar nada em `~/.claude/plugins/cache`.
- `CLAUDE.global.md` e o lembrete do hook ganham uma linha cada, não mais.

## Review Focus

1. Bug, rename ou ajuste sem decisão de arquitetura: não para (anti-objetivo). Teste: T1 ×2 na Task 3.
2. Usuário responde "passa" à escolha: segue com a recomendação e registra igual. Teste: T4 ×2 na Task 3 (o harness responde "passa").
3. Pedido que já traz a opção ("usa cron do systemd"): não pergunta de novo, só registra. Teste: grep na Task 1.
4. Repo com `docs/adr/`: segue a convenção dele. Teste: grep na Task 1.
5. Repo sem git ou sem commit pedido: o `ARQUITETURA.md` é escrito mesmo assim. Teste: grep na Task 1.

---

### Task 1: Skill `arquitetura`

**Files:**
- Create: `skills/arquitetura/SKILL.md`

**Interfaces:**
- Produces: skill `arquitetura` (nome no frontmatter), lida pelas regras da Task 2.

- [ ] **Step 1: Escrever `skills/arquitetura/SKILL.md`**

Frontmatter: `name: arquitetura`; `description` com os gatilhos "projeto novo" e "feature com decisão cara de desfazer (modelo de dado, contrato externo, auth, serviço pago, síncrono × assíncrono, deploy)", e "não use em bug, rename ou ajuste".

Seções, partindo da seção Arquitetura da `ciclo` antiga (`/private/tmp/claude-501/-Users-dvdev/9d0cd299-38ea-4156-b8b3-955c8cc18fd4/scratchpad/antigo/repo/skills/ciclo/SKILL.md`) com as peças do design:
- **Quando:** porta de mão única pela lista acima; registrar só se for difícil de reverter, surpreender sem contexto e vier de trade-off real (domain-modeling). Bug, rename e ajuste: não usar.
- **ARQUITETURA.md:** Forças (2 a 4 atributos em ordem, cada um com número), Forma (3 a 6 linhas), Decisões `| data | decisão | alternativas | por quê | revisitar quando |`. Repo sem o arquivo: rascunho pelo código, specs e `git log`, com `?`. Repo com `docs/adr/`: seguir a convenção dele.
- **Projeto novo:** estimativa com número (usuários, requisições/dia, volume de dados) entra nas Forças; o `ARQUITETURA.md` vai dentro do design doc do brainstorming.
- **A parada:** tabela opção × forças, com colunas complexidade, custo, escala e familiaridade, mais consequência ("fica mais fácil / mais difícil"); sem recomendar; termina em "Sua escolha e o porquê?" e para, sem agir antes da resposta (grilling). Pedido que já traz a opção: não pergunta, só registra. Depois da escolha: recomendação; se diferem, até 3 linhas do que muda e o usuário decide. "passa": segue com a recomendação.
- **Registro:** linha nas Decisões no mesmo commit da feature; commit (sem push) com `Por quê:`, `Recusado:` e `Olhe:`. Sem git: o arquivo é escrito mesmo assim.

- [ ] **Step 2: Conferir os casos do Review Focus no texto**

Run: `cd ~/new-claude-setup && for p in 'passa' 'docs/adr' 'já traz' 'sem git' 'revisitar quando' 'Sua escolha e o porquê' 'Recusado:'; do grep -q "$p" skills/arquitetura/SKILL.md && echo "ok $p" || echo "FALTA $p"; done`
Expected: 7 linhas `ok`.

- [ ] **Step 3: Commit**

```bash
git add skills/arquitetura/SKILL.md docs/superpowers/specs/2026-11-04-arquitetura-design.md docs/superpowers/plans/2026-11-04-arquitetura.md
git commit -m "feat(arquitetura): skill que para na decisão cara de desfazer e registra no ARQUITETURA.md"
```

### Task 2: Regra de disparo e settings versionado

**Files:**
- Modify: `CLAUDE.global.md` (linha nova depois da linha do Superpowers)
- Modify: `settings.json` (adicionar `extraKnownMarketplaces.superpowers-marketplace`, `enabledPlugins."superpowers@superpowers-marketplace": true`, `hooks.UserPromptSubmit` com os dois lembretes de hoje)
- Modify: `README.md` (linhas da skill `arquitetura` e do plugin superpowers na tabela)

**Interfaces:**
- Consumes: skill `arquitetura` (Task 1).

- [ ] **Step 1: Linha no `CLAUDE.global.md`**

Texto: `- Projeto novo e feature com decisão cara de desfazer passam pela skill arquitetura antes de qualquer código: parar com as opções e esperar a escolha.`

- [ ] **Step 2: `settings.json` do repo**

Copiar do `~/.claude/settings.json` atual o bloco `hooks.UserPromptSubmit` (lembretes SUPERPOWERS e PONYTAIL), o marketplace e o plugin. No lembrete SUPERPOWERS, acrescentar antes de "Caveman/Ponytail": `Projeto novo ou decisao cara de desfazer: skill arquitetura antes de codar.` O comando continua um `echo` com uma só aspa simples de cada lado.

- [ ] **Step 3: Validar o JSON e o hook**

Run: `cd ~/new-claude-setup && python3 -m json.tool settings.json >/dev/null && bash -c "$(python3 -c "import json;print(json.load(open('settings.json'))['hooks']['UserPromptSubmit'][0]['hooks'][0]['command'])")" | python3 -c "import json,sys;t=json.load(sys.stdin)['hookSpecificOutput']['additionalContext'];assert 'arquitetura' in t;print('ok')"`
Expected: `ok`

- [ ] **Step 4: Instalar e conferir numa sessão nova**

Run: `bash install.sh && ls -l ~/.claude/skills/arquitetura && cd "$(mktemp -d)" && claude -p "diga só ok" --output-format stream-json --verbose 2>/dev/null | grep -o '"arquitetura"' | head -1`
Expected: o symlink para `~/new-claude-setup/skills/arquitetura` e `"arquitetura"` na lista de skills.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.global.md settings.json README.md
git commit -m "feat(setup): regra de disparo da skill arquitetura e superpowers versionado"
```

### Task 3: Validação no benchmark

**Files:** nenhum no repo; saídas em `.../scratchpad/ab/out/`.

**Interfaces:**
- Consumes: setup instalado (Task 2); `run-one.sh` condição `H` (setup ao vivo, `--effort high`, bypass); `juiz-pacote.py`.

- [ ] **Step 1: Rodar T4 ×2 e T1 ×2**

Run: `MAX=2 bash .../ab/run-all.sh valida t4-H-4 t4-H-5 t1-H-4 t1-H-5`
Expected: `fim do lote valida`.

- [ ] **Step 2: Conferir os critérios**

Run: `python3 -I .../ab/grade.py t4-H-4 t4-H-5 t1-H-4 t1-H-5`, depois ler `nota.json` de cada.
Expected: T4: `sessoes` 2 (parou), `ARQUITETURA.md` em `docs_alterados` e `Recusado:` em `mensagens`, nas 2. T1: `sessoes` 1 e gabarito 12/12, nas 2.

- [ ] **Step 3: Juiz cego na mesma rodada**

Pacote com `t4-H-4 t4-H-5 t4-V-1 t4-V-2` (antigo de referência), sementes 7 e 13, `ponytail:` trocado por `shortcut:`; dois juízes com o prompt de 04/11.
Expected: média do atual a até 1 ponto do antigo.

- [ ] **Step 4: Limpar**

Mover `~/.claude/projects/*scratchpad-w-*` para `.../scratchpad/transcripts/`; conferir que `~/estudos/REVISAO.md` não mudou.
