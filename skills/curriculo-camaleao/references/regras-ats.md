# Regras de formatação ATS e checklist de veracidade

## Formato e estrutura

- **Saída:** LaTeX compilável, gerando PDF pesquisável (texto selecionável).
- **Tamanho:** 1 página. O verificador reprova 2 ou mais.
- **Proibido:** headers, footers, tabelas, colunas, linhas decorativas,
  sombreamento, cores de fonte diferentes de preto, ícones, símbolos além do
  bullet simples e do separador `|`, texto escondido ou branco.
- **Hifenização:** desligada no template. Palavra cortada no fim da linha
  ("Lang-" e "Chain") vira dois tokens e o ATS perde a keyword. Nunca
  religue.
- **Fonte:** preta, 10pt, `lmodern`.
- **Seções padronizadas** (ou equivalentes em inglês): Resumo Profissional,
  Experiência Profissional, Competências Técnicas, Formação Acadêmica,
  Certificações, Idiomas.
- **Contato no corpo do documento**, nunca em header ou footer, em duas
  linhas separadas por `|`.
- **Datas:** sempre `MM/AAAA` (ex.: `11/2025 -- Presente`), consistentes no
  documento inteiro. Se a base só tem o ano, use só o ano; nunca invente o
  mês.
- **Cabeçalho de cada experiência:** linha 1 com cargo em negrito e datas à
  direita (`\hfill`); linha 2 com empresa e local separados por `|`.
- **Bullets:** só `\item` simples, sem sub-bullets.
- **Keyword matching:** use a grafia exata da vaga, sobretudo em Resumo,
  Experiência e Competências. Forma extensa mais sigla quando a vaga usa as
  duas (ex.: "Retrieval-Augmented Generation (RAG)"). Não abrevie a menos que
  a própria vaga abrevie.
- **Modelo base:** `template.tex` deste diretório, sem alterar a estrutura.

## Regras de conteúdo

- **Veracidade absoluta:** nenhum fato inventado; tudo vem de `candidato.md`
  ou de confirmação explícita do usuário na conversa.
- **Quantifique** com os números que a base tem. Sem número na base, escreva
  a ação e o escopo, sem inventar resultado.
- **Verbo de ação** no início de cada bullet (Desenvolvi, Integrei, Reduzi,
  Atuei...). Respeite as travas da base: onde ela diz "atuei no time", nunca
  escreva "conduzi" ou "migrei".
- **Bullet em Contexto, Ação, Resultado**, com o resultado só quando a base
  tiver um.
- **Evite genéricos:** toda skill listada é verificável; soft skill só
  demonstrada por conquista. Sem clichês ("proativo", "dinâmico", "team
  player").

## Checklist de veracidade (depois do verificador, antes de entregar)

O verificador mede formato e keywords. Ele não sabe se uma frase é verdade.
Para cada bullet do currículo, confirme:

- [ ] O bullet corresponde a um item de `candidato.md`, na mesma experiência.
- [ ] Nenhum detalhe que a base marca como "não informado" foi preenchido
  com outro item da base. "Construí dashboards com Google Apps Script"
  falha: a ferramenta dos dashboards não foi informada. Juntar dois itens
  confirmados da mesma experiência numa frase natural é permitido.
- [ ] Todo resultado ("reduzindo", "aumentando", "otimizando", percentual,
  volume) está na base. A Etros não está em produção: nenhum resultado lá.
- [ ] As travas escritas na base para aquele item foram seguidas (NDA,
  "nos primeiros meses após a migração", "atuei", "não nomear").
- [ ] Tecnologia marcada como "em estudo" ou "noções" na base não aparece
  como experiência profissional.
- [ ] Gap real (`!` no arquivo de keywords) não aparece no PDF, ou aparece
  só como "em estudo" quando a base diz isso.
