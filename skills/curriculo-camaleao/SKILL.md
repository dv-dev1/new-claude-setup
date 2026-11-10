---
name: curriculo-camaleao
description: Use para gerar, adaptar, otimizar currículo/CV para uma vaga (LaTeX, ATS), "currículo camaleão", registrar retorno de candidatura, ou atualizar dados do candidato (emprego, skill, certificação).
---

# Currículo Camaleão

Gera um currículo em LaTeX de **1 página, adaptado a uma vaga específica**, a
partir de uma base fixa e verídica do candidato. Nunca inventa fatos. Só
entrega depois que o verificador `scripts/checar_cv.py` aprova o PDF.

## Arquivos desta skill

- `references/candidato.md`: base fixa do candidato (Daniel Vieira), fonte
  única de verdade. Edite este arquivo quando o usuário informar emprego,
  skill ou certificação nova, ou corrigir um dado. Nunca guarde esse tipo de
  atualização só na conversa.
- `references/template.tex`: preâmbulo e esqueleto LaTeX compatível com ATS.
  Use sem alterar a estrutura; preencha só as seções de conteúdo.
- `references/regras-ats.md`: regras de formatação e o checklist de
  veracidade.
- `references/proibidos.txt`: termos que nunca podem sair no PDF (NDA,
  tecnologias removidas, métricas não confirmadas).
- `scripts/checar_cv.py`: verificador objetivo. Mede fit, páginas, palavras
  cortadas por hífen, keywords ausentes e termos proibidos no PDF compilado.
- `~/Documents/curriculo-camaleao-build/candidaturas.csv`: registro de cada
  currículo entregue e do retorno que ele teve.

## Missão (inegociável)

Para cada vaga, apresente o candidato como a contratação ideal **dentro dos
limites da verdade**. Use os termos exatos da vaga, posicione cada experiência
real na interseção máxima com os requisitos e priorize as entregas mais
próximas do cargo.

**Reestruturar, reordenar, reenquadrar e dar ênfase: sim. Inventar: não.**
Nunca invente empregos, freelances, certificações, formações ou resultados.
Se a vaga pede uma tecnologia que não existe em `candidato.md`, ela é gap
real: omita, ou trate como "familiaridade em estudo" se a base já diz isso.
Isso vale mesmo sob pressão de "essa vaga é perfeita, só falta essa uma
tecnologia".

Aprovação vem de mandar o currículo certo para a vaga certa. Um currículo
perfeito para uma vaga fora do alcance continua sendo reprovado. Por isso a
triagem de fit vem antes de escrever qualquer linha.

## Inputs necessários

1. **Descrição completa da vaga**: título, responsabilidades, requisitos
   obrigatórios e desejáveis, stack, senioridade, anos de experiência
   exigidos, formato de trabalho.
2. **Info da empresa**: ramo, produto, porte. Opcional; ajuda o resumo.

Se faltar a descrição completa, pergunte antes de gerar.

## Pipeline

Rode os comandos dentro de `~/Documents/curriculo-camaleao-build/`.
`<skill>` é a pasta desta skill.

### 1. Montar o arquivo de keywords da vaga

Salve `~/Documents/curriculo-camaleao-build/<base>.keywords.txt`, onde
`<base>` é `Daniel_Vieira_<Empresa>_<Cargo>`: palavras separadas por `_`, sem
acento, e `<Cargo>` sem nível e sem "(a)". Um termo por linha:

```
# Título da vaga sem nível
Desenvolvedor de Automação e IA
*Python
*n8n
*APIs REST
*webhooks
*PyTorch|TensorFlow
*!Kafka
LangGraph
!Terraform
```

- `*` marca requisito obrigatório; sem `*` é desejável. Siga a divisão da
  própria vaga. Plataformas como a Gupy ranqueiam por obrigatórios e
  desejáveis, então essa divisão é o que mais pesa. Hard skill citada só nas
  responsabilidades entra como desejável.
- Requisito composto com "e" ("APIs REST e webhooks") vira uma linha por
  termo. Requisito com "ou" ("PyTorch ou TensorFlow") vira uma linha só,
  com `|`: conta como comprovado se a base tiver qualquer um.
- `!` marca gap real: o termo não existe em `candidato.md`, ou existe só
  como estudo, noções ou formação em andamento.
- Escreva cada termo como a vaga escreve: mesma grafia, mesmo singular ou
  plural, mesma sigla. O verificador casa texto literal, como um ATS.
