---
name: explain-project
description: Use para entender, estudar ou explicar um projeto ou repositório (equipe, reunião, entrevista), em página Artifact. Para um commit, use `entender-diff`.
---

# Por baixo dos panos

O usuário quer entender um projeto que não escreveu à mão, a ponto de explicá-lo a outra pessoa. Ele precisa de duas camadas: **o negócio** (que regra existe, por que existe, um caso real) e **o mecanismo** (tool calling, idempotência, backoff), com o termo de mercado, o trecho de código que o aplica e o porquê da decisão. Suba a **escada de abstração**: do trecho real ao conceito, do conceito à decisão e à alternativa recusada.

Ele entende pelo visual: regras e código viram um fluxograma só, e cada conceito vira um fluxo passo a passo. Texto curto. Termo técnico fica em inglês, como o mercado fala (_thread_, _worker_, _queue_, _retry_, _backoff_, _rate limit_, _event log_), nunca traduzido.

## Entrada

`/explain-project [<repo>...] [nível]`: `dono/nome` do GitHub ou caminho local; sem repo, o diretório atual. Nível padrão **júnior**; `pleno` aprofunda escala e falhas.

## Custo

Sem subagente. Leia o caminho de entrada até a saída, não o repositório inteiro.

## Passos

### 1. Ler

Clone cada repo do GitHub só para leitura em `~/estudos/.originais/<nome>` (`gh repo clone <dono/nome> ~/estudos/.originais/<nome>`); use caminho local como está. Leia o material do negócio (enunciado, mensagem do cliente, manual, spec), o README (seções de decisões e de limites admitidos) e o caminho de uma entrada real até a saída: a rota ou o comando, o núcleo, as chamadas externas, o estado e os testes. Anote `arquivo:linha` de cada peça com o comando que a mostrou, e a fonte de cada decisão (README, comentário, docstring).

Para cada regra de negócio, anote a condição, o resultado, o `arquivo:linha` onde o código a aplica, a fonte do porquê (`arquivo:linha` do material) e um caso real dos dados que passa por ela. Rode o código nos casos (o núcleo puro, com os dados de amostra) e use o valor que sair, nunca um valor de cabeça.

Feito quando: cada projeto tem uma entrada real seguida até a saída, com `arquivo:linha` de cada peça, e cada regra tem fonte e caso conferido.

### 2. Escolher os conceitos

Para cada peça, pergunte: que ideia reconhecível fora deste projeto ela implementa? O nome de mercado é o título da ficha (_tool calling_, _rate limit_, _máquina de estados_). Junte peças que implementam a mesma ideia. No nível júnior, fique com 6 a 8 conceitos por projeto, os que quem ouve a explicação precisa: arquitetura, onde entra o LLM, falhas de rede, estado, testes. Corte detalhe interno de biblioteca e otimização.

Com dois ou mais projetos, um conceito presente em pelo menos dois vira **Padrão** e entra na aba Padrão, numa tabela com uma coluna por projeto, e a ficha fica no projeto onde ele é mais claro.

Feito quando: cada conceito tem nome de mercado, as peças que o implementam e a marca Padrão ou o projeto.

### 3. Montar a página

Siga a página-modelo [references/exemplo.html](references/exemplo.html): copie o `<style>`, as abas e o `<script>` e troque só o conteúdo. Uma aba **Padrão comum** (com dois ou mais projetos) e uma aba por projeto, cada uma aberta por:

- **Resumo em 30 segundos**: o tipo de sistema em termos técnicos (agente conversacional, workflow assíncrono, pipeline) e a peça onde entra o LLM.
- **Fluxo: negócio e código**: um fluxograma por projeto (`<div class="fx" data-fluxo="<projeto>">` + objeto em `FLUXO` no script da página-modelo), de cima para baixo: o caminho principal desce, o desvio sai pelo lado. Uma chave Negócio / Código / Os dois troca o rótulo de cada caixa entre a regra (`t`, `s`) e o código que a aplica (`c`, `f` com `arquivo:linha`): negócio antes do sistema, sem um segundo desenho. Rótulo de negócio na língua do negócio ("Repetiu antes do prazo?"), nunca o nome da função. O clique abre embaixo da caixa `faz`, `porque` com `fonte`, `exemplo` com o caso real, o `codigo` e a `ficha`. Porquê sem fonte vira `inferido`.

  | O que é | `k` |
  |---|---|
  | acontece no mundo (cliente pergunta, médico pede, tick do schedule) | `ev` |
  | condição que muda o caminho (`if`, `try/except`, regra) | `q`, com o rótulo de cada saída |
  | valor calculado, passo do código, query, chamada externa | `calc` |
  | estado final ou resposta | `end` |
  | pessoa que decide ou age | `human` |

  `llm: true` marca onde entra o LLM, a única cor fora do sim/não. O agent loop é uma caixa `calc` com `llm: true`; a ficha mostra as voltas. Cada `lane` é um assunto ou um gatilho (rota, worker) com `titulo`, `passos` e, se continua outra faixa, `de: <id>`. No passo: `lados: [[rótulo, id]]` para cada desvio e `desce` para o rótulo da saída de baixo. Desvio que não é fim volta ao passo seguinte; `vai: <id>` na caixa aponta outro retorno ou uma volta (retry, loop do agente). Uma caixa por decisão ou efeito colateral, não por linha.

  O `caso` é um caso real do ponto de entrada à saída (`passos: [[id, texto]]`, com o valor que o código devolveu); pode repetir uma caixa, como a segunda volta do agent loop. O botão "Seguir o caso" acende o caminho com o texto de cada passo. O `GLOSSARIO` guarda só termo do negócio (glosa, carteirinha), sublinhado com definição no hover; o termo técnico segue em inglês e sem definição. O que vem do conhecimento do setor, e não das fontes, leva `(conhecimento do setor)`.
