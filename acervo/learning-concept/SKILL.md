---
name: learning-concept
description: Ensina um tema de estudo, de linguagem e fundamento (Python, C, JavaScript) a ferramenta (Docker, Postgres), em cartões: o conceito com o porquê, prática à mão sem IA e uma decisão em cenário.
disable-model-invocation: true
---

# Learning concept

O usuário quer o **modelo mental** do tema: o que é cada peça, quando ela se aplica, quando não se aplica e por quê. Claude escreve todo o código que não ensina o conceito; o que ensina, o usuário escreve sem IA. O aprendizado mora no **erro**: o usuário erra no palpite, no exercício e na decisão, e a correção mostra o critério. Toda explicação parte de uma **dor** concreta, num cenário do nível dele (um script que soma gastos de um CSV, um agente FastAPI que chama a OpenAI).

Leia primeiro `~/new-claude-setup/acervo/entender-diff/references/entender.md`. Use seus fluxogramas em caixas.

## Custo

Sem subagente. Até 6 chamadas de ferramenta por resposta. O progresso fica na trilha, `TRILHA.md`: sessão nova lê a trilha e retoma `## Agora`, sem reler o resto.

## Entrada

- `/learning-concept <tema>`: monta trilha nova em `~/estudos/<tema-em-kebab-case>/`.
- `/learning-concept` ou "continue": retome `TRILHA.md` do diretório atual. Sem trilha local, procure `~/estudos/*/TRILHA.md`: um resultado, retome; vários, pergunte qual; nenhum, siga o plano.
- Plano: `~/estudos/PLANO.md` lista as trilhas em ordem, cada uma com o seu `/learning-concept <tema>`. Sem trilha para retomar, proponha a primeira não marcada e espere o ok; sem plano, pergunte o tema.

## Passos

### 1. Trilha (só quando não há trilha para retomar)

Se o objetivo não estiver claro, pergunte uma vez para que o usuário quer o tema (ex.: "subir meu agente num servidor").

Escolha o **modo**, que muda só o passo "Na mão" e o mini-projeto:

- `base`: linguagem ou fundamento (Python, C, JavaScript, estruturas de dados, SQL). Ele escreve a lógica; a meta é fluência sem IA.
- `ferramenta`: tecnologia usada sobre a base (Docker, Postgres, FastAPI). Ele digita só as linhas onde o conceito aparece.

Na dúvida entre os dois, pergunte junto com o objetivo. Liste de 6 a 12 conceitos em ordem de dependência: cada cartão usa só conceitos dos anteriores. O nome do conceito é o termo técnico como a documentação oficial escreve (`image`, `container`, `volume`, `network`, `compose`), com uma frase em português.

Agente que chama LLM usa a API da OpenAI com a chave do usuário em `OPENAI_API_KEY`; sem ela no ambiente, peça antes do cartão que chama o modelo.

Grave `~/estudos/<tema>/TRILHA.md`:

```markdown
# Trilha: <tema>

Para quê: <objetivo do usuário>
Modo: <base | ferramenta>
Rodar: <pré-requisito, ex.: Docker Desktop aberto · `uv run`>

## Mapa
<fluxograma em caixas, uma caixa por conceito, na ordem; ✓ feito, ◆ agora, ○ por vir>

## Cartões
### 1. <conceito> — <frase>
- [ ] dor e modelo · [ ] na mão · [ ] decisão
Doc: <URL com a seção exata>
Resumo: <a frase do usuário, corrigida>

## Decisões
| cenário | resposta dele | critério certo |
|---|---|---|

## Agora
Cartão 1, abertura
```

Feito quando: a trilha está gravada e o Mapa foi mostrado. Siga para o cartão 1 na mesma resposta.

### 2. Cartão: abertura

Uma resposta, nesta ordem:

