# Corte de overhead: só o desperdício medido sai

Data: 2026-11-11. Origem: o limite de 5 h estourou em ~2 h com 3 sessões em paralelo; a medição desta data separou o que é desperdício do que traz benefício.

## Intenção

Gastar menos token sem perder qualidade. Sai só o que a medição mostrou que é desperdício. O que tem benefício medido fica. O que dá para otimizar sem perda, otimiza.

## Medição (base das decisões)

Fonte: 732 subagentes do histórico, os transcripts desde 2026-11-08 e 7 chamadas `claude -p` em Haiku, ligando e desligando uma peça por vez.

- Os lembretes do `UserPromptSubmit` disparam também em `<task-notification>`. No jarvis, 105 das 135 injeções (78%) vieram de aviso de subagente, não de prompt humano.
- A lista de skills ocupa 20,5 KB (53 skills). ~7,6 KB são de skills com 0 uso pelo modelo desde 2026-11-08.
- Conectores claude.ai: Gmail e Calendar com 0 uso no histórico inteiro; Claude Docs com 2. O Drive (31 usos) fica.
- Esforço: o benchmark de 2026-11-04 deu o mesmo acerto em `high` e `xhigh`, com o `xhigh` 32% mais caro (US$ 9,72 contra US$ 6,65).
- Re-review: Opus achou problema novo em 29% (14/48) e Sonnet também em 29% (15/52). O custo médio é de 1,18M tokens por agente no Opus contra 0,25M no Sonnet. O Haiku deu 12/12 "limpo", o que indica que ele não acha nada.
- Rodadas de re-review: a 2ª ainda achou problema em 3 de 10; a 3ª achou em 0 de 2.
- Benéfico, fica:
  - review inicial: achou problema em 37% das tarefas (75/202);
  - revisor Opus: acha mais que o Sonnet (46% contra 33%);
  - revisão final em Opus: bloqueante em 20 de 31;
  - Thermos Alpha: achou bug real depois da revisão final em 3 de 4 (path traversal, dedupe de parcela, injeção por encaminhamento);
  - Thermos Beta: sem bug achado, mas com ganho de manutenção.
- Compactação:
  - frequência: 14 automáticas desde 2026-11-08, todas em ~515k;
  - tamanho: resumo de 13–30 mil caracteres; o contexto volta com 77–163k;
  - cobertura: 95% dos arquivos editados (79/83) e 79% dos SHAs citados (41/52);
  - volume: 71% dos tokens das sessões principais vêm de chamadas com mais de 250k de contexto;
  - perda provável: em 2026-11-09, no jarvis, logo após a compactação, o modelo disse "nenhum CSV" e o usuário respondeu "Não já te mandei".

## O que entra

1. **Lembretes só em prompt humano.** Os 3 hooks `echo` do `UserPromptSubmit` viram um script (`hooks/lembretes.py`). Ele lê o JSON da entrada e não imprime nada quando o `prompt` começa com `<task-notification>`; também ignora os outros prefixos não humanos do `varredura.py`. Em prompt humano, injeta os mesmos 3 textos, palavra por palavra.
2. **Skills sem uso fora do contexto do modelo.** Usar `skillOverrides: "user-invocable-only"`: a skill some da lista do modelo, mas `/nome` continua funcionando. Entram:
   - `code-review`, `simplify`, `loop`, `schedule`, `init`, `security-review`;
   - `fewer-permission-prompts`, `keybindings-help`, `plugin-authoring`, `run`;
   - `anthropic-skills:skill-creator`, `anthropic-skills:docs`, `anthropic-skills:docx`, `anthropic-skills:pptx`;
   - `ponytail:ponytail-help`, `ponytail:ponytail-gain`, `ponytail:ponytail-debt`, `ponytail:ponytail-review`;
   - `superpowers:using-superpowers`, cujo texto inteiro o hook já injeta.

   Testado em 2026-11-11 na 2.1.322: o `skillOverrides` esconde skills nativas e da conta, mas não esconde skills de plugin. Por isso as 5 de plugin (`ponytail:*` e `superpowers:using-superpowers`) saem deste item, e ficam 14 skills.
