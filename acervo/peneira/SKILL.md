---
name: peneira
description: Use para caçar/procurar vagas, "vagas novas", Easy Apply (LinkedIn), registrar candidatura ou resposta, "placar de candidaturas", "peneira", "onde eu apliquei".
---

# Peneira

Caça vagas em fontes de API pública, filtra pelo perfil real do candidato, e
mantém o ledger de candidaturas que permite medir **taxa de resposta por
canal** — o número que decide onde vale gastar o próximo currículo.

As fontes públicas não pedem login. O LinkedIn é a exceção: usa a sessão
`linkedin` do `playwright-cli` por `eval`, e a skill nunca lê nem grava
cookie (o csrf é lido dentro da aba e não sai dela).

## Arquivos

- `buscar.py` — coletores, filtro e ledger. Só stdlib, sem dependência.
- `perfil.json` — cargos-alvo, termos de exclusão, modelos e cidades aceitas.
  Editar aqui quando o usuário mudar o que procura, nunca guardar na conversa.
- `linkedin.py` — parsing e chamadas SDUI do LinkedIn, sempre por `playwright-cli -s=linkedin eval` na página do LinkedIn.
- `test_peneira.py` — checagem offline do filtro, do dedupe e do placar.
- `test_linkedin.py` — o mesmo para o LinkedIn, sobre fixtures sanitizadas.

O ledger fica em `~/.local/share/peneira/vagas.db` (SQLite), fora da skill: são
dados do usuário, não código.

## Fontes

| Fonte | Endpoint | O que já vem pronto |
|---|---|---|
| GitHub `vagas` | `api.github.com/repos/<repo>/issues` | label de nível, contrato e modelo |
| Portal Gupy | `employability-portal.gupy.io/api/v1/jobs?jobName=&offset=&limit=` | `workplaceType`, `type`, `publishedDate`, descrição completa |
| Remotive | `remotive.com/api/remote-jobs` | `candidate_required_location` |
| Himalayas | `himalayas.app/jobs/api?limit=20&offset=` | `locationRestrictions`, `seniority` |
| RemoteOK | `remoteok.com/api` | `location`, faixa salarial |
| Jobicy | `jobicy.com/api/v2/remote-jobs?count=50&tag=` | `jobGeo`, `jobLevel` |
| LinkedIn (Easy Apply) | `/jobs/search/?f_AL=true&f_TPR=r86400` via `playwright-cli eval` | id e título na busca; empresa, modelo e descrição na página da vaga |

Remotive, Himalayas, RemoteOK e Jobicy são portais de vaga remota internacional e passam por
`regioes_aceitas`: vaga restrita a "United States" ou "Europe" é descartada na
coleta. Elas rendem pouco em volume (dezenas, não centenas) porque a maioria
das vagas remotas dessas plataformas é fechada para os EUA — isso é o mercado,
não defeito do coletor. O Remotive expõe só 18 vagas na API pública; o
Himalayas capa `limit` em 20 e o volume vem do `offset`.

## Ranking

`listar` e `lote` ordenam por `nota()`: quantas tecnologias do candidato a vaga
cita (título conta em dobro), mais `bonus_nivel` quando a vaga está em
`niveis_aceitos`, mais `bonus_recente` quando foi publicada dentro de
`dias_recentes`. Vaga fora da faixa de senioridade perde metade dos pontos, mas
não é vetada.

O bônus de nível existe porque vaga júnior costuma ter descrição curta e
perderia sempre para uma vaga sênior que lista a stack inteira da empresa.

As duas classificam nível, contrato e modelo de trabalho como campo
estruturado. Não gaste token de LLM reclassificando o que já vem classificado —
foi esse gasto que dominou a conta na versão anterior deste projeto.

## Manutenção do perfil

`perfil.json` decide o que entra. Quando ele mudar, rode `revisar`: as vagas já
guardadas são reavaliadas e as que não passam viram `cortada`, sem tocar em
nenhuma que já foi aplicada. Sem esse passo, um ajuste de filtro só vale para as
vagas futuras.

Duas armadilhas já pagas nesse arquivo:

- **Nível não entra em `cargos`.** Colocar "junior" ali fez entrar "Analista de
  Departamento Pessoal Júnior" — qualquer título com a palavra passava.
  Senioridade é assunto do ranking (`bonus_nivel`), não do filtro de cargo.
- **`stack_excluir` casa por lookaround, não por `\b`.** `\b` não funciona antes
  de um ponto, então `.net` nunca casaria; e sem o lookahead, "java" barraria
  "javascript".

## Comandos

