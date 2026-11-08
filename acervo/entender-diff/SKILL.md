---
name: entender-diff
description: Use para entender o que mudou num commit ou branch, revisar a própria branch antes do merge, ou saber o que a IA fez e por quê. Caçar bug é do /code-review.
---

# Entender diff

O usuário quer entender uma mudança que não escreveu à mão: como era, como ficou e por quê. Caçar defeito é trabalho do `/code-review`.

Leia primeiro `references/entender.md`. As regras de código real, por quê e fluxograma valem em todos os passos.

## Passos

### 1. Fixar o diff

Use a rev que o usuário passou (`A..B` ou um SHA; SHA sozinho vale `SHA^..SHA`). Sem rev, use `git merge-base HEAD main`..`HEAD`. Rode `git diff --stat` e `git log --oneline` do intervalo.

Feito quando: base, fim e lista de arquivos estão na tela.

### 2. Ler

Leia o diff inteiro e o estado anterior dos arquivos (`git show <base>:<arquivo>`). Separe o que muda comportamento do que é refactor ou mecânico (rename, formatação, import); o mecânico entra só numa linha no fim do agora. Para cada símbolo alterado, rode `grep -rn "<símbolo>"` e anote quem o chama.

Feito quando: você sabe qual fluxo a mudança toca e quem chama o que mudou.

### 3. Antes

Como o fluxo funcionava antes da mudança, visto por quem usa o sistema: de 3 a 5 linhas com o `arquivo:linha` do estado anterior, e o fluxograma do caminho antigo. Feche com a limitação que a mudança resolve, se o commit, a spec ou o código a mostrarem.

Feito quando: quem nunca viu o projeto entende o caminho antigo.

### 4. Agora

Como funciona depois, no mesmo formato e na mesma ordem do antes, para comparar lado a lado: uma linha por diferença, com `arquivo:linha`, e o fluxograma do caminho novo. O que ficou igual diz "como antes".

Feche com `Pode quebrar:` cada chamador anotado no passo 2 que passa a se comportar diferente ou ainda conta com o comportamento antigo (um valor, um formato, um tempo), com `arquivo:linha` e o efeito. Sem nenhum, escreva `Pode quebrar: nada fora do diff depende do que mudou`.

Feito quando: cada diferença entre os dois fluxogramas tem uma linha que a explica, e cada chamador do passo 2 foi conferido para o `Pode quebrar`.

### 5. Por quê

Rode:

```bash
python3 ~/new-claude-setup/acervo/entender-diff/scripts/decisoes.py --repo <repo> --rev <base>..<fim>
```

A saída traz o que o usuário pediu nas sessões que fizeram o diff (ou `sem transcript`). Leia também os comentários novos, as mensagens de commit e as `specs/*.md` do intervalo. Com isso e com o antes e o agora, escreva os blocos `Problema / Solução / Por quê` de `references/entender.md` para as decisões visíveis no diff, ou seja, os pontos em que havia outro caminho.

Feito quando: toda decisão com motivo próprio está num bloco, com `motivo não registrado` onde faltou fonte.

### 6. Fechar

Tudo fica no chat: o antes, o agora e o por quê, com os dois fluxogramas em caixas. Fora o diagrama do Orca (`references/entender.md`, Fluxograma), não grave arquivo; só se o usuário pedir. Esta resposta fica fora do teto de 8 linhas de prosa, da tela e dos blocos do manual; o de 8 palavras por célula vale.

Feito quando: o chat tem antes, agora e por quê.
