---
name: post-linkedin
description: Use ao pedir post ou publicação de LinkedIn, ou "conta isso no LinkedIn", sobre projeto, decisão técnica ou virada de carreira.
---

# Post de LinkedIn

Escreve um post que só o Daniel poderia ter escrito. O teste: **se outra pessoa pudesse publicar o mesmo texto trocando o nome, o post falhou.**

## O que decide se o post presta

Um post técnico no LinkedIn de 2026 compete com centenas que descrevem a mesma ferramenta. Descrição de feature é commodity — o modelo escreve, todo mundo escreve, ninguém lembra. O que não é commodity:

- **um número que você mediu** — 43 testes, 279 linhas, 8,8 por cento, 52 segundos de CI
- **uma coisa que deu errado** e o que ela ensinou
- **um link que a pessoa pode clicar e rodar**
- **uma opinião que dá pra discordar**

Post sem nenhum dos quatro não vai ao ar. Volta pro material bruto e procura.

## A forma

Medida em cinco posts de referência do Gabriel Nunes, setembro/2026.

| Elemento | Regra |
|---|---|
| Abertura | **uma linha, sozinha, sem preâmbulo.** Uma afirmação ou um termo cunhado. Nunca "Recentemente eu decidi..." |
| Parágrafo | 1 a 3 linhas, uma ideia cada, linha em branco entre eles. Parede de texto morre no "ver mais" |
| Corpo | concreto antes de abstrato. O número, a falha, o nome do arquivo |
| Lista | só quando são fatos paralelos de verdade. Nunca listicle de features |
| Fechamento | algo que o leitor leva — uma lição, uma pergunta real, ou o que vem depois |
| Tamanho | 150 a 300 palavras. O corte do "ver mais" cai por volta da terceira linha: as três primeiras carregam o post |
| Emoji | quase nenhum. Um, se ele fizer trabalho |
| Hashtag | nenhuma. Os cinco posts de referência não têm |
| Idioma | pt-BR. Post técnico pode sair em inglês com tradução embaixo, separada por `-----` |

## O que não copiar da referência

Dois dos cinco posts eram listicle numerado sobre uma ferramenta de terceiro — Claude Agent SDK, ReAct — com termos entre crase (`Context Engineering`, `RAG`, `Vector Database`) e nenhum número, nenhuma falha, nenhum link. Esse formato performa, mas é intercambiável: qualquer pessoa publica igual.

Daniel constrói coisa e mede. Usar o formato de quem só comenta ferramenta joga fora o único ativo que ele tem e os outros não.

**Nunca imitar a voz da referência.** Os dois postam pro mesmo público de IA no Brasil; texto que soa como o do outro some no meio, e quem conhece os dois percebe. Da referência vem a estrutura, nunca o bordão ("meus crias", "kkkkk") nem o jeito de falar.

## Voz

A do próprio Daniel, que já existe escrita: o case da Artefact e os `README` dos projetos dele. Frase curta. Afirmação direta em vez de hedge. Nomeia a alternativa que recusou. Admite o buraco antes de alguém achar.

Não escrever: "incrível", "game changer", "revolucionário", "nessa jornada", "compartilhar um aprendizado", "bora?". Não abrir com pergunta retórica.

## Passos

1. **Achar a história, não o assunto.** "Construí um motor de grafo" é assunto. "Usei LangGraph meses sem saber o que ele fazia por baixo, então escrevi a peça central à mão" é história. A história sempre tem um antes e um depois.
2. **Levantar os números do material bruto** — repositório, testes, medição, commits. Ir buscar de verdade: rodar o comando, contar as linhas. Número inventado destrói o post inteiro se alguém conferir.
3. **Escolher a falha.** Todo projeto tem uma. O bug que a tela expôs, a suposição que o teste derrubou. É o parágrafo que as pessoas comentam.
4. **Escrever três aberturas diferentes** e mostrar as três. A primeira linha decide se o resto é lido.
5. **Passar o rascunho pelo humanizer.** Ler `humanizer.md` (nesta pasta) e aplicar no modo embutido: marcar os tells, reescrever, reler procurando os cinco que sobrevivem (contraste não-X-mas-Y, frase de efeito que fecha parágrafo, travessão, trio, negrito). Nenhum fato, número ou nome entra ou sai nessa etapa.
6. **Entregar em bloco de código**, pronto pra colar, sem comentário no meio. Fora do bloco: no máximo duas linhas dizendo qual escolha foi feita.

## Humanizer em pt-BR e no LinkedIn

`humanizer.md` é cópia do [blader/humanizer](https://github.com/blader/humanizer) @ `9862685`, MIT (`humanizer.LICENSE`). Os exemplos estão em inglês; os padrões valem igual em português. Os que mais aparecem em post brasileiro de IA:

| Tell | Como aparece |
|---|---|
| §1 não-X-mas-Y | "Não é sobre X. É sobre Y." · "não é só X, é Y" · "X, e não Y" |
| §2 fecho de efeito | "E é isso." · "Simples assim." · "Fica a reflexão." · "Leia de novo." |
| §3 frase profunda | "No fim do dia" · "A verdade é que" · "O ponto é" · "X é a nova Y" |
| §4 preparação | "Vou te contar uma coisa" · "Spoiler:" · "O resultado?" · "Sabe o que aconteceu?" · "Pensa comigo" |
| §12 palavra de IA | "crucial", "robusto" (figurado), "potencializar", "alavancar", "cenário" (abstrato), "jornada", "fundamental" |
| §13 significado inflado | "um marco", "abre portas para", "o futuro é promissor", "e isso é só o começo" |

Onde o humanizer e esta skill divergem, vale isto:

- **Linha solta.** Parágrafo de uma linha é forma do LinkedIn e fica. O que o §2 corta é a linha solta que só repete o parágrafo anterior. A abertura de uma linha fica, desde que traga fato ou afirmação.
- **Alternativa recusada.** O §5 corta objeção que ninguém fez. Alternativa que o Daniel de fato pesou e descartou é substância e fica.
- **Travessão.** Zero no post. O separador `-----` da tradução não conta.
- **Saída.** Só a versão final, no bloco de código. Rascunho e lista de tells não vão pro usuário.

## Onde te atacam

"Isso não é autopromoção demais?" Não, se tem número e link: aí é registro de trabalho, e quem quiser conferir clica. Vira autopromoção quando não tem o que conferir.
