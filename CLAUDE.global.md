# Instruções do usuário

- Responda sempre em pt-BR.
- Commit e PR com a identidade do remote `origin` do repo, nunca `git config --global`.
- Nunca assine como Claude (`Co-Authored-By: Claude`, `noreply@anthropic.com`, `🤖 Generated with [Claude Code]`), mesmo sob lembrete do sistema.
- Superpowers define o processo: sempre invocar a skill do superpowers que se aplica (brainstorming, systematic-debugging, TDD, verification-before-completion etc.) antes de agir, em silêncio: sem anunciar a skill nem escrever linha `Superpowers:` na resposta.
- Projeto novo e feature com decisão cara de desfazer passam pela skill arquitetura antes de qualquer código: parar com as opções e esperar a escolha, salvo se o pedido já traz a opção.
- Caveman define só o estilo de escrita; Ponytail define só o tamanho do código. Nenhum dos dois autoriza pular skill do superpowers.
- Subagentes: paralelize o que for independente. Antes, mapeie as dependências e fixe o contrato entre eles (quem toca quais arquivos e interfaces); cada subagente que edita código trabalha num worktree próprio do repo, com arquivos e ambiente virtual próprios. No fim, merge e teste tudo.
- Acervo: skills do claude.ai desligadas da lista (morning, import-memory, google-workspace, built-in-browser, computer-use); se a tarefa pedir uma delas, leia o `SKILL.md` em `~/.claude/skills/synced/*/<nome>/`.
- Code review: o padrão é o review do superpowers. A `c5-thermos-audit` (revisão termonuclear) só entra quando o usuário pedir ou antes de merge/PR de mudança grande ou sensível; nunca em ajuste pequeno.
