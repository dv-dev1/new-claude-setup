# Mapa do Blackboard (UNIPÊ / Cruzeiro do Sul)

Descoberto em 27/09/2026. Atualizar quando o DOM mudar.

## Entrada
- Portal: `https://novoportal.cruzeirodosul.edu.br/gfa/home` (Área do Aluno, Angular).
- O botão "Acesso ao Ambiente Virtual" é um `<a>` sem `href` com `img[alt="Acessar Ambiente Virtual"]`.
  Ele chama `window.open`, que o `click` do browser automatizado não segue (medido no cmux). Não clicar: ir direto à URL do SSO.
- SSO (SAML, usa a sessão do portal):
  `https://bb.cruzeirodosulvirtual.com.br/auth-saml/saml/login?apId=_5073_1&redirectUrl=https%3A%2F%2Fbb.cruzeirodosulvirtual.com.br%2Fultra`
- Destino logado: `https://bb.cruzeirodosulvirtual.com.br/ultra/course` (Blackboard Ultra).
- Sessão expirada: a URL fica no domínio do portal ou numa tela de login, e o texto não tem "Disciplinas".

## Login do portal
Mapeado em 30/10/2026. O SSO expirado cai em `login.microsoftonline.com/.../saml2` (Microsoft Entra).
- E-mail: `input[type=email]` + `--submit`. O `snapshot` logo depois pode vir velho; ler `innerText`.
- Com o perfil persistente, a Microsoft pulou a senha e foi direto ao 2FA por SMS ("Enter code").
- Código: `input[name=otc]` (tel). O usuário também pode digitar no navegador headed e avisar.
- Depois do código, volta sozinho para `/ultra/course`.

## Lista de atividades
- Painel "Para fazer" na própria `/ultra/course`, com três blocos: "Com atraso", "Vencimento hoje" e
  "Vencimento em breve". Cobre só 7 dias para trás e 7 para frente.
- Vazio: os textos "Nenhum item atrasado", "Nenhum item com entrega para hoje", "Nenhum item com entrega
  para os próximos 7 dias".
- A API REST pública (`/learn/api/public/v1/...`) devolve `403 AccessDenied`: ela exige OAuth de app
  registrado. Não usar.

## Tela da atividade
Mapeada em 20/10/2026 numa atividade de envio (texto + arquivo). Questionário ainda não mapeado.
- `/assessment/<id>/overview` mostra prazo, pontos e tentativas sem iniciar nada. A URL
  `/assessment/<id>/attempt/create` (ou o botão "Ver instruções") abre o envio.
- Abrir pelo outline: clicar na pasta (`button` com o texto exato, ex. "Atividades") e depois no
  título do item; `[data-content-id="<id>"]` identifica a linha.
- Texto: editor Quill `#bb-editorassignment-attempt-authoring-submission`. Preencher por `eval` com
  `innerHTML` em `<p>` + `dispatchEvent(new Event('input'))`; "Contagem de palavras" confirma.
- Arquivo: `set-input-files --selector 'input[type=file]' --file <a> --file <b>`.
- Rascunho salva sozinho ("Salvo pela última vez HH:MM:SS"). Botões: "Salvar e fechar" e "Enviar".
- PDF de material: o `iframe[src*=bbcswebdav]` redireciona ao doc-viewer; o parâmetro `pdfUrl` é URL
  assinada que baixa com `curl` sem cookie.

## Exercício (questões com editor de texto)
Mapeado em 22/10/2026 (Programação para Dispositivos Móveis).
- Abrir pelo "Para fazer": o título é `.MuiTypography-h5` dentro de um `<a>`; clicar no `<a>` por `eval`.
- Overview: "Iniciar tentativa N" é `a.button-attempt` (não aparece no `snapshot`).
- Editores das respostas: `.guidance-wrapper bb-rich-text-editor .ql-editor`, um por questão, na ordem.
  O último editor (`.freeform-response-editor`) é "Conteúdo adicional", opcional.
- Código: um `<p>` por linha (linha vazia = `<p><br></p>`), espaços normais; a indentação persiste.
  Rascunho salva sozinho; conferir recarregando a página.
- Anexo do enunciado: `[data-bbfile]` tem `resourceUrl`; `fetch` falha (CORS). Abrir em aba nova do
  perfil `blackboard` e pegar a URL assinada final com `get url`.