3. **Conectores sem uso negados no Claude Code:** Gmail, Google Calendar e Claude Docs, via `permissions.deny` (`mcp__claude_ai_Gmail`, `mcp__claude_ai_Google_Calendar`, `mcp__claude_ai_Claude_Docs`). Testado em 2026-11-11: o Drive fica e os outros saem. O `disableClaudeAiConnectors` foi descartado porque derruba o Drive. O `disabledMcpServers` foi descartado porque vale só por projeto.
4. **Esforço `high`** no Opus 5.5 e no Sonnet 5.5; o Fable continua em `medium`. O implementador padrão continua sendo o Opus 5.5, agora em `high` (decisão do usuário).
5. **Regra de re-review no `CLAUDE.global.md`:**
   - re-review de rodada de correção roda em Sonnet, nunca em Haiku;
   - no máximo 2 rodadas; depois disso, para e chama o usuário;
   - review inicial, revisão final e thermos continuam em Opus.
6. **Compactação em 350k** (`autoCompactWindow: 350000`, hoje 550000).
7. **`hooks/compactar.txt` mais forte para compactações repetidas.** Entram estas linhas:
   - os dados que o usuário já entregou (arquivos, caminhos, dados colados, respostas) e onde estão; nunca pedir de novo;
   - as 3 últimas mensagens do usuário, palavra por palavra;
   - as fontes de verdade no disco (plano, spec, ledger, relatórios) e o passo atual da skill ativa; apontar para elas e relê-las antes de retomar;
   - os subagentes e tarefas em segundo plano em andamento: ID, o que fazem e o que fazer quando terminarem;
   - se já existe resumo anterior, levar adiante as instruções e preferências do usuário e os itens PENDING dele, sem mudança, salvo os resolvidos;
   - antes de fechar o resumo, reler cada mensagem do usuário desde o resumo anterior e confirmar que cada instrução, correção e dado entregue aparece.
8. **Repo e local alinhados.** Hoje o local tem `sonnet: xhigh` e `fable: medium` em `modelSettings`, e o repo não. O `settings.json` do repo passa a ser a fonte, e o `install.sh` aplica no local.
9. **Medição de cobertura da compactação no repo.** Um script em `benchmark/` mede, nos resumos de compactação desde uma data, quanto dos arquivos editados e dos SHAs citados foi preservado. Ele roda daqui a ~1 semana e compara com a base: 95% dos arquivos e 79% dos SHAs. Se piorar, a compactação volta para 550k.
10. **README** atualizado nos itens que mudam.

## Fora

- Não muda o plugin superpowers nem os prompts dele.
- O thermos fica como está (Alpha e Beta).
- O modelo do review inicial e da revisão final não muda.
- Não muda o caveman nos subagentes, o `varredura.py`, os hooks de SessionStart nem o `CLAUDE.md` além da regra do item 5.

## Abordagens consideradas

- O que cortar:
  - A, só os cortes medidos (escolhida);
  - B, A mais compactação menor (entrou depois, com a instrução reforçada);
  - C, A mais Sonnet como implementador padrão (recusada: o usuário mantém o Opus 5.5, agora em `high`).
- Validação da compactação:
  - medir de graça os resumos reais depois de uma semana (escolhida);
  - teste A/B com 2 transcripts reais antes de aplicar (recusado: custaria ~1M tokens, a instrução atual já preserva 95% e a mudança volta com uma linha).
- Limite da compactação:
  - 350k (escolhido): estimativa de ~26% menos tokens por chamada na sessão principal, com ~1,7x mais compactações;
  - 300k: ~34% menos tokens, com ~2,2x mais compactações. Fica para depois da medição.

## Para quem constrói

- A ordem dos commits.
- O nome do script de cobertura.
- O formato do teste de `hooks/lembretes.py` em `tests/test_setup.py`, seguindo o padrão do arquivo.
