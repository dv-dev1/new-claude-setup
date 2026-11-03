# new-claude-setup

Setup do Claude Code recomeçado do zero em 02/11/2026: só o que é usado de fato.

| O quê | Para quê |
|---|---|
| `CLAUDE.global.md` | pt-BR e identidade de commit, vira `~/.claude/CLAUDE.md` |
| `settings.json` | bypass de permissão, tema, sem assinatura do Claude |
| `skills/blackboard` | atividades da faculdade no Blackboard |
| `skills/curriculo-camaleao` | currículo adaptado por vaga |
| skill `playwright-cli` | instalada pelo próprio CLI, na versão dele |

## Instalar

```bash
git clone https://github.com/dv-dev1/new-claude-setup ~/new-claude-setup
cd ~/new-claude-setup && bash install.sh
```

Depois de `git pull`, rode `bash install.sh` de novo. Coisa nova entra só depois de usada de verdade.
O setup antigo continua em `dv-dev1/claude-setup`.