- Pergunta sem enunciado (medido em 05/11/2026, "1° Prática"): o enunciado fica no material da pasta da aula
  (ex. `Exercício.pptx`). O pptx baixa pelo `originalUrl` do doc-viewer, igual ao PDF; texto com `unzip` dos
  `ppt/slides/*.xml` e imagens em `ppt/media/` (o enunciado pode ser só um print da tela a reproduzir).
- Enviar: há dois `button` "Enviar" (um oculto); clicar no visível (`offsetParent !== null`). Abre o
  diálogo "Enviar exercício?" com outro "Enviar". Recibo: overview mostra "Enviado em DD/MM/AA HH:MM".

## Dentro da disciplina
- Abrir a disciplina: clicar no card pelo texto (o card não aparece no `snapshot`).
  URL fica `/ultra/courses/<id>/outline`.
- Disciplina fora de "Cursos recentes" (ex. Análise de Dados e BI, `_1191256_1`): clicar em
  "Visualizar todos os cursos" e no `h4` com o nome.
- Abas (Mensagens, Avisos, Agenda...): clicar no link da aba (`.js-course-<tool>-tool`). `goto` direto na
  URL da aba às vezes cai em outra aba (medido em 03/11/2026).
- Mensagens do professor: `/ultra/courses/<id>/messages`. Avisos: `/announcements`.
- Grupos: clicar na aba "Grupos" (vai para `/groups/enrollments`; ir direto a `/groups` cai no fluxo de
  atividade). Expandir o conjunto com `#row-<id> .item-expand button` e ler `.group-set-list` por `eval`.
  O aluno só vê o grupo em que está.

## ASG (prova da Área do Aluno, fora do Blackboard)
Mapeada em 30/10/2026. A2 = AS no Blackboard (1,5) + ASG (3,5), aberta em 2 dias fixos (aviso da disciplina).
- Portal: `novoportal.cruzeirodosul.edu.br` > "Ensino superior" > instituição (digitar "UNIP" no campo e
  clicar no botão "UNIPÊ - ...") > "Entrar com email acadêmico" (reaproveita a sessão Microsoft).
- O botão "Plataforma de Provas" da tela de escolha dá alert de erro. Ir por "Portal do Aluno" >
  menu "Vida Acadêmica" > card "Plataforma de Prova"; abre aba nova (`tab-select 1`).
  Antes, fechar o modal da CPA com "Responder depois".
- Aba: `unipe.grupoa.education/avalia-online/instructions/?idRespondentQuestionCollection=<id>`.
  Um caderno só com 10 questões de múltipla escolha por disciplina online; tentativa única; 3h30.
  "Eu li e aceito" + "Iniciar Avaliação" iniciam o cronômetro: só com ok.
- Dentro da prova: uma questão por tela. Alternativa = `.answer-alternative__letter` (clicar no pai);
  marcada fica com fundo `rgb(129, 212, 250)`. Navegar por "Próximo"/"Anterior" (`innerText`).
  Questão com imagem (código, formulário): o texto vem vazio, então tirar `screenshot --full-page`.
- Botão "N/40" abre o painel ("40 Respondidas"). Em seguida "Ir para o resumo" mostra tudo, com `.alternative-selector`
  marcada no mesmo azul. "Enviar respostas" abre um diálogo que pede a "Chave de envio" exibida nele, em 5 caixas
  de um dígito (clicar na 1ª e `type`). Recibo em `/avalia-online/finish`: "Avaliação finalizada... em <data>".

## Itinerário Extensionista (DreamShaper)
Mapeado em 10/11/2026. Itinerário Extensionista 2 = `_1196223_1` (achar pelo campo `#courses-overview-filter-search`
em "Visualizar todos os cursos"; a lista esconde cursos com `.courseUnavailable`).
- Regras no `Plano De Curso Itinerário - Unipê.pptx` (pasta "Funcionamento do itinerário"): só o professor cria o
  projeto/grupo no DreamShaper, depois que cada aluno faz o 1º acesso. Líder manda lista (nome + RGM) pelo BB.
- 1º acesso: pasta "Acessando o Projeto" > "Acesso à Ferramenta de Projeto" > botão "Abrir" visível
  (abre aba nova `cds-ext-pres-cultdesenvsocial-unipe-262.dreamshaper.com/dashboard`; `tab-select 1`).
- Sem grupo: dashboard mostra "Você ainda não tem projetos." Com grupo: card do projeto, 19 etapas, % de conclusão.
- Mensagens: conversa abre clicando em `.message-info`; o texto da thread vem no `innerText` depois de "itens por página".
