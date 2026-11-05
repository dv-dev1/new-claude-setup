# agenda-consultas

Agenda da Clínica Boa Vista: a recepção marca as consultas num painel, e este serviço guarda e expõe a agenda.

## Como roda

- Um VPS em São Paulo (1 vCPU, 1 GB de RAM), com Node 22 e o processo único `npm start`, sob systemd. O serviço reinicia a cada deploy, umas duas vezes por semana.
- As consultas ficam em `data/consultas.json`, gravado pelo painel da recepção. Não há banco de dados.
- Volume: cerca de 120 consultas por dia, em dois médicos.

## Rotas

- `GET /consultas` lista as consultas.
- `GET /consultas/:id/confirmacao` devolve o texto de confirmação da consulta.

## Testes

`npm test`
