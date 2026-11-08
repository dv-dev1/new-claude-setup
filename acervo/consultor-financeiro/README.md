# consultor-financeiro

Skill do Claude Code que transforma os CSVs do Nubank num ledger acumulado e
responde "posso comprar isso?" com o efeito nas faturas dos próximos meses.

Manda o extrato de setembro e ela já tem julho e agosto. Ingestão é idempotente:
mandar o mesmo arquivo duas vezes não duplica linha.

## O que ela responde

```
$ python3 financas.py resumo

COBERTURA: 5 meses — 2026-04, 2026-06, 2026-07, 2026-08, 2026-10
  BURACO na série: 2026-05, 2026-09 — mediana sobre série furada mente.
  CEGO em 2026-04, 2026-06, 2026-07, 2026-08: pagou fatura mas o CSV da fatura
  não foi importado. O gasto do cartão nesses meses só aparece como o total pago.

PARCELAS A VENCER: R$ 5090.28 já comprometidos
  2026-09  R$    888.10
  ...
  2027-03  R$    324.89

MÊS CEGO reconstruído pelas parcelas que ainda aparecem na fatura:
  mês        fatura paga  era parcela  gasto novo
  2026-04         775.19       500.00      275.19
  2026-08        1733.92       888.10      845.82
```

`Parcela 5/10` na fatura de outubro prova que aquela cobrança existiu nos quatro
meses anteriores. Dá para reconstruir quanto de uma fatura antiga já era
compromisso velho sem ter o CSV daquele mês.

## Uso

```
python3 financas.py ingerir ~/Downloads/NU_*.csv
python3 financas.py ingerir ~/Downloads/Nubank_2026-10-03.csv --competencia 2026-10
python3 financas.py resumo
python3 financas.py simular --preco 2500 --parcelas 10
python3 financas.py --self-check
```

Fatura precisa de `--competencia`: a data da compra não diz em que fatura ela
vence. Sem dependência: só `csv`, `hashlib`, `statistics`, `decimal` da stdlib.
`Decimal`, nunca `float` — centavo de fatura não aceita erro de ponto flutuante.

## As três armadilhas que ela evita

1. **Dupla contagem.** `Pagamento de fatura` no extrato é o mesmo dinheiro que
   já está linha a linha na fatura. Somar os dois infla o gasto em quase 2x.
2. **RDB não é renda.** No Nubank o saldo parado rende em RDB e resgata sozinho
   quando você gasta. Contar resgate como entrada infla a renda em mais de
   R$ 1.000/mês.
3. **Gasto é líquido, não bruto.** Quem paga a conta e recebe de volta por Pix
   tem saída bruta muito maior que o gasto real. Usar o bruto reprova compra
   que cabe folgado.

## Onde mora o quê

Lógica neste repositório; **estado fora dele**, em
`~/.claude/consultor-financeiro/` — `ledger.csv`, `perfil.md`, `categorias.csv`.
Essa separação não é organização, é privacidade: o ledger tem nome de
contraparte, CPF mascarado, agência e conta.

`categorias.csv` é o que a skill aprendeu. Corrigiu uma vez, vale para o
passado também — a reingestão reaplica as regras ao que estava sem categoria.
