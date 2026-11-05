# Arquitetura antes de codar — design

## Intenção

O setup atual passa a projetar antes de codar. Projeto novo e feature com decisão cara de desfazer param, mostram as opções contra as forças do projeto, o usuário escolhe, e a decisão fica registrada (`ARQUITETURA.md` e commit). O objetivo é que a aplicação saia de um ciclo de engenharia, não de vibe coding.

Por quê: no benchmark de 04/11 (mesmo esforço, mesmas tarefas), o juiz cego do T4 deu 16,0 ao setup antigo, 11,5 ao atual e 12,0 ao nativo. O atual nunca parou para a decisão nem registrou `ARQUITETURA.md`; o antigo fez as duas coisas em 2 de 2.

## Objetivos

- Projeto novo: sempre `ARQUITETURA.md` antes de qualquer código, dentro do design doc do brainstorming.
- Feature com porta de mão única (modelo de dado ou onde ele mora, contrato externo, auth, serviço com custo recorrente, síncrono × assíncrono, topologia de deploy): parar com a tabela opção × forças e "Sua escolha e o porquê?"; só depois vem a recomendação.
- Registrar: linha em Decisões do `ARQUITETURA.md` (data, decisão, alternativas, por quê, revisitar quando) e commit com `Por quê:` e `Recusado:`.

## Não-objetivos

- Reduzir tokens (decisão do usuário: o peso extra é aceito).
- `spec.md` por feature, as três lentes de review, pergunta de estudo no `REVISAO.md`, palpite em bug.

## Anti-objetivo

Parar em bug, rename ou ajuste sem decisão de arquitetura. Isso vira atrito e custo sem ganho.

## Restrições

- Skill própria no repo, em `skills/arquitetura/`, ligada ao `~/.claude` pelo `install.sh` como as outras.
- Não editar os plugins: o cache é sobrescrito a cada atualização.
- `CLAUDE.global.md` e o hook de lembrete ganham só uma linha cada.

## Abordagens

1. **Escolhida:** skill `arquitetura` mais uma linha de regra no `CLAUDE.global.md` e no lembrete do hook. A skill carrega só quando entra; a regra garante o disparo (no teste, o atual pulou o brainstorming em 2 de 3 T4).
2. Tudo no `CLAUDE.global.md`: dispara sempre, mas pesa em toda chamada, inclusive em bug, e mistura com as regras gerais.
3. Descartada: hook que barra edição sem `ARQUITETURA.md`. Hook não distingue decisão de arquitetura de bug ou rename.
4. Descartada: instalar uma skill pronta do skills.sh. Nenhuma das 9 avaliadas (04/11) cobre o fluxo inteiro: as que param para perguntar não comparam opções com número, e as que registram ADR não param.

## Base e inspirações

Base: seção Arquitetura da skill `ciclo` antiga, a única com forças em número, escolha antes da recomendação e "revisitar quando" (16/16 no juiz). Peças emprestadas:
- `mattpocock/skills` `grilling`: parar e esperar a resposta; não agir antes da confirmação.
- `mattpocock/skills` `domain-modeling`: registrar só quando a decisão é difícil de reverter, surpreende sem contexto e veio de um trade-off real.
- `anthropics/knowledge-work-plugins` `architecture`: colunas da tabela (complexidade, custo, escala, familiaridade) e consequências (o que fica mais fácil, o que fica mais difícil).
- `wondelai/skills` `system-design`: estimativa de escala com número (usuários, requisições, dados), só em projeto novo.
- `addyosmani/agent-skills` `documentation-and-adrs`: repo que já tem `docs/adr/` segue a convenção dele em vez do `ARQUITETURA.md`.

## Decidido pelo usuário

- Parar e deixar o usuário escolher antes de codar.
- Projeto novo sempre passa pela arquitetura.
- Tokens fora do escopo.

## Chamadas minhas (confira)

- A escolha do usuário vem antes da recomendação, como no setup antigo; se diferirem, até 3 linhas sobre o que muda e o usuário decide.
- Repo sem `ARQUITETURA.md`: rascunho pelo código, specs e `git log`, com `?` no que não souber, para o usuário corrigir.
- Versionar no repo o plugin superpowers e o hook de lembrete, que hoje só existem no `~/.claude`; sem isso a regra some num `install.sh` em máquina nova.

## Validação

Benchmark de 04/11 com o setup novo:
- T4 ×2: passa se parar com a tabela em 2 de 2 e, depois do "passa", escrever `ARQUITETURA.md` e `Recusado:` no commit em 2 de 2; juiz cego na mesma rodada.
- T1 ×2 (bug): passa se não parar para arquitetura em nenhum.

## Fica para quem implementa

O texto da skill e o modelo exato do `ARQUITETURA.md`, partindo da seção Arquitetura da skill `ciclo` antiga (`dv-dev1/claude-setup`, `skills/ciclo/SKILL.md`).
