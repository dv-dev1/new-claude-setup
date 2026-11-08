---
name: do-zero
description: Use para entender "do zero", "passo a passo" ou "como foi construído" um projeto que a IA escreveu. Commit/branch, `entender-diff`; negócio, `explain-project`.
---

# Do zero

O usuário não escreveu o código: quer saber o que foi feito, quando e por quê, na ordem em que o projeto nasceu. Um capítulo por resposta.

Leia primeiro `~/new-claude-setup/acervo/entender-diff/references/entender.md`. As regras de código real, por quê e fluxograma em caixas valem aqui.

## Custo

Esta skill existe para ser barata. Sem subagente, sem grafo, sem arquivo de saída fora o diagrama do Orca (Fluxograma do `entender.md`). Até 4 chamadas de ferramenta por capítulo, mais a do diagrama. Leia só o que o `roteiro.py` imprimiu; arquivo cortado, o `git show` que ele mesmo indicou. O progresso está em arquivo: sessão nova retoma do capítulo certo sem reler nada.

## Passos

O script é `python3 ~/new-claude-setup/acervo/do-zero/scripts/roteiro.py`, sempre com `--repo <raiz do repo>`.

### 1. Roteiro (só na primeira vez)

Rode `capitulo`. Se ele responder `sem roteiro`, rode `commits` e agrupe a lista em capítulos:

- de 8 a 15 capítulos, cada um uma peça que se explica sozinha, na ordem do primeiro commit;
- `fix`, `test` e `refactor` vão para o capítulo da peça que tocam, mesmo que tenham vindo dias depois;
- commit só de texto, estilo ou `chore` vai para `fora`, com o motivo; documento que é entrega (uma proposta, um ADR) vira capítulo;
- título na língua do negócio: "Decidir o destino de cada exame", não "motor.py".

Mande o agrupamento pelo stdin do `gravar`, uma linha por capítulo (`Título | sha sha`) e uma por descarte (`fora: motivo | sha sha`). Ele recusa commit faltando ou repetido; corrija e repita. Menos de 5 commits no histórico: pare e indique `explain-project`.

Feito quando: o `gravar` imprimiu o resumo. Mostre o resumo ao usuário e siga para o capítulo 1 na mesma resposta.

### 2. Capítulo

Rode `capitulo` (ou `capitulo N`, se o usuário pediu um número). A saída traz o título, os capítulos de antes e o de depois, a mensagem e o stat de cada commit, e o diff com teto de linhas. Motivo de uma decisão vem, nesta ordem, da mensagem do commit, de comentário novo no diff e de `specs/*.md`. Só quando faltar, rode `python3 ~/new-claude-setup/acervo/entender-diff/scripts/decisoes.py --repo <repo> --rev <sha>` para aquele commit. Sem fonte, escreva `motivo não registrado`.

Escreva nesta ordem:

- **Capítulo N de M: título**, com as datas e os shas.
- **Onde estamos**: o que já existe e o que falta, em 2 linhas.
- **O problema**: a necessidade que puxou esta peça, na língua do negócio.
- **O que entrou**: até 4 trechos reais do diff, cada um com `sha` e `arquivo:linha`, na ordem em que um depende do outro, e um fluxograma do caminho que o capítulo criou.
- **Por quê**: até 5 blocos `Problema / Solução / Por quê` do `entender.md`, cada um com uma quarta linha `Alternativa recusada:`.
- **O que a revisão pegou**: um `fix` por linha, dizendo o que quebrava. Sem `fix` no capítulo, omita.
- **Pergunta**: uma, sem resposta.
- Última linha: `/do-zero continua no capítulo N+1`.

Narre como construção ("o próximo problema é..."), nunca como inventário do diff. O `arquivo:linha` é o do commit; se o usuário perguntar onde aquilo está hoje, `grep -n` no HEAD.

Feito quando: o capítulo está no chat e termina na linha de continuação.

### 3. Fechar

Tudo fica no chat. Fora o diagrama do Orca, não grave arquivo; só se o usuário pedir. Esta resposta fica fora do teto de 8 linhas de prosa, da tela e dos blocos do manual; o de 8 palavras por célula vale. Se o `capitulo` avisar de commits sem capítulo, diga ao usuário e refaça o `gravar` antes do capítulo seguinte.

Feito quando: `roteiro terminado` apareceu, ou o usuário parou.
