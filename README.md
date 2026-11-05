# new-claude-setup

Setup do Claude Code recomeçado do zero em 02/11/2026: só o que é usado de fato.

| O quê | Para quê |
|---|---|
| `CLAUDE.global.md` | pt-BR, identidade de commit, sem assinatura, superpowers em silêncio, skill arquitetura, regra de subagentes (contrato e worktree por subagente) e índice do acervo; vira `~/.claude/CLAUDE.md` |
| `settings.json` | igual ao `~/.claude/settings.json`: bypass, Opus 5.5 em xhigh, agent teams, plugins, lembretes `UserPromptSubmit`, output style padrão, compactação automática em 550k, 55% da janela (`autoCompactWindow`), lista de skills com 3% da janela (`skillListingBudgetFraction`, padrão 1%), statusline, tema, sem assinatura do Claude |
| acervo | `skillOverrides: "off"` em 5 skills do claude.ai sem uso; o `CLAUDE.global.md` diz onde ler o `SKILL.md` delas sob demanda. Skill de plugin de terceiros (caveman, ponytail) não aceita `skillOverrides` no Claude Code 2.1.318: só sai desligando o plugin inteiro |
| `hooks/varredura.py` | `Stop`: turno que rodou systematic-debugging e editou arquivo volta uma vez para varrer o repo inteiro, da raiz, atrás de outras ocorrências do bug |
| `hooks/compactar.txt` | `PreCompact` (manual, auto e idle): prompt de compactação do colega com acréscimos: fala do usuário, último pedido, verificação, estado externo e nada de segredo (o Claude Code aceita até 10.000 caracteres por hook) |
| `tests/test_varredura.py` | testes do hook de varredura e do tamanho do texto de compactação: `python3 tests/test_varredura.py` |
| `hooks/sem-assinatura.py` | barra commit/PR com assinatura do Claude |
| `skills/blackboard` | atividades da faculdade no Blackboard |
| `skills/curriculo-camaleao` | currículo adaptado por vaga |
| `skills/arquitetura` | projeto novo e decisão cara de desfazer: para com as opções contra as forças, espera a escolha e registra no `ARCHITECTURE.md` (ou em `decisions/` dentro de workspace) |
| plugin `superpowers` | ciclo de engenharia (brainstorming, plano, TDD, debugging, verificação), com lembrete no `UserPromptSubmit` para usar em silêncio ([obra/superpowers](https://github.com/obra/superpowers)) |
| plugin `ponytail` | dev sênior preguiçoso: menos código, sem cortar validação nem teste ([DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)); o Claude Code instala sozinho via `settings.json` |
| plugin `caveman` | respostas curtas no modo padrão, só o plugin, sem CLI/proxy ([JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)) |
| skill `playwright-cli` | instalada pelo próprio CLI, na versão dele |
| `skills/c5-thermos-audit` | code review termonuclear do colega (2 subagentes: correção/segurança e arquitetura/Code Judo); só sob pedido ou antes de merge de mudança grande ([origem](https://github.com/borjamoskv/cortex-persist/tree/main/skills/c5-thermos-audit)) |
| `skills/agent-desktop` | apps do Mac pela árvore de acessibilidade; precisa do CLI (`npm i -g agent-desktop`) |
| `config/ccstatusline.json` | layout da statusline, vira `~/.config/ccstatusline/settings.json` |
| `benchmark/` | mede setups nas mesmas tarefas (sintéticas e bugs reais) com juiz cego; ver `benchmark/README.md` |

## Instalar

```bash
git clone https://github.com/dv-dev1/new-claude-setup ~/new-claude-setup
cd ~/new-claude-setup && bash install.sh
```

Depois de `git pull`, rode `bash install.sh` de novo. Coisa nova entra só depois de usada de verdade.
O setup antigo continua em `dv-dev1/claude-setup`.
