---
name: arquitetura
description: "Use antes de qualquer código em projeto novo e em feature com decisão cara de desfazer: modelo de dado ou onde ele mora, contrato externo, auth, serviço com custo recorrente, síncrono × assíncrono (fila, cron, timer), topologia de deploy. Para com as opções pesadas contra as forças do projeto, espera a escolha do usuário e registra no ARQUITETURA.md. Não use em bug, rename ou ajuste."
---

# Arquitetura antes de codar

Decisão de arquitetura é porta de mão única: custa caro desfazer. Ela se decide contra as forças do projeto, com o usuário escolhendo, e fica registrada. O resto é decisão de código e segue a menor mudança que resolve.

## Quando entra

- **Projeto novo:** sempre, antes do primeiro arquivo de código.
- **Feature:** quando alguma opção que você pesaria é deste tipo, mesmo a que iria para o `Recusado:`:
  - modelo de dado, ou onde o dado mora ou é calculado (aparelho × servidor);
  - contrato externo (API, webhook, formato de arquivo que outro sistema lê);
  - auth e permissão;
  - dependência ou serviço com custo recorrente;
  - síncrono × assíncrono (fila, cron, timer, worker);
  - topologia de deploy.
- **Não entra:** bug, rename, refatoração sem mudança de contrato, texto, estilo, config. Siga direto.
- **Registre** só a decisão que passa nos três: difícil de reverter, surpreende quem chega sem contexto, saiu de um trade-off real.

## 1. Forças

Leia código, README, specs e o `git log` (`Por quê:`, `Recusado:`) antes de propor. As forças moram no `ARQUITETURA.md`, na raiz, numa página:

```markdown
# Arquitetura

## Forças
1. <atributo de qualidade> — <número> (ex.: custo — VPS de 1 GB, US$ 6/mês)
2. ...  (2 a 4, em ordem de prioridade)

## Forma
<3 a 6 linhas: as peças e o caminho do dado>

## Decisões
| data | decisão | alternativas | por quê | revisitar quando |
|---|---|---|---|---|
```

- Repo sem o arquivo: rascunhe pelo código, specs e `git log`, com `?` no que não souber. O rascunho vai na mensagem da parada para o usuário corrigir.
- Repo com `docs/adr/` ou outra convenção de decisão: siga a dele em vez de criar o `ARQUITETURA.md`.
- Projeto novo: estime com número (usuários, requisições/dia, dados em 1 ano, pico) e ponha nas Forças; sem número do usuário, proponha um com `?`. O `ARQUITETURA.md` entra no design doc do brainstorming e é aprovado junto.

## 2. A parada

Antes de escrever código, uma mensagem com as Forças (ou o rascunho) e a tabela:

| opção | complexidade | custo | com 10× | familiaridade | fica mais fácil | fica mais difícil |
|---|---|---|---|---|---|---|

- 2 a 4 opções reais, incluindo a mais simples que funciona.
- Sem recomendar. Termine em "Sua escolha e o porquê?" e pare: nenhum código, arquivo ou instalação antes da resposta.
- Pedido que já traz a opção ("usa o cron do systemd"): não pergunte de novo. Se uma força a contradiz, diga em uma linha e siga; registre igual.

## 3. Depois da escolha

- Força nova no porquê do usuário entra nas Forças.
- Dê a sua recomendação. Se difere da escolha, diga em até 3 linhas o que muda (o que quebra primeiro com 10×, quanto custa) e o usuário decide.
- "passa" ou "pode seguir sem perguntar": siga com a sua recomendação, diga que a escolha foi sua e registre igual.
- Implemente pelo fluxo do superpowers (plano, TDD).
- Durante a implementação, decisão de código com alternativa óbvia segue numa linha `No caminho: X em vez de Y, porque Z`. Decisão de arquitetura nova volta à parada.

## 4. Registro

- Linha nas Decisões: data, decisão, alternativas recusadas, por quê ligado a uma Força, e revisitar quando com gatilho medível ("> 1.000 consultas/dia", "segunda instância do servidor").
- No mesmo commit da feature, sem push:

  ```
  <tipo>: <o que muda>

  Por quê: <a força que decidiu>
  Recusado: <alternativa> — <motivo>
  Olhe: <arquivo:linha onde a decisão mora>
  ```

- Repo sem git: escreva o `ARQUITETURA.md` mesmo assim e ponha o `Por quê:`/`Recusado:` na resposta.