```
python3 buscar.py cacar                    # coleta, grava as novas, imprime
python3 buscar.py listar [--quantas N]     # aprovadas ainda sem candidatura
python3 buscar.py ver <chave>              # descrição completa da vaga
python3 buscar.py marcar <chave> <estado>  # nova|aplicada|resposta|entrevista|rejeitada|silencio
python3 buscar.py lote [--quantas N]        # prepara as N melhores de uma vez
python3 buscar.py revisar                  # reaplica o perfil ao ledger
python3 buscar.py placar                   # taxa de resposta por fonte
python3 buscar.py cacar --fonte linkedin   # Easy Apply, 24 h (cai para 7 dias)
python3 buscar.py aplicar --quantas N --seco  # tabela do lote, sem enviar
python3 buscar.py aplicar --quantas N      # envia as aprovadas no --seco, 30 s ± 5 entre elas
python3 buscar.py responder "<pergunta>" "<valor>"
python3 buscar.py curriculo <chave> --pdf <pdf> --ats <nota> [--mensagem <texto>]
```

## Fluxo de uma candidatura

1. `cacar` — traz o que apareceu desde a última vez. Vaga já vista não repete.
2. Mostre as novas ao usuário e deixe ele escolher. Não escolha por ele.
3. `ver <chave>` — pega a descrição completa já coletada.
4. Invoque a skill `curriculo-camaleao` com essa descrição como "descrição
   completa da vaga". Ela cuida da análise, do LaTeX, da validação ATS e do PDF.
   Não gere currículo aqui.
5. Depois que o usuário enviar: `marcar <chave> aplicada`.
6. Quando chegar retorno: `marcar <chave> resposta` (ou `entrevista`,
   `rejeitada`). Sem esse passo o `placar` não mede nada.

## Quando o usuário perguntar onde vale aplicar

Rode `placar` e responda com o número, não com opinião. Enquanto houver menos de
~20 candidaturas registradas, diga que a amostra ainda é pequena — uma taxa
sobre 3 envios não distingue canal bom de sorte.

## `preparar` — o pacote de candidatura

```
python3 buscar.py preparar <chave>
```

Cria `~/Documents/peneira/<data>-<empresa>-<vaga>/` com:

- `vaga.md` — descrição completa e os campos já extraídos (empresa, modelo,
  contrato, nível, URL de candidatura, e-mail de contato, formulário).
- `email.txt` — rascunho, só quando a vaga traz e-mail de contato.

`respostas.json` guarda o que se repete em todo formulário (nome, contato,
stack curta, disponibilidade). Campo vazio ali é dado que o candidato ainda não
informou: **pergunte, nunca preencha por conta própria** — pretensão salarial
inventada vira compromisso no processo seletivo.

Depois do `preparar`:

1. Invoque `curriculo-camaleao` passando o conteúdo de `vaga.md` como descrição
   da vaga. Peça que o PDF final seja salvo na mesma pasta do dossiê.
2. Personalize `email.txt` com a experiência real que casa com a vaga — o
   rascunho é genérico de propósito. Só use o que está em `candidato.md`.
3. **O envio é do usuário.** Não dispare e-mail, não preencha formulário e não
   automatize candidatura em plataforma. Entregue o pacote pronto e o caminho
   do PDF; quem clica é ele. A exceção é o Easy Apply do LinkedIn, pela seção
   abaixo, e só depois do ok do usuário ao lote.
4. `marcar <chave> aplicada` depois que ele confirmar o envio.

## LinkedIn: Easy Apply automático

Decidido pelo usuário em 24/10/2026, revendo a recusa anterior: o termo de uso
do LinkedIn proíbe automação e a punição pode ser restrição do perfil. O lote
pequeno, o intervalo de 30 s ± 5 e o ok obrigatório reduzem o risco, não o
eliminam.

1. Abra a sessão: `playwright-cli -s=linkedin open https://www.linkedin.com/feed/ --headed --persistent`.
   `exit 2` com "sessão do LinkedIn expirada" = peça login nessa janela e pare.
2. `cacar --fonte linkedin`. Pergunte ao usuário quantas vagas quer no lote.
3. `aplicar --quantas N --seco` e leia as pendências. `responder` guarda cada
   resposta em `formulario_linkedin` de `respostas.json`, e vale para as
   próximas vagas:
   - Sim/Não: `responder` com `sim` ou `não` (outro texto volta como pendência).
   - Pergunta cuja resposta está em `curriculo-camaleao/references/candidato.md`
     (ex.: anos de experiência com uma tecnologia) → `responder` com o número
     que a base sustenta, e diga ao usuário o que gravou.
   - Pergunta que a base não responde → pergunte ao usuário; nunca estime.
     Grave com `responder`: vale para as próximas vagas.
   - `tipo … não mapeado` → a vaga vira `cortada`; não há como responder.
