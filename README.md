# new-claude-setup

Setup do Claude Code recomeçado do zero em 02/11/2026: só o que é usado de fato.

| O quê | Para quê |
|---|---|
| `CLAUDE.global.md` | pt-BR, identidade de commit, sem assinatura, superpowers em silêncio, skill arquitetura, regra de subagentes (contrato e worktree por subagente), regra de re-review e índice do acervo; vira `~/.claude/CLAUDE.md` |
| `settings.json` | igual ao `~/.claude/settings.json`: bypass, Opus 5.5 e Sonnet 5.5 em high (Fable em medium), agent teams, plugins (superpowers e ponytail; caveman desligado), lembretes `UserPromptSubmit`, caveman por hook (`SessionStart` e `SubagentStart`), output style padrão, compactação automática em 350k, 35% da janela (`autoCompactWindow`), conectores Gmail, Calendar e Claude Docs negados (`permissions.deny`), 14 skills sem uso escondidas do modelo (`skillOverrides: "user-invocable-only"`, `/nome` funciona), lista de skills com 3% da janela (`skillListingBudgetFraction`, padrão 1%), statusline, tema, sem assinatura do Claude |
| `acervo/` | skills fora da lista, lidas sob demanda: 23 do setup antigo (sem o ciclo de dev, que é do superpowers) e, em `acervo/caveman/`, as 22 extras do caveman com a licença; mais 5 do claude.ai desligadas por `skillOverrides: "off"`. Uma linha do `CLAUDE.global.md` lista tudo e diz onde ler o `SKILL.md`. O `install.sh` só liga `skills/*`, então nada disso entra na lista. Skill de plugin de terceiros não aceita `skillOverrides` (testado na 2.1.319): só sai desligando o plugin |
| `hooks/varredura.py` | `Stop`: turno que rodou systematic-debugging e editou arquivo volta uma vez para varrer o repo inteiro, da raiz, atrás de outras ocorrências do bug. Conta também debug e edição feitos por subagente e a correção que vem no turno seguinte ao debug ("pode corrigir") |
| `hooks/compactar.txt` | `PreCompact` (manual, auto e idle): prompt de compactação do colega com acréscimos: fala do usuário, último pedido, verificação, estado externo, nada de segredo, dados já entregues, últimas 3 falas, fontes de verdade no disco, trabalho em andamento, herança do resumo anterior e checagem final (o Claude Code aceita até 10.000 caracteres por hook) |
| `tests/test_varredura.py` | testes do hook de varredura e do tamanho do texto de compactação: `python3 tests/test_varredura.py` |
| `tests/test_setup.py` | testes dos hooks do caveman (rodam o comando real do `settings.json`) e do índice do acervo: `python3 tests/test_setup.py` |
| `hooks/sem-assinatura.py` | barra commit/PR com assinatura do Claude |
| `skills/blackboard` | atividades da faculdade no Blackboard |
| `skills/curriculo-camaleao` | currículo adaptado por vaga |
| `skills/arquitetura` | projeto novo e decisão cara de desfazer: para com as opções contra as forças, espera a escolha e registra no `ARCHITECTURE.md` (ou em `decisions/` dentro de workspace) |
| plugin `superpowers` | ciclo de engenharia (brainstorming, plano, TDD, debugging, verificação), com lembrete no `UserPromptSubmit` (`hooks/lembretes.py`, só em fala humana) para usar em silêncio ([obra/superpowers](https://github.com/obra/superpowers)) |
| plugin `ponytail` | dev sênior preguiçoso: menos código, sem cortar validação nem teste ([DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)); o Claude Code instala sozinho via `settings.json` |
| `hooks/caveman.md` | respostas curtas no modo padrão do caveman, o que o colega usa: a skill do [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) 4.0.1 (Apache-2.0) sem a troca de modo, injetada por hook no início da sessão e de cada subagente. Sem o plugin, as 21 skills dele saem da lista; sem troca de modo nem "stop caveman" |
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
