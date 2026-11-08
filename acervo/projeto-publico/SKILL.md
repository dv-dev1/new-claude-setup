---
name: projeto-publico
description: 'Estrutura repositórios públicos clonáveis. Use em tamanho: projeto quando outra pessoa for clonar o repositório, publicar no PyPI ou mencionar "projeto público".'
---

## Estrutura de projeto público (`tamanho: projeto`)

Vale **só** para repositório que outra pessoa vai clonar. Script solto e `tamanho: rápido` não levam nada disto: cerimônia que ninguém mantém estraga as regras que importam.

Obrigatório:

- `pyproject.toml` com `[build-system]`, `requires-python`, `license`, `dependencies` e extra `dev`. Sem ele o projeto não é instalável e o import depende do diretório em que você está.
- `LICENSE` — MIT, salvo motivo declarado.
- `README.md` que abre dizendo o que é em duas linhas e mostra a **saída real** de um comando, não a descrição dela; estrutura e esqueleto em `readme-padrao`.
- `.github/workflows/ci.yml` rodando o teste em pelo menos duas versões de Python.
- `[tool.ruff]` no `pyproject.toml`, e `ruff check` no CI.

Opcional, e só quando paga o próprio custo:

- layout `src/` — convenção, não ganho; adote se for publicar no PyPI
- `.pre-commit-config.yaml` — vale quando mais de uma pessoa commita
- `mypy` — vale em biblioteca com API pública

**Promessa do README vira job de CI.** Quando o `README` afirma algo verificável — "zero dependência", "roda sem chave de API", "500 linhas" — escreva o job que quebra quando deixar de ser verdade. Frase envelhece em silêncio; job vermelho, não.