- **Mapa dos arquivos**: tabela arquivo · papel.
- **Stack e limites**: modelo, provedor, banco, escala, o que ficou de fora, com a fonte.

No fim da aba, **Onde mexer para mudar**: tabela mudança provável · `arquivo:linha`.

Depois, uma **ficha** por conceito, nesta ordem:

| Bloco | Conteúdo |
|---|---|
| Título e termos | nome do conceito + termos de mercado (`tool calling · agent loop`) |
| Conceito | 2 ou 3 linhas: o mecanismo em termos técnicos, válido fora do projeto |
| Fluxo | `ol.flow` sequencial: um passo por `li`, chip de ator (código, LLM, SQLite, serviço externo, pessoa), ação curta, `arquivo:linha`; ramo vira dois `.out` (sim/não) no passo; loop vira nota "↻ volta ao passo N"; fase vira `li.phase` |
| Código anotado | trecho real de até 12 linhas, com `arquivo:linha`, e marcadores `<span class="pin">N</span>` explicados ao lado: o que a linha faz e por quê |
| Decisão | escolha · recusado · por quê, com a fonte; sem fonte, `motivo não registrado` |
| Para explicar | 2 frases faladas para explicar a outra pessoa |

O fluxo segue a ordem em que o código roda, de cima para baixo, sem setas cruzando: fluxo errado ou confuso atrapalha mais que ajuda. Use o dado real do projeto nos passos (o id, o status HTTP, o valor). Escape `<`, `>` e `&` no código. Marque `inferido` no que nenhuma fonte mostrou. Limite admitido no README entra na ficha do conceito como decisão "Lacuna admitida".

Grave em `~/estudos/<tema>/por-dentro.html` e publique com o Artifact tool (`icon: "code"`). Republicar o mesmo arquivo mantém a URL.

No Orca (`echo $TERM_PROGRAM` dá `Orca`), mande também o caminho principal de cada projeto ao Excalidraw, que abre numa aba ao lado: `python3 ~/.claude/tools/excalidraw.py <projeto>`, com a spec no stdin no formato do Fluxograma de `~/new-claude-setup/acervo/entender-diff/references/entender.md`.

Feito quando: toda regra do passo 1 está no fluxo, todo conceito do passo 2 tem ficha com todos os blocos, e cada `arquivo:linha` saiu de um comando.

### 4. Conferir e entregar

Confira o fluxo contra o código, ramo por ramo. Releia a função de cada caixa e liste cada `if`, `return`, `except` e `continue`: cada saída vira desvio ou `desce`, ou o detalhe diz para onde ela vai. Um `get` que pode voltar vazio também é ramo, como uma operadora sem regra para o exame.

| No código | No fluxo |
|---|---|
| pessoa resolve e o item volta às regras | `vai` até a pergunta |
| espera, retry, consulta de novo | `vai` até a própria caixa |
| checagens independentes que se somam | uma `q` por checagem, `desce: "segue"` |
| saída sem nenhum caso nos dados | `exemplo` marcado `ilustrativo` |

Rode `node ~/new-claude-setup/acervo/explain-project/scripts/conferir-fluxo.js <pagina.html>`. Ele acusa id sem caixa, caixa solta, pergunta com menos de dois ramos, caixa sem saída, porquê sem fonte e caso que pula de uma caixa a outra sem ligação; precisa sair `OK`. Depois, rode o caso no código e confira que cada passo segue o ramo que o código seguiu.

Confira de novo cada `arquivo:linha` e cada citação de fonte com `sed -n`/`grep` antes de publicar: corrija número de linha errado e retire o porquê que a fonte não sustenta. Abra a página no navegador, troque a chave para Código, siga o caso e abra uma caixa de cada faixa; texto cortado ou sobreposto volta ao rótulo, mais curto. Entregue o link e a tabela de conceitos por aba.

Feito quando: `conferir-fluxo.js` sai `OK`, cada ramo do código tem desvio ou nota no detalhe, a página está publicada e nenhuma citação ficou sem conferir.
