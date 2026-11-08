---
name: pesquisa-web
description: Pesquisa na web pelo navegador adequado. Use ao pesquisar, buscar fontes, consultar preços ou cotas na web, ou mencionar "pesquisa na web".
---

## Pesquisa na web (obrigatório)

Toda pesquisa na web passa por um navegador, não pelo WebFetch nem pelo WebSearch. O WebFetch resume a página com um modelo pequeno no meio e não roda JS; o navegador lê a página renderizada, e número de preço ou de cota chega intacto.

O navegador é o `playwright-cli`, pelo Bash, na sessão `pesquisa`, com perfil próprio, nunca o perfil nem os cookies do navegador do usuário:

- Abrir: `playwright-cli -s=pesquisa open <url> --headed --persistent`. Headless leva captcha do DuckDuckGo e do Brave (medido em 30/10/2026); com `--headed`, o usuário acompanha na janela.
- Seguir: `playwright-cli -s=pesquisa goto <url>`.
- Ler: `playwright-cli -s=pesquisa --raw eval "() => document.body.innerText"`. Para clicar ou preencher, `snapshot` dá os refs (`click e12`, `fill e5 "texto"`).
- Buscar: `goto` para `https://html.duckduckgo.com/html/?q=<termos>` ou `https://www.google.com/search?q=<termos>`.
- Ao terminar: `playwright-cli -s=pesquisa close`.

Cobrado por `pesquisa-playwright.py`: barra WebFetch e WebSearch quando o `playwright-cli` está no PATH e nunca barra o `claude-code-guide`. Sem o CLI, pesquisar pelo WebFetch é melhor do que não pesquisar.
