# Brechas do setup: caveman enxuto, acervo e varredura entre turnos

Data: 2026-11-08. Origem: comparação dos dois áudios do colega com o setup (spec de 2026-11-05).

## Intenção

Fechar as três brechas que a comparação achou: a lista de skills fica mínima, como o colega recomenda, e a varredura passa a pegar a correção de bug que hoje escapa. A compactação fica como está (550k, decisão do usuário).

## O que entra

1. **Caveman só no modo padrão, sem plugin.** O `skillOverrides` não desliga skill de plugin de terceiros na 2.1.319 (testado por settings de projeto e por flag, com nome curto e com prefixo). O plugin sai com `"caveman@caveman": false`; o `false` é explícito porque o `install.sh` funde dicts e manteria o `true` já instalado. O setup aplica o estilo com 3 hooks no `settings.json`, como o plugin faz hoje no modo padrão:
   - `SessionStart`, sem matcher (startup, resume, clear, compact): imprime `hooks/caveman.md`, o `SKILL.md` da skill `caveman` 4.0.1 sem as instruções de troca de modo.
   - `SubagentStart`: o mesmo texto como `additionalContext`.
   - `UserPromptSubmit`: o lembrete de hoje, palavra por palavra.

   Saem da lista 21 skills e 3 agentes do caveman.
2. **Acervo.** Pasta `acervo/` no repo, fora de `~/.claude/skills`: não entra na lista, porque o `install.sh` só liga `skills/*`.
   - `acervo/<nome>/`: 23 skills do setup antigo (`dv-dev1/claude-setup` em `76acf5e`). Ficam de fora as 3 já ativas e as 9 do ciclo de desenvolvimento antigo, que competem com o superpowers: `ciclo`, `clean-code-guard`, `diagnosing-bugs`, `finishing-a-development-branch`, `open-code-review-delegate`, `revisao-dois-eixos`, `subagent-driven-development`, `test-driven-development`, `writing-plans`. Caminhos `~/.claude/skills/<nome>` dentro delas passam a apontar para `~/new-claude-setup/acervo/<nome>`.
   - `acervo/caveman/`: as outras skills do caveman 4.0.1 (todas menos `caveman`), o comando `caveman-init`, os 3 agentes do `cavecrew` e `LICENSE`/`NOTICE` (Apache-2.0). As que chamam script do plugin não rodam sem ele.
   - Uma linha no `CLAUDE.global.md` substitui a do acervo atual: onde fica cada grupo e os nomes.
3. **Varredura entre turnos.** O `hooks/varredura.py` passa a disparar também quando:
   - o turno anterior rodou `systematic-debugging` sem editar e este turno editou (o "pode corrigir");
   - o `systematic-debugging` rodou dentro de um subagente lançado no turno.

   A varredura anterior continua fechando a janela. O teste que travava o caso entre turnos muda de lado.

## Fora

- Compactação: fica em 550k.
- Ponytail: os 5 extras ficam na lista. Os hooks dele fazem bem mais (band, statusline, ledger) e copiar não compensa.
- Correção sem `systematic-debugging` e edição por `Bash`: sem sinal confiável, continuam sem varredura.

## Abordagens consideradas

- Caveman: hooks próprios (escolhida); plugin copiado para o repo só com a skill principal (3.189 linhas de JS para manter na mão); deixar como está (não fecha a brecha). O usuário quer o modo padrão, que é o que o colega usa, e as outras skills do caveman no acervo. Troca de modo, estatísticas e atualização automática não fazem falta.
- Acervo: cópia no repo novo (escolhida). Apontar para um clone do repo antigo traria de volta o ciclo antigo e um segundo clone para manter.
- Varredura: janela de um turno (escolhida). Janela aberta até a próxima varredura pegaria correção 2+ turnos depois, com mais varredura à toa.

## Decisões minhas, para conferir

- O caveman no acervo fica em subpasta própria, com a licença.
- `hooks/caveman.md` perde só as linhas de troca de modo e de `/caveman status`. "stop caveman" deixa de valer: o lembrete por mensagem não sabe parar.
- Os agentes do `cavecrew` vão para o acervo junto com a skill que os usa.
