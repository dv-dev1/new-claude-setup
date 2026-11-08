---
name: readme-padrao
description: 'Padrão visual e de conteúdo de README. Use ao criar repositório, escrever ou redesenhar README.md, ou documentar projeto no GitHub.'
---

## README padrão

Híbrido, não norma: visual do perfil `guithepc`, conteúdo forte, narrativa "por quê" antes de "como". Esqueleto pronto em `references/template.md`; copie e preencha, não reinvente.

### Ordem das seções

| # | Seção | Regra |
|---|---|---|
| 1 | Cabeçalho centralizado | título, uma frase, 4 a 6 badges, menu de âncoras, print |
| 2 | Why | o problema e a ideia, com 1 Mermaid |
| 3 | See it | saída real de um comando, nunca descrição dela |
| 4 | Run it | clone, instalar, rodar, testar; comandos copiáveis |
| 5 | How it works | tabela arquivo → papel, trecho de código, Mermaid |
| 6 | The trap | `> [!WARNING]` com a armadilha conhecida |
| 7 | What this is not | tabela de limites; escopo honesto |

Seção não aplicável sai; ordem não muda.

### Regras

- **Um idioma por repo.** pt-BR se o leitor é brasileiro (teste, empresa BR); inglês nos demais.
- **Print no topo** quando há UI; salve em `docs/`, nunca link externo.
- **Mermaid** para fluxo, estados e sequência; prosa não repete o diagrama.
- **`<details>`** para rota, código de erro, log longo e suposição; o topo fica curto.
- **Tabela lado a lado** (`<table>`) para dois prints; `<sub>` na legenda.
- **Badge só do que o CI prova** (CI, versão, licença, contagem). Promessa verificável vira job, ver `projeto-publico`.
- **Nunca** path de máquina (`/Users/...`), chave, e-mail pessoal ou "TODO" no README.
- **Reescrever README existente:** não perca conteúdo; o que sai do topo vai para `<details>` ou tabela.

### Verificação antes de commitar

```bash
grep -nE "/Users/|/home/|TODO|sk-[A-Za-z0-9]" README.md   # deve imprimir nada
grep -c '```mermaid' README.md                             # pelo menos 1
```

Diagrama não renderizado localmente: diga que não conferiu no GitHub.
