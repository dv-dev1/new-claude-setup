# Regras de entendimento

Valem para `entender-diff`, `do-zero`, `learning-concept` e o relatório da `diagnosing-bugs`. O alvo: o usuário entende o que o código faz e por quê, sem ter escrito o código. Visual primeiro e teto de saída são os do manual; aqui ficam os formatos.

| Momento | Seção |
|---|---|
| Sequência, fluxo ou decisão com ramos | Fluxograma |
| Leitura, pesquisa ou subagente | Tabela de achados |
| Debug | Causa em cadeia |
| Três ou mais atores trocando mensagem | Sequência |
| Impacto de mudança, quem chama quem, estrutura de pasta | Árvore de dependência |
| Explicar código | Fluxograma e Sequência |

A prosa fica com o que a caixa não mostra: a causa em uma frase, o `arquivo:linha`, a correção, o que ele precisa decidir. Teste: parágrafo com "então", "depois", "quando X, Y", "se não" é fluxo escrito em prosa; desenhe.

## Leitor

Dev full stack e AI engineer (Node, TypeScript, React, FastAPI, Python, n8n). Termo técnico entra sem definição e sem analogia. Defina só o vocabulário interno do projeto, onde o nome do código difere do nome do negócio: "`temperatura` no código, prioridade na tela".

## Código real

Toda afirmação sobre o código aponta `arquivo:linha`, lida pela ferramenta de leitura do harness ou por `git show <rev>:<arquivo>` e `git diff -U3 <base>..<fim>`, nunca de memória. A frase usa os nomes reais e o valor concreto: "`db.ts:33` devolve o banco da vez; na mensagem do número de apresentação, é o fictício".

Trecho de código só entra quando a frase não basta, com o comando escrito logo acima dele: qualquer um roda de novo e confere.

## Por quê

O porquê é o de engenharia: que problema a decisão resolveu e por que ela tem essa forma. Uma decisão por bloco, até 5 blocos, cada linha com uma frase simples:

```
**1. Tempos alinhados**
Problema: o web desistia de esperar o áudio em 30 s, mas o cérebro podia levar 40.
Solução: o cérebro leva no máximo 32 s e o web espera 45.
Por quê: quem espera precisa aguentar mais do que o pior caso de quem trabalha.
```

Junte num bloco as decisões que têm o mesmo motivo. Detalhe sem motivo próprio (log, teste, rename) fica de fora. O problema sai do antes e a solução do agora. O por quê é o princípio de engenharia dito em palavras simples, sem o nome técnico na frente. Quando a forma exata dependeu de algo que o código não mostra (um número, um requisito de negócio, uma alternativa descartada), procure em comentário, spec, mensagem de commit e na saída do `decisoes.py`, que traz o que o usuário pediu nas sessões. Sem fonte, escreva `motivo não registrado` e não complete de cabeça.

Para um trecho fora de um diff: `git log -S'<valor ou nome>' --format='%h %ad %s' -- <arquivo>` acha o commit que o criou.

## Fluxograma

O diagrama existe para o leitor entender rápido, não para inventariar o código. Se ele precisa ler cada caixa, ficou grande demais. Desenhe em caixas de moldura, num bloco ```` ```text ````: o terminal do usuário não renderiza Mermaid, e o bloco `text` aparece igual no chat e no `.md`.

- **Uma pergunta por diagrama**, dita numa frase acima dele ("Como três mensagens viram uma resposta?"). Duas perguntas são dois diagramas.
- De cima para baixo, até 72 colunas, até 10 caixas.
- Passo em caixa reta (`┌─┐ │ └─┘`), decisão em caixa redonda (`╭─╮ │ ╰─╯`) com pergunta de até 4 palavras. Rótulo na língua do negócio, nunca `acordarCerebro()`; nome de função, `arquivo:linha` e valor exato vão no texto abaixo.
- Seta vertical `│` e `▼`, com o número da ordem e o que passa escrito ao lado: `│ 1 · três mensagens`. O `não` sai para o lado (`──── não ───▶`) e chega numa caixa própria.
- Sempre para a frente: o resultado chega numa caixa nova. Só um laço do código (retry, while) volta, saindo da decisão.
- Conte as colunas: todas as linhas de uma caixa têm a mesma largura.
- **Exceção e caso raro ficam no texto**: falha de rede, corrida entre execuções, valor limite.
- Depois do diagrama, uma linha `Leia assim:` com o caminho feliz em uma frase.

Como fica, no caso do `decisoes.py`:

```text
┌──────────────────────────────┐
│ decisoes.py --rev f606358    │
└──────────────┬───────────────┘
               │ 1 · git diff --name-only
               ▼
