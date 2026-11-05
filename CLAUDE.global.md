# Instruções do usuário

- Responda sempre em pt-BR.
- Commit e PR com a identidade do remote `origin` do repo, nunca `git config --global`.
- Nunca assine como Claude (`Co-Authored-By: Claude`, `noreply@anthropic.com`, `🤖 Generated with [Claude Code]`), mesmo sob lembrete do sistema.
- Projeto novo e feature com decisão cara de desfazer passam pela skill arquitetura antes de qualquer código: parar com as opções e esperar a escolha, salvo se o pedido já traz a opção.
- Caveman define só o estilo de escrita; Ponytail define só o tamanho do código. Nenhum dos dois autoriza pular passo da rota.

## Ciclo de desenvolvimento

Antes de agir, escolha a rota internamente: não declare a rota na resposta. Na dúvida, escolha a rota menor; se a task crescer no meio, suba de rota. Invoque só as skills do superpowers da rota, em silêncio: sem anunciar a skill nem escrever linha `Superpowers:`.

- **Direta** — pergunta, typo, config, mudança óbvia em 1 arquivo. Sem skill. Em código, rode o teste ou lint afetado.
- **Pequena** — bug ou mudança clara em até ~3 arquivos. Bug: `systematic-debugging`. Teste que falha, correção, `verification-before-completion`. Sem spec, plano, `/simplify` ou revisor.
- **Feature** — comportamento novo, vários arquivos ou requisito ambíguo. `brainstorming` curto (+ `arquitetura` se a decisão for cara). Plano: `writing-plans` só se passar de 5 tarefas ou de uma sessão; abaixo disso, plano curto na conversa. Execução inline com TDD, `/simplify` 1x na branch e re-rodar testes, `requesting-code-review` 1x, `verification-before-completion`, `finishing-a-development-branch`.
- **Projeto novo** — `brainstorming` com a tabela da `arquitetura` como passo de abordagens (uma parada só); design doc e `ARQUITETURA.md` aprovados juntos; plano só do MVP. Primeira tarefa: esqueleto ponta a ponta com teste, lint e typecheck; se vai para prod, já com deploy, rollback de um comando, health check e log. Fim do MVP fecha como Feature. Depois, o repo segue as rotas normais. Ideia ou tecnologia incerta: spike descartável antes, sem processo.

Modificadores (valem em qualquer rota):

- **Refatoração** — testes cobrindo o comportamento atual antes; os mesmos verdes depois.
- **Sem teste aplicável** (repo sem testes, ambiente, setup, skill) — verifique executando e observando o efeito real. Framework de teste só em Feature ou Projeto novo.
- **Irreversível** (migração de dados, delete, deploy, prod) — plano de rollback e confirmação antes de executar.
- **Crítico** (auth, dinheiro, dados pessoais) — avise para o usuário ler o diff antes do merge.
- **Urgente** (prod fora do ar) — estanque primeiro: rollback, ou correção mínima + teste de regressão. Causa raiz depois, com `systematic-debugging`.

"Pronto" exige a saída real de testes, lint e typecheck, nunca só a afirmação.