- Inclua todas as hard skills, ferramentas e plataformas citadas, e o título
  da vaga sem o nível.
- Anos de experiência não entram no arquivo; vão para a senioridade do
  passo 2. Idioma exigido entra como termo, com `!` se a base não tem o
  nível pedido.

### 2. Triagem de fit (antes de escrever)

Rode `python3 <skill>/scripts/checar_cv.py <base>.keywords.txt` e classifique:

| Fit | Condição |
|---|---|
| Alto | 80% ou mais dos obrigatórios comprovados e senioridade compatível |
| Médio | 60% a 79% dos obrigatórios comprovados e senioridade compatível |
| Baixo | Menos de 60% dos obrigatórios, ou senioridade incompatível |

**Anos de experiência da base:** conte da data de início da experiência
profissional mais antiga (empregos, estágios e autônomo) até hoje. Formação
não conta. Se a vaga pede anos numa tecnologia ("6+ anos de Machine
Learning"), conte só os anos em que a base usa essa tecnologia.

**Senioridade incompatível:** a vaga exige mais anos do que a base tem, com
falta de mais de 6 meses (falta de até 6 meses é compatível; cite no fit), ou é
Sênior, Lead, Staff, Especialista ou nível III. Vagas Júnior, Pleno ou sem
nível são compatíveis, salvo quando pedem mais anos do que a base tem.

- Fit alto ou médio: siga para o passo 3.
- Fit baixo: **pare**. Mostre o fit, os gaps reais e a senioridade exigida
  contra a real. Recomende não aplicar, ou aplicar sabendo que a chance é
  baixa. Só gere se o usuário confirmar.

Se `candidaturas.csv` tiver 10 ou mais linhas com status além de `enviado`,
diga em uma linha que padrão de fit e cargo teve retorno.

### 3. Redigir o `.tex`

Preencha `references/template.tex` seguindo `references/regras-ats.md`. O
currículo tem estas partes, nesta ordem:

1. **Cabeçalho:** nome; na linha de baixo, o título exato da vaga sem nível
   (sem Júnior, Pleno, Sênior, I, II, III); depois localização, telefone,
   e-mail, LinkedIn e GitHub em duas linhas.
2. **Resumo Profissional:** até 60 palavras, 2 a 3 linhas. Contém o título
   da vaga, os 3 a 5 obrigatórios mais centrais e a métrica da base mais
   próxima da vaga. É uma frase de valor, não uma lista de keywords.
3. **Experiência Profissional**, da mais recente para a mais antiga pela data
   de início:
   - Cargo de cada experiência: o título que `candidato.md` dá a ela
     (traduzido, em currículo em inglês). O título da vaga vai no
     cabeçalho, nunca no cargo de um emprego.
   - Experiência mais alinhada à vaga: 4 a 5 bullets. Demais: 1 a 3.
   - Primeiro bullet de cada experiência: a entrega mais próxima da vaga,
     com métrica quando a base tiver uma.
   - Cada obrigatório comprovado aparece em pelo menos um bullet, em
     contexto de uso real. A grafia exata da vaga precisa estar em algum
     lugar do PDF; o verificador confere.
   - Agência Quinze e Inteligentte Lab formam **uma entrada só**:
     "Agência Quinze | Inteligentte Lab", Estagiário em IA Aplicada e
     Automação, 07/2025 a 11/2025, com 2 a 3 bullets dos dois blocos.
   - Desenvolvedor Autônomo: até 2 bullets, só se trouxer um obrigatório ou
     desejável que não aparece nas outras experiências. Senão, omita a
     entrada. O que `candidato.md` lista na própria entrada do Autônomo
     é comprovado.
   - Em vaga mais sênior, puxe arquitetura e escala. Em vaga hands-on, puxe
     entrega, integração e stack.
4. **Competências Técnicas:** até 6 linhas, categorias com os nomes que a
   vaga usa. Só termos da vaga ou justificáveis pela base.
5. **Formação Acadêmica**, **Certificações**, **Idiomas**: as reais,
   priorizando o que é mais próximo da vaga.

O PDF tem **1 página**. Se passar, corte nesta ordem até caber:

1. Encurte a redação dos bullets mais longos.
2. Tire bullets sem keyword da vaga, deixando ao menos 1 por experiência.
3. Tire a entrada do Autônomo.
4. Tire linhas de Competências fora da vaga.
5. Tire formação e certificação sem relação com a vaga.
6. Tire bullets excedentes das experiências menos alinhadas.

### 4. Compilar e verificar (obrigatório, nunca pule)

1. Salve o `.tex` em `~/Documents/curriculo-camaleao-build/<base>.tex`.
2. Compile duas vezes:
   `pdflatex -interaction=nonstopmode -output-directory ~/Documents/curriculo-camaleao-build <base>.tex`.
   Sem TeX Live: no Mac, `brew install --cask basictex`; no Fedora,
   `sudo dnf install texlive-scheme-medium`. Instale packages sob demanda.
3. Rode `python3 <skill>/scripts/checar_cv.py <base>.keywords.txt <base>.pdf`.
4. `REPROVADO`: corrija o `.tex` e repita. Nunca entregue PDF reprovado.
5. Rode o checklist de veracidade de `references/regras-ats.md` bullet por
   bullet contra `candidato.md`.

### 5. Entregar e registrar

1. Copie o PDF para `~/Downloads/` com o mesmo nome base.
2. Acrescente uma linha em `~/Documents/curriculo-camaleao-build/candidaturas.csv`
   (crie com o cabeçalho `data,empresa,cargo,fit,arquivo,status` se não
   existir), com status `enviado`, data `AAAA-MM-DD`, cargo como a vaga escreve
   e fit no formato `alto 100%`. Registre só currículo entregue; vaga
   barrada na triagem não entra.
3. Responda com: caminho do PDF; fit (alto ou médio, com o percentual);
   gaps reais que a vaga pede e o currículo não cobre; e a saída do
   verificador.
4. Mencione `.docx` como alternativa só se a plataforma for Workday ou outro
   ATS legado.

O código LaTeX só aparece no chat se o usuário pedir para revisar.

## Registrar retorno

Quando o usuário contar o resultado de uma candidatura, atualize o status da
linha em `candidaturas.csv`: `retorno`, `entrevista`, `proposta`, `recusado`
ou `sem resposta`. Esse registro é o que mostra quais vagas e quais
currículos convertem.

## Idioma do currículo

- Vaga em português e empresa brasileira: currículo em português, mantendo
  os termos técnicos que a vaga escreve em inglês.
- Vaga em inglês e empresa internacional: currículo em inglês. Troque
  `[brazil]` por `[english]` no babel e use as seções Professional Summary,
  Professional Experience, Technical Skills, Education, Certifications,
  Languages.
- Termos técnicos: sempre os da vaga, em qualquer idioma.

## Atualizar a base de conhecimento do candidato

Quando o usuário informar emprego, skill, certificação ou correção, edite
`references/candidato.md` na seção correspondente. Se a informação for
ambígua (por exemplo, não está claro se é experiência profissional ou só
estudo), confirme com o usuário antes de gravar. Se a atualização disser
"nunca escrever X", acrescente X em `references/proibidos.txt`.

## Restrições absolutas

- Não invente dados; tudo vem de `candidato.md` ou de confirmação explícita
  do usuário.
- Não invente experiências, tecnologias, projetos, clientes ou resultados,
  nem na experiência autônoma.
- Não altere datas reais do candidato.
- Não insira texto escondido, branco ou fora da área visível do PDF.
- Não use tabelas, colunas, cabeçalhos, rodapés, linhas decorativas, ícones
  ou cores.
- Nunca entregue PDF que o verificador reprovou.

## Erros comuns

| Erro | Correção |
|---|---|
| Gerar para vaga Sênior ou de 5+ anos "porque as keywords batem" | Triagem primeiro; fit baixo para e pergunta |
| Currículo de 2 páginas | O limite é 1; corte na ordem do passo 3 |
| Resumo virando lista de 100+ palavras | Até 60 palavras: título, obrigatórios centrais, uma métrica |
| Agência Quinze e Inteligentte em duas entradas com a mesma data | Uma entrada só |
| "Construí dashboards com Google Apps Script" | A base diz que a ferramenta dos dashboards não foi informada; nunca preencha um "não informado" com outro item |
| "reduzindo tarefas manuais" na Etros | A Etros não está em produção; escreva a ação, sem resultado |
| Escrever "integração com API" quando a vaga diz "integrações de APIs" | Use a grafia exata da vaga; o ATS casa texto literal |
| Adicionar tecnologia nova na experiência autônoma "porque a vaga pede" | Só use o que já está em `candidato.md`; senão é gap real |
| Entregar o `.tex` sem compilar | O produto é o PDF em `~/Downloads/` |