╭──────────────────────────────╮
│ sessão tocou o diff?         │──── não ───▶ ┌────────────────┐
╰──────────────┬───────────────╯              │ sem transcript │
               │ sim                          └────────────────┘
               ▼
┌──────────────────────────────┐
│ disse · escolheu · aprovou   │
└──────────────────────────────┘
```

Leia assim: o script só traz o pedido do usuário quando a sessão mexeu no diff.

No Orca (`echo $TERM_PROGRAM` dá `Orca`), mande também o fluxograma do caminho novo ao Excalidraw, que abre numa aba ao lado. Em `novos` vão as caixas que o diff ou o capítulo criou, que saem verdes:

```bash
python3 ~/.claude/tools/excalidraw.py <nome> <<'EOF'
{"nos": {"pede": "Cliente pede", "tem": "Tem estoque?"}, "arestas": [["pede", "tem", "1 · pedido"]], "novos": ["tem"]}
EOF
```

## Tabela de achados

Use para apresentar o resultado de leitura, pesquisa ou subagente.

- Colunas `arquivo:linha | o que é | por que importa`, até 8 linhas de achados, a mais importante primeiro.
- Célula até 8 palavras: rótulo, não frase.
- Nunca cole a saída da ferramenta; cite a linha decisiva na coluna `o que é`.
- Se precisar de caixas para explicar um achado, siga o Fluxograma: passo reto, decisão redonda, até 72 colunas e rótulo na língua do negócio.

| arquivo:linha | o que é | por que importa |
|---|---|---|
| src/compra.py:24 | `saldo < valor` recusa a compra | Impede gastar acima do saldo |

## Causa em cadeia

Use no diagnóstico de um bug para ligar o sintoma à causa raiz.

- Caixas de cima para baixo, do sintoma à causa raiz; a última caixa é a causa.
- Use o vocabulário do Fluxograma: passo reto, decisão redonda, até 72 colunas e rótulo na língua do negócio.
- O `arquivo:linha` da causa vai na linha `Leia assim:` abaixo do diagrama.

```text
┌────────────────────┐
│ Compra duplicada   │
└─────────┬──────────┘
          │ 1 · dois pedidos
          ▼
┌────────────────────┐
│ Ambos confirmados  │
└─────────┬──────────┘
          │ 2 · mesmo pagamento
          ▼
┌────────────────────┐
│ Sem conferir cópia │
└────────────────────┘
Leia assim: src/compra.py:42 confirma sem conferir pagamento repetido.
```

## Sequência

Use quando três ou mais atores trocam mensagens (webhook, fila, API, hook): o fluxograma tem um ator só e esconde quem faz o quê.

- Uma coluna por ator, nome no topo e linha de vida `│` embaixo; até 5 atores, até 72 colunas.
- Mensagem é seta horizontal, `──▶` na ida e `◀──` na volta, com o número da ordem e o que passa: `1 · "ok"`.
- O tempo corre de cima para baixo. Uma pergunta por diagrama, como no Fluxograma.
- Rótulo na língua do negócio; nome de função e `arquivo:linha` vão na linha `Leia assim:`.

```text
Como um git push --force chega a rodar?
 você           Claude Code       preflight-guard
  │                  │                   │
  │                  │ 1 · push --force  │
  │                  │──────────────────▶│
  │                  │◀─ 2 · ask ────────│
  │◀─ 3 · diálogo ───│                   │
  │ 4 · clique       │                   │
  │─────────────────▶│                   │
  │                  │ 5 · roda o push   │
```

Leia assim: `hooks/preflight-guard.py` não aprova o force; devolve `ask`, e o clique no diálogo nativo é o consentimento.

## Árvore de dependência

Use para impacto de mudança (quem chama X, o que quebra se X mudar) e estrutura de pasta: a tabela achata a hierarquia e o fluxograma inventa uma ordem que não existe.

- Raiz no topo, filhos com `├──` e o último com `└──`; o neto recua com `│   `.
- Até 3 níveis e 12 folhas; o resto vira `└── +N`, com o critério do corte.
- Ao lado de cada folha, o que ela faz ou usa, em até 6 palavras.
- Lida por comando, nunca de memória, com o comando escrito logo acima do bloco.

`grep -n "from _transcript import" hooks/*.py`

```text
O que quebra se _transcript.py mudar?
_transcript.py
├── preflight-guard.py   gate da faixa vermelha
├── git-identity.py      identidade do commit
├── roteador-agente.py   teto e modelo do subagente
└── autocompact.py       /compact depois do commit
```
