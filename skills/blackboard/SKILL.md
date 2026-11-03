---
name: blackboard
description: Use quando o usuário pedir para ver ou fazer as atividades da faculdade no Blackboard (UNIPÊ / Cruzeiro do Sul), perguntar "tem atividade?", "o que tem pra fazer na faculdade", ou mencionar "blackboard".
---

# Blackboard

Entra no Blackboard Ultra da faculdade pelo `playwright-cli` (sessão `blackboard`), lista as atividades pendentes, pergunta quais
fazer, responde Questionário e Dissertativa na tela e **só envia com ok explícito por atividade**.
Caminhos, URLs e seletores ficam em `mapa.md`. Ler antes de navegar.

## Regras fixas

- **Senha nunca passa pelo chat**: o transcript guarda tudo em texto puro. Ela mora no Keychain
  (serviço `blackboard-unipe`, conta = e-mail de login) e vai direto para o campo, sem ser impressa:
  `playwright-cli -s=blackboard --raw fill <campo senha> "$(security find-generic-password -s blackboard-unipe -w)" --submit`.
  Nunca rodar `security ... -w` sozinho nem com `echo`. Senha mandada no chat: não usar e pedir que ele
  a guarde no Keychain.
- O CLI ecoa o valor digitado: sem `--raw`, o `fill` imprime a senha, e o `snapshot` mostra o valor do campo.
  Depois do `fill` da senha, conferir só a URL (`--raw eval "() => location.href"`). Se ainda estiver no
  login, limpar o campo (`--raw fill <campo senha> ""`) antes de qualquer `snapshot`.
- O **código 2FA** pode vir no chat: expira em segundos. Pedir só quando a tela de código aparecer.
- Sem item no Keychain: pedir ao usuário que rode, no próprio terminal (não pelo `!`):
  `security add-generic-password -s blackboard-unipe -a <e-mail de login> -w`.
- Sempre a sessão `blackboard` (`-s=blackboard`, perfil persistente próprio). Nunca a `pesquisa` ou a `linkedin`.
- **Nunca clicar** em botão cujo texto contenha "Enviar", "Submit", "Finalizar", "Concluir" ou "Entregar"
  sem o usuário ter dado ok **àquela atividade** nesta conversa. Um ok não vale para a atividade seguinte.
- Questionário cronometrado ou com tentativa única: avisar antes de abrir, porque abrir já inicia o tempo
  ou consome a tentativa. Abrir só com ok.
- Só Questionário e Dissertativa. Outro tipo (envio de arquivo, fórum) aparece na lista como "pulado".

## Fluxo

1. **Entrar.** `playwright-cli -s=blackboard open <SSO do mapa.md> --headed --persistent`; conferir com
   `playwright-cli -s=blackboard --raw eval "() => location.href"`. Todo comando seguinte leva `-s=blackboard`.
   Sessão expirada: abrir o portal, preencher o e-mail de login (`security find-generic-password -s blackboard-unipe`,
   campo `acct`) e a senha pelo Keychain, pedir o código 2FA no chat e preencher. Seletores do login
   estão no `mapa.md`. Se ainda não estiverem, mapear com `snapshot` antes de preencher e anotar.
2. **Listar.** Ler o painel "Para fazer" com `--raw eval "() => document.body.innerText"`. Mostrar disciplina, atividade, tipo e prazo.
   Painel vazio: dizer que não há nada nos próximos 7 dias e parar.
3. **Escolher.** Perguntar quais fazer (AskUserQuestion com multiSelect).
4. **Responder.** Para cada atividade escolhida: abrir, ler os enunciados com o `eval` do texto ou
   `snapshot` (dá os refs), responder com `click <ref>`/`check <ref>` nas alternativas e `fill <ref>` no texto. Salvar
   rascunho se houver o botão. Não enviar.
5. **Revisar.** Mostrar no chat cada questão, a resposta e uma justificativa de uma linha. Perguntar
   "envio a <atividade>?".
6. **Enviar.** Só com ok: clicar em enviar, ler a tela de recibo e citá-la no chat. Sem ok: deixar como
   está.

Tela mudou ou seletor falhou: `snapshot`, achar o novo caminho e atualizar o `mapa.md`.
