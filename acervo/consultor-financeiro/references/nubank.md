# Os CSVs do Nubank

Detalhe denso que só se consulta na hora de parsear. É também o primeiro
arquivo a quebrar quando o Nubank mudar o export — o conserto mora aqui, não
no corpo da skill.

## Os dois formatos

**Extrato da NuConta** — `Data,Valor,Identificador,Descrição`

```
14/08/2026,-150.00,6a45b227-0466-4de4-8734-e1bee93468dc,Compra no débito - PAGUE MENOS     1464
```

Data `DD/MM/AAAA`. Valor já vem com o sinal certo: negativo sai, positivo
entra. `Identificador` é UUID — chave de deduplicação de graça, sem hash.

**Fatura do cartão** — `date,title,amount`

```
2026-08-14,Uber* Trip,23.90
```

Data ISO. **O sinal é invertido:** `23.90` é uma compra, ou seja, dinheiro
saindo, e um estorno vem negativo. O parser nega o valor da fatura para que
no ledger negativo signifique saída sempre. Errar isso troca o sinal de todo
gasto de cartão e nenhuma soma depois faz sentido.

Fatura não tem identificador. A chave é
`fatura:sha1(competencia|data|valor|descricao_normalizada)[:12]`, e duas
compras idênticas no mesmo dia ganham sufixo `#2`, `#3` pela ordem no arquivo
— sem isso um dos dois cafés de R$ 7,00 some do ledger em silêncio.

## Competência não é a data

Uma compra de 14/08 cai na fatura de setembro se o cartão fecha dia 3. A data
não diz em que fatura o dinheiro vence, então `--competencia AAAA-MM` existe
para a fatura. Guarde o dia de fechamento no `perfil.md`.

## As três armadilhas que inflam tudo

Todas viram a categoria `interno`, e o resumo tira `interno` dos dois lados.

1. **`Pagamento de fatura`** no extrato é o **mesmo dinheiro** que já está
   linha a linha na fatura. Somar os dois infla o gasto em quase 2x.
2. **`Resgate RDB` / `Aplicação RDB`** é o saldo dele rendendo e voltando. No
   Nubank o dinheiro parado fica em RDB e resgata sozinho quando ele gasta —
   um resgate casado com uma saída no mesmo dia e no mesmo valor é o produto
   funcionando, **não** aperto de caixa. Medido nos extratos de abril, junho e
   julho de 2026: o líquido de RDB no mês fica entre R$ 2 e R$ 209, o que
   confirma que é vaivém de saldo. Contar resgate como entrada infla a renda
   em mais de R$ 1.000/mês.
3. **Pix para ele mesmo** (mesmo CPF, outro banco — Inter, Mercado Pago) é
   dinheiro trocando de bolso. R$ 1.786 em três meses no caso dele.

## Reembolso: o gasto que não é dele

Ele paga a conta e os amigos devolvem por Pix. Em 17/06/2026 recebeu R$ 73,33
de duas pessoas e pagou exatamente R$ 73,33 da fatura. A fatura fica maior que
o gasto real dele.

O script não adivinha isso — entrada de pessoa física logo depois de uma
compra é candidata a reembolso, e quem confirma é ele. Quando confirmar,
categorize os dois lados como `reembolso` e trate como `interno` na leitura.

## Vários pagamentos de fatura num mês não provam rotativo

Abril teve 3, junho 5, julho 2. Isso tanto pode ser adiantamento — pagar a
fatura aberta aos poucos, que é disciplina — quanto rotativo, que é juro caro.
**O extrato sozinho não distingue os dois.** Só a fatura mostra a linha de
juros. Não acuse rotativo sem ela: pergunte, ou peça o CSV da fatura.

## Como ele exporta

- **Extrato:** app, Conta, ícone de recibo, escolher o mês, "Exportar".
- **Fatura:** app, Cartão de crédito, abrir a fatura do mês, "Exportar" e
  escolher CSV. É **uma fatura por vez** — sem elas não existe cálculo de
  parcelas a vencer, que é o número central da skill.
