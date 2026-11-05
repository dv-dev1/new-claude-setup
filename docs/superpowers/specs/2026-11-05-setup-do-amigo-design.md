# Setup do amigo: varredura, compactação, orçamento de skills e acervo

Data: 2026-11-05. Origem: dois áudios de um colega explicando o setup dele do Claude Code.

## Intenção

Aplicar no `new-claude-setup` o que o colega recomendou, sem trazer de volta o excesso que o recomeço de 02/11 tirou.

## O que entra

1. **Hook de varredura** (`Stop`, `hooks/varredura.py`). Dispara quando o turno rodou `superpowers:systematic-debugging` (pela ferramenta ou digitado como slash command) e editou arquivo (`Edit`, `Write`, `MultiEdit`, `NotebookEdit`), direto ou por subagente. Compactação no meio do turno não perde o debug. Bloqueia uma vez (respeita `stop_hook_active`) e manda o Claude varrer o repo inteiro a partir da raiz atrás de outras ocorrências do bug, com variações de busca, e informar a contagem final.
2. **Instrução de compactação** (`PreCompact`, sem matcher: manual, auto e idle). Um hook imprime `hooks/compactar.txt`, o prompt do colega íntegro (999 caracteres). O Claude Code aceita até 10.000 caracteres por saída de `PreCompact`.
3. **Janela de compactação**: `autoCompactWindow: 550000`, 55% da janela (o colega sugeriu 600k; o usuário ajustou para 55%). O Opus 5.5 tem 1M nativo. `idleCompaction` já vem ligado.
4. **Orçamento da lista de skills**: `skillListingBudgetFraction: 0.03`. O padrão é `0.01`, 1% da janela.
5. **Acervo**: `skillOverrides: "off"` para 5 skills do claude.ai sem uso (`morning`, `import-memory`, `google-workspace`, `built-in-browser`, `computer-use`). Os extras do caveman e do ponytail ficaram de fora: o Claude Code 2.1.318 ignora `skillOverrides` em skill de plugin de terceiros. Uma linha no `CLAUDE.global.md` aponta onde ler o `SKILL.md` delas sob demanda.
6. **Subagentes**: uma linha no `CLAUDE.global.md`. Paralelizar o que for independente depois de mapear dependências, com contrato entre eles, cada um no próprio worktree, e no fim merge e teste de tudo.

7. **Output style padrão**: `outputStyle: "default"` no `settings.json` e o `outputStyle: "Concise"` sai do `~/.claude/settings.local.json`. Caveman (`caveman`) e ponytail (`full`) já estão no modo padrão e ficam como estão.

8. **Code review termonuclear**: `skills/c5-thermos-audit` (do colega), com descrição que restringe o uso a pedido explícito ou merge/PR de mudança grande ou sensível, e uma linha no `CLAUDE.global.md`.

## Fora

- Skills do setup antigo no acervo: não escolhidas.

## Abordagens consideradas

- Varredura: só em turno com debugging e edição (escolhida, sem ruído). Alternativas: toda edição, com uma rodada extra por turno; subagente revisor, mais isento, mas lento e caro.
- Compactação: um hook com o texto íntegro. A escolha inicial foi um resumo de 500 caracteres, por um limite lido errado no binário; a revisão final achou o limite real (10.000) e o texto voltou íntegro. Alternativa descartada: seção no `CLAUDE.md`, que custa tokens todo turno.
- Acervo: `skillOverrides` com índice no `CLAUDE.md`. Mover os arquivos não funciona, porque a atualização do plugin restaura a pasta.

## Limites conhecidos

- Varredura não vê edição feita por `Bash` (`sed -i`, heredoc), nem debugging que começou num turno e editou em outro.
