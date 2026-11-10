---
name: novo-workspace
description: "Use quando o usuário digitar /novo-workspace para criar o workspace do projeto discutido na conversa. Só por invocação manual."
disable-model-invocation: true
---

# novo-workspace

Cria o workspace do projeto desta conversa no padrão do `~/workspace-standard` (`STANDARD.md`). A
conversa é a fonte: o usuário não descreve o projeto de novo. Se a sessão roda na pasta do código do
projeto, essa pasta vira o `repo/` do workspace.

- Script: `python3 ~/workspace-standard/workspace.py`
- Destino: `~/Documents/agent-memory/projects/<nome>`

## Passos

1. **Juntar o que a conversa disse.** O que é o projeto, para quem é, a stack, como verificar que
   funciona, as fontes (repositório, URL, servidor), os prazos e as decisões que o usuário tomou. Se
   a sessão não tem contexto do projeto, faça uma pergunta só, sobre o que é o projeto e para que
   serve, e espere a resposta.
2. **Conferir o script.** Se `~/workspace-standard/workspace.py` não existe, pare e diga que
   procurou nesse caminho.
3. **Escolher o nome.** Use um nome curto, em kebab-case e em inglês, porque o padrão pede nomes em
   inglês (`scheduling-app`, `tutoring-scheduler`). Se `~/Documents/agent-memory/projects/<nome>` já
   existe, pare e pergunte.
4. **Decidir de onde vem o código.**
   - A pasta da sessão é o código do projeto quando tem os arquivos dele e o conteúdo bate com a
     conversa.
   - A pasta da sessão nunca é o código do projeto se for `~` ou ficar dentro de
     `~/Documents/agent-memory/`, ou se for outro projeto.
   - `~/workspace-standard` e `~/new-claude-setup` nunca são movidas, porque hooks e skills dependem
     desses caminhos. Nesses casos, use `--repo <url>` se a
     conversa deu uma URL. Sem URL, não passe nada: o `repo/` nasce com `git init`.
   - Se a pasta tem `AGENTS.md` ou `CLAUDE.md` próprios, pare e pergunte. Separar o que é do
     workspace e o que é do código é trabalho à parte.
5. **Confirmar o mv.** Se a pasta vai ser movida, mostre `<origem> → <destino>/repo` numa linha e
   espere o ok do usuário.
6. **Criar.** Rode
   `python3 ~/workspace-standard/workspace.py new <destino> [--move <pasta> | --repo <url>]`. Se o
   script sair com erro, mostre a mensagem e pare.
7. **Preencher.** Edite só os arquivos abaixo, por cima dos placeholders `<...>` do template:
   - `AGENTS.md`: o que é (duas linhas), Como verificar (o comando real; sem um, escreva
     `a confirmar`), Fontes (a linha `código` aponta para `repo/` e para o remoto, se houver).
   - Em Limites, deixe só a regra padrão de segredos e apague as linhas de exemplo `<regra>`. Regra
     nova precisa de incidente real.
   - `current-state.md`: Agora, Frentes abertas (o que ficou sem decisão) e Próximo passo.
   - No `session-log.md`, troque a linha que o template criou por
     `AAAA-MM-DD — workspace criado a partir da conversa`. Com `--move`, a linha diz também de onde
     o código veio.
   - Para cada decisão que o usuário tomou na conversa, crie um arquivo
     `decisions/AAAA-MM-DD-<slug-em-inglês>.md`.
   - Siga as seções e o cabeçalho do arquivo `*-adopt-workspace-standard.md`, que o `new` criou.
   - Seção que a conversa não cobre fica `a confirmar`.
   - Escreva só o que a conversa disse. O que você deduziu e não foi confirmado vai marcado
     `a confirmar`.
   - Propostas suas que o usuário não aceitou não viram decisão.
   - O `ARCHITECTURE.md` fica como o template deixou, porque quem preenche é a skill `arquitetura`.
8. **Avisar sobre o `.venv`.** Se `repo/` tem `.venv` em qualquer nível, avise o usuário: ele guarda
   caminho absoluto e precisa ser recriado.
9. **Checar e entregar.** Rode `python3 ~/workspace-standard/workspace.py check <destino>`.
   - Se aparecer erro, corrija e rode de novo.
   - Entregue ao usuário a saída do check.
   - Entregue o comando para abrir o workspace: `cd <destino> && claude`.
   - Com `--move`, avise que o histórico desta sessão fica preso no caminho antigo.

## Não faça

- Commit no git do workspace: ele não tem remoto, então não tem identidade de `origin`.
- Editar o código em `repo/` ou reorganizar o código movido.
- Criar spec, skill ou regra de Limites.