4. Para cada vaga sem pendência: `ver <chave>` e a skill `curriculo-camaleao`
   com essa descrição. Depois `curriculo <chave> --pdf <pdf> --ats <nota>`.
   Nota >= 90: escreva uma mensagem curta ao recrutador (20 a 400 caracteres,
   só com fatos de `candidato.md`) e passe em `--mensagem`; o script aceita sem,
   mas o LinkedIn pode recusar o preferencial.
   Repita 3–4 até o `--seco` só mostrar `pronta` ou pendência que o usuário não
   respondeu.
5. `aplicar --quantas N --seco` de novo e mostre a tabela. ★ = preferencial.
   Espere o "ok" explícito do usuário a este lote. O `--seco` grava as vagas
   `pronta` e a ★ de cada uma em `lote_aprovado.json`, ao lado do ledger; o
   envio usa essa ★, não a recalcula.
6. `aplicar --quantas N`. Mostre a última linha ("X de Y candidaturas
   enviadas") e as falhas. `placar` confirma a conta na fonte `linkedin`.

O script cobra o ok: sem `--seco` do mesmo dia, `aplicar` sai com 1 e não toca
no LinkedIn; só envia as vagas que o `--seco` mostrou como `pronta` (as outras
saem como "fora do lote aprovado"); e gasta o ok na execução, então cada envio
pede novo `--seco` e novo ok.

Regras que o script já cobra: só Easy Apply (vaga externa vira `cortada`);
ATS < 85 vira `cortada` e não envia; "seguir empresa" sempre desmarcado;
preferencial só com ATS >= 90, elegibilidade e crédito do LinkedIn e menos de 2
no mês; pendência deixa a vaga `nova`, sem consumir cota. Vaga `cortada` pelo
LinkedIn (externa, tipo não mapeado, ATS < 85, envio sem confirmação) guarda o
`motivo` no dossiê `linkedin-<id>.json` e o `revisar` não a reabre; para
tentar de novo, use `marcar <chave> nova`, que também apaga o `motivo`.

Comando com `exit 2` em qualquer passo: peça login e pare. Para retomar, refaça
o passo interrompido (1–4) e siga até o passo 5: novo `--seco` e novo ok. O ok
vale só para a tabela que o usuário viu.

## Pretensão salarial

`preparar` calcula e escreve no dossiê. A regra, decidida pelo candidato em
06/09/2026: estimar o valor da vaga e pedir abaixo dela, na proporção de
`desconto_pretensao` em `respostas.json` (hoje 15%). Mudar o número é editar
esse campo — não há percentual escrito no código.

Ordem de precedência:

1. **Salário declarado na vaga** vence sempre. O script pega o maior valor em
   `R$` da descrição — vale-refeição e auxílio são menores que o salário.
2. Sem declaração, usa `faixas_clt_mensal` de `respostas.json` pelo nível da
   vaga, multiplicado por `multiplicador_pj` quando o contrato é PJ.

As faixas são **estimativa de mercado, não dado verificado** — estão em
`respostas.json` justamente para o candidato corrigir. O dossiê sempre mostra de
onde o número veio, então dá para conferir antes de responder o formulário.

Ao informar a pretensão num processo, diga o número do dossiê; se o candidato
quiser mudar, mude — o cálculo é ponto de partida, não regra.

## Validação

```
python3 validar.py
```

Mede cada afirmação sobre a skill e imprime a evidência: testes unitários,
fontes vivas, precisão da fila inteira (não uma amostra), lote sem repetição e
dentro da faixa, dossiês completos, pretensão dentro do piso, ledger ponta a
ponta, cron instalado e comprovadamente disparado.

Rode depois de mexer em `perfil.json`, nos coletores ou no cron.

`FALHA` é defeito e derruba a pipeline (`exit 1`). `PENDENTE` é o que ainda não
aconteceu — currículo dos dossiês, candidaturas registradas — e não derruba:
são fatos sobre o estado, não código quebrado. Um deles vira `PASSA` sozinho
quando o usuário aplicar e marcar.

Para provar que o cron dispara sem esperar as 8h: instale uma linha temporária
para dois minutos à frente com o marcador `# peneira-teste`, escrevendo em
`/tmp/cron-fire.log`, e remova depois. `validar.py` lê esse arquivo como prova.

Três falsos positivos já corrigidos no próprio validador — vale saber antes de
mexer nele: "financeiro" e "atendimento" aparecem no *ramo* da empresa, não no
cargo (por isso o corte olha só o que vem antes de `(`, `|` ou travessão), e
`faixas_clt_mensal` mora em `respostas.json`, não em `perfil.json`.