- **Onde estamos**: `Cartão N de M · <conceito>` e o Mapa com `◆` neste cartão.
- **Revisão relâmpago** (do cartão 2 em diante): uma pergunta de uma linha sobre um cartão anterior, de preferência um que ele errou em `## Decisões`. Ele responde junto com o palpite; corrija em uma linha no passo 3.
- **Dor**: a cena concreta do problema sem o conceito, em até 3 linhas. Ex.: "o agente roda no seu Mac com Python 3.12; o servidor tem 3.9 e não tem a `libpq`".
- **Modelo mental**: caixas com as peças e quem fala com quem; uma analogia de uma linha; tabela `quando usa · quando não usa · alternativa`.
- **Doc**: a seção da documentação oficial e o que observar nela, em até 2 linhas. Confira a URL com a skill `pesquisa-web` quando não tiver certeza e grave em `Doc:`.
- **Na mão**, modo `base`: grave você o teste (`test_<conceito>.py` com `pytest`, `assert` em C, `node:test` em JavaScript) e o esqueleto com a assinatura e o corpo vazio. Ele escreve o corpo, de 5 a 25 linhas, sem IA no editor. Mostre a assinatura, o que cada teste cobra em uma linha e o comando que roda os testes; a solução fica de fora.
- **Na mão**, modo `ferramenta`: antes, grave você o apoio que não ensina o conceito (app de exemplo, dependências, arquivos de dados). O usuário digita de 1 a 5 linhas ou comandos onde o conceito aparece (`FROM python:3.12-slim`, `docker run -p 8000:8000 agente`, `@app.post("/perguntar")`). Mostre o trecho com `arquivo:linha` e as linhas em volta. Para cada linha não óbvia, um bullet com a consequência de fazer diferente, como "sem `-p`, a porta fica presa dentro do container".
- **Palpite**: "o que acontece quando você rodar?" (no modo `base`, "quais testes passam na primeira vez?"), sem resposta.
- Última linha: `digite, rode, diga seu palpite e continue`.

Grave em `## Agora` o arquivo, o comando e a saída esperada, para conferir em outra sessão.

Feito quando: o trecho está no chat e o apoio está no disco.

### 3. Cartão: conferir e decidir (o usuário voltou)

Leia o arquivo do passo e rode o comando gravado em `## Agora`.

- **Erro de digitação** (nome trocado, aspas, indentação): no modo `ferramenta`, corrija você e mostre em uma linha o que estava e o que ficou; no modo `base`, a sintaxe é parte do aprendizado: aponte `arquivo:linha` e a mensagem de erro, e ele corrige.
- **Erro de entendimento** (porta trocada, peça no lugar errado): aponte `arquivo:linha` e o que muda no resultado. O usuário corrige. Repita até funcionar.
- **Palpite**: compare com a saída real em até 3 linhas. Palpite errado é o ponto alto do cartão: mostre, nas caixas do modelo mental, por que a saída real faz sentido.

**Ajuda em degraus**, quando ele travar ou pedir ajuda, um degrau por resposta:

1. Uma pergunta que aponta onde olhar ("o que tem em `total` depois da primeira volta?").
2. O conceito nas caixas do modelo mental, sem código.
3. Pseudocódigo em português.

Código da solução só depois do degrau 3 e a pedido dele. Nesse caso, o mesmo exercício volta com outro dado na revisão relâmpago do próximo cartão.

Depois, a **Decisão**: um cenário novo, diferente do exemplo do cartão, que pede julgamento sobre quando usar ou não usar. Ex.: "agente + Postgres, um dev só, deploy numa VPS: Compose ou Kubernetes? Por quê?". Peça também a frase: "explique `<conceito>` para um colega em uma frase". Sem resposta.

Feito quando: o trecho funciona e a decisão foi perguntada.

### 4. Cartão: fechar (o usuário respondeu a decisão)

Corrija em até 3 linhas: o que estava certo, o que faltou e o critério que decide. Se o usuário não souber, a falha é da pergunta: responda você, com caixas comparando os dois caminhos.

Grave a frase dele, corrigida, em `Resumo:`; uma linha em `## Decisões`; marque o cartão; atualize Mapa e `## Agora`. Siga para a abertura do próximo cartão na mesma resposta; depois do último, para o mini-projeto.

Pergunta no meio, inclusive "onde estou?" ou "não entendi": responda com o Mapa e o modelo mental do cartão; o passo continua pendente.

Feito quando: o cartão está marcado e a trilha atualizada.

### 5. Mini-projeto e entrevista

Com todos os cartões marcados, um projeto pequeno que junte os conceitos da trilha:

- Modo `ferramenta`: monte você (ex.: agente FastAPI com Postgres no Compose), rode e mostre funcionando.
- Modo `base`: grave você o enunciado e os testes, num tamanho de uma a duas sessões (ex.: controle de gastos no terminal). Ele escreve o código sem IA, com ajuda em degraus. Revise com `arquivo:linha`: o que está bom e um caso que os testes não cobrem e quebra.

Depois, uma pergunta de entrevista por resposta, uma por peça: "por que esta peça existe aqui? O que quebra sem ela?". Corrija cada resposta em até 3 linhas.

Feche com uma tabela: conceito · onde aparece no projeto (`arquivo:linha`) · frase do usuário. Marque a trilha em `~/estudos/PLANO.md`, se ela estiver lá.

Feito quando: o projeto roda e a tabela foi mostrada.
