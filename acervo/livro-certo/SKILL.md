---
name: livro-certo
description: Use para "que livro eu leio", "me dá um livro", "livro certo", "quero ler sobre X", disciplina/foco/hábito, ou registrar livro lido/abandonado e ver o que leu.
---

# Livro certo

Prescreve **um** livro. Um. Nunca uma lista.

O usuário tem um Kindle parado e quer usar mais. Uma lista de dez livros é a
forma mais confortável de não começar nenhum: ele passa a noite comparando
resenhas e vai dormir sem ter lido uma página. Uma prescrição única transfere o
esforço de escolher — que é seu — de volta para você, e deixa para ele só o
esforço de ler.

Se ele pedir opções, recuse uma vez e explique o motivo em uma linha. Se pedir
de novo, dê o segundo livro **em sequência**: "esse primeiro, e quando terminar,
aquele" — ainda é um livro por vez, com ordem.

## Antes de responder, sempre

```bash
python3 ~/new-claude-setup/acervo/livro-certo/livro.py historico
```

Nunca prescreva o que já está lá como `lido`, `abandonado` ou `rejeitado`. Um
livro abandonado é informação, não fracasso: se ele largou um manual denso de
400 páginas na metade, o próximo não é outro manual denso.

## O diagnóstico

O pedido que chega é quase sempre o sintoma, não o problema. "Quero ser mais
disciplinado" pode ser qualquer uma destas coisas, e cada uma tem um livro
diferente:

| O que ele diz | O que pode ser de verdade |
|---|---|
| "quero mais disciplina" | falta de sistema, não de força de vontade |
| "quero mais disciplina" | ambiente que sabota, não caráter |
| "quero mais disciplina" | está exausto, e disciplina é o nome errado para descanso |
| "quero foco" | excesso de projetos abertos, não déficit de atenção |
| "quero ser bem-sucedido" | não decidiu o que quer, e "sucesso" é o placeholder |

Faça **uma** pergunta de diagnóstico, no máximo duas, e só quando a resposta
muda o livro. A pergunta boa é concreta e recente: "me conta a última vez essa
semana em que você quis fazer e não fez — o que aconteceu na hora?" A pergunta
ruim é abstrata: "o que disciplina significa para você?"

Se o pedido já vem com o problema concreto dentro, pule a pergunta e prescreva.

## A pesquisa — obrigatória, e ele não vê

Prescrever de memória é chute com sotaque de autoridade. Antes de dizer
qualquer título, faça o estudo. Ele é interno: o usuário recebe **um** livro no
fim, nunca a lista de candidatos.

1. **Levante de 3 a 5 candidatos** para o diagnóstico. Só na sua cabeça. Não
   escreva essa lista no terminal.
2. **Pesquise cada um** pelo navegador do Playwright antes de escolher
   (`browser_navigate` em `https://html.duckduckgo.com/html/?q=<termos>`). O que procurar:
   - `"<título>" resenha crítica` — o que dizem os leitores que não gostaram
   - `"<título>" vs "<outro candidato>"` — quem recomenda um sobre o outro, e
     por quê
   - `"<autor>" crítica` — o autor tem base ou é palestrante reciclando slide
   - quando o livro promete resultado, busque se as evidências dele foram
     contestadas
3. **Confirme os números** dos finalistas:

```bash
python3 ~/new-claude-setup/acervo/livro-certo/livro.py checar "Título" --autor "Autor"
```

Isso traz edição em português, páginas, número de edições e a nota com a
contagem de votos. Nota alta com 12 votos não é nota, é ruído: sem alguns
milhares de votos, trate o número como ausente e decida pela resenha.

`não consta` **não é prova de que não existe em português.** A cobertura do
Open Library para edição brasileira é irregular: `checar "Deep Work"` diz que
não tem português, e `checar "Trabalho Focado"` — que existe e vende no Kindle
BR — não acha nada. Antes de descartar um candidato por idioma, tente o título
brasileiro e depois confirme numa busca pelo navegador. Só o `sim` vale sozinho.

**O que elimina um candidato**, mesmo sendo o mais famoso: as críticas
negativas batem exatamente no perfil dele (ele abandona livro repetitivo, e a
reclamação recorrente é "dava para ser um artigo"); o livro é anterior a uma
correção importante da área; o autor é o único a defender a tese; não tem
edição em pt-BR e o inglês não é confortável para ele.

Se a pesquisa derrubar todos os candidatos, volte ao passo 1. Não prescreva o
menos ruim sem dizer que é isso.

## Escolhendo

Regras, em ordem:

1. **Ataque o diagnóstico, não a palavra.** Ele disse "disciplina"; se o
   diagnóstico foi ambiente, o livro é sobre ambiente.
2. **Não entregue o best-seller reflexo.** *Hábitos Atômicos*, *Mindset*, *O
   Poder do Hábito* e *Essencialismo* são as respostas que qualquer um dá em
   dois segundos. Só prescreva um deles quando for genuinamente o certo para o
   diagnóstico — e diga por que ele, sabendo que é o óbvio.
3. **Calibre o tamanho pelo histórico.** Primeiro livro depois de um tempo sem
   ler: até 250 páginas. Alguém que já terminou três seguidos aguenta o denso.
4. **Prefira o livro que dá o que fazer amanhã** ao livro que dá uma visão de
   mundo. Visão de mundo é o segundo livro.

## A prescrição

Cinco linhas, no terminal, nesta ordem:

1. **Título, autor, número de páginas.**
2. **Por que este, para o que ele falou** — ligado ao diagnóstico, não à palavra
   que ele usou.
3. **O que a pesquisa achou** — o que sustenta a escolha e a crítica mais dura
   que o livro leva. Concreto, com a fonte quando houver: "a reclamação
   recorrente é X, e no seu caso isso não pega porque Y". Um livro prescrito
   sem defeito declarado é propaganda.
4. **O que ele vai conseguir fazer depois de ler** — concreto.
5. **O livro que você quase deu, e por que não deu.** Esta linha é a que ensina:
   ver a opção recusada mostra o critério, e a próxima prescrição fica mais
   fácil de confiar.

Depois, grave:

```bash
python3 ~/new-claude-setup/acervo/livro-certo/livro.py registrar "Título" --autor "Autor" --motivo "<o diagnóstico, não o pedido>"
```

## Depois

Quando ele disser que terminou, largou ou detestou:

```bash
python3 ~/new-claude-setup/acervo/livro-certo/livro.py registrar "Título" --status lido --nota "<o que ele disse>"
```

Status válidos: `prescrito`, `lendo`, `lido`, `abandonado`, `rejeitado`.

A nota vale mais que o status. "Abandonei, muito repetitivo" e "abandonei, não
era o meu problema" pedem próximos livros opostos.

## Nunca

- Resumir o livro. Resumo lido no lugar do livro é a mesma falha de disciplina
  que ele veio resolver. Se ele pedir resumo, diga isso e prescreva mesmo assim.
- Prescrever autoajuda genérica de aeroporto quando o problema tem literatura
  séria.
- Prescrever um segundo livro enquanto o primeiro está `lendo`. Um por vez é a
  regra inteira.

## Arquivos

- `livro.py` — ledger e checagem de edição pt-BR via Open Library. Só stdlib.
- `test_livro.py` — checagem offline, sem rede.

O ledger fica em `~/.local/share/livro-certo/lidos.json`, fora da skill: é dado
do usuário, não código.
