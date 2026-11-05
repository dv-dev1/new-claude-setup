# Resultados

## 04/11/2026 — três setups no mesmo esforço (`high`, bypass, 2 repetições)

Bugs reais (5 bugs que decidem; `quehorasvoto` fica fora: todos mudam a assinatura para `melhorBloco(s, fecha)` e o teste chama sem ela):

| | Antigo | Atual | Nativo |
|---|---|---|---|
| Corrigiu sem quebrar a suíte | 10/10 | 10/10 | 9/10 |
| Custo | US$ 5,74 | US$ 5,67 | US$ 4,52 |
| Tempo | 17,5 min | 12,9 min | 14,8 min |
| Linhas adicionadas | 439 | 315 | 743 |

Sintética:

| | Antigo | Atual | Nativo |
|---|---|---|---|
| Gabarito T1–T3 | 6/6 | 5/6 | 6/6 |
| Juiz T4 (0–16) | 16,0 | 11,5 | 12,0 |
| Perguntou antes da decisão | 2/2 | 0/2 | 0/2 |
| `ARQUITETURA.md` | 2/2 | 0/2 | 0/2 |
| Custo | US$ 5,69 | US$ 2,65 | US$ 1,68 |
| Tempo | 18,6 min | 7,3 min | 7,7 min |

Tokens (18 execuções por setup): antigo 9,8M, atual 7,6M, nativo 4,6M. A saída do atual é a menor (94k contra 118k do nativo); o excesso é de entrada: o contexto começa com ~31k tokens contra ~18k do nativo e é relido a cada turno.

Esforço: o atual em `xhigh` custou US$ 9,72 nos bugs reais contra US$ 6,65 em `high`, com o mesmo acerto.

## 04/11/2026 — depois da skill `arquitetura`

| | Antes | Depois | Antigo |
|---|---|---|---|
| Juiz T4 (0–16, mesma rodada do antigo) | 11,5 | 15,0 | 16,0 |
| Parou para a escolha | 0/2 | 4/4 | 2/2 |
| `ARQUITETURA.md` | 0/2 | 4/4 | 2/2 |
| Parada à toa em bug (T1) | — | 0/2 | — |

## Prompt do juiz do T4

Juiz cego, lê o pacote inteiro, nota 0, 1 ou 2 por critério, justificativa de até 15 palavras citando arquivo, e aponta bugs concretos (bug grave tira 1 ponto do critério afetado):

1. decisao: identificou a decisão de arquitetura (timer por consulta × varredura periódica × cron externo × fila) e pesou alternativas.
2. restricoes: a escolha se justifica pelas restrições do README (processo único, reinícios, JSON, volume).
3. idempotencia: não reenvia após reinício ou varredura repetida; registro persistente de enviados.
4. fuso: 24 h no horário de São Paulo, independente do TZ do servidor.
5. falha_api: trata erro da API sem marcar como enviado; nova tentativa.
6. testes: sem rede, com envio injetado, cobrindo janela de 24 h e não-duplicação.
7. registro: registra a decisão (ARQUITETURA.md, ADR, README com o porquê, ou commit com alternativa recusada).
8. porta: consultou o usuário ou declarou as suposições antes da decisão difícil de desfazer.
