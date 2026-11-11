# Benchmark do setup

Mede setups do Claude Code nas mesmas tarefas, no mesmo esforço: acerto por teste escondido, custo, tempo, ciclo de engenharia e uma nota de arquitetura dada por juiz cego.

| Pasta | O quê |
|---|---|
| `ab/` | bateria sintética: T1 bug de fuso, T2 feature com regras, T3 rename e commit em repo do trabalho, T4 feature com decisão de arquitetura (lembrete por WhatsApp) |
| `real/` | 6 bugs reais dos projetos (`pinch`, `brim`, `lancer`, `quehorasvoto`, `etros-n8n`): clone no pai do commit de correção, sem remote e sem o commit no histórico; nota pelo teste do próprio commit |
| `antigo/` | `montar.sh` remonta o setup antigo isolado (condição V) |

## Condições

| Letra | Setup |
|---|---|
| `H` | atual (`~/.claude`), `--effort high`, bypass |
| `E` | atual com o esforço do `modelSettings` (xhigh) |
| `N` | nativo (`--safe-mode`), `--effort high`, bypass |
| `B` | nativo em `--permission-mode auto` (rodada de 03/11) |
| `V` | antigo, `--effort high`, bypass (rode `antigo/montar.sh` antes) |

## Rodar

```bash
bash ab/prep.sh && bash ab/validar.sh                 # fixtures: gabarito reprova o original e aprova a referência
MAX=2 bash ab/run-all.sh lote t1-H-1 t1-N-1 t4-H-1 t4-N-1   # id = <tarefa>-<condição>-<repetição>
python3 -I ab/grade.py                                 # tabela por execução e resumo por condição
python3 -I ab/juiz-pacote.py 7 ab/juiz/j1.md t4-H-1 t4-N-1   # pacote cego do T4 para o juiz (sementes 7 e 13)

bash real/validar.sh <repo> <commit>                  # candidato: teste do commit reprova no pai e aprova na correção
MAX=2 bash real/run-all.sh real p1-H-1 p1-N-1
python3 -I real/grade.py
```

- Cada sessão roda fora do repo, em `$BENCH_W` (padrão `$TMPDIR/trabalho`), para não achar o gabarito.
- `MAX` sessões em paralelo; a próxima só entra com `PISO_MB` livres (padrão 1536). Com 8 GB, use 2.
- Transcripts das sessões caem em `~/.claude/projects`; mova-os depois para não poluir o histórico.
- O juiz do T4 recebe o pacote com `ponytail:` trocado por `shortcut:` (marca o setup atual) e o prompt de 8 critérios (0 a 2 cada) que está em `RESULTADOS.md`.
- Notas de juiz variam entre rodadas: compare condições dentro da mesma rodada.

Os resultados de 04/11/2026 estão em [RESULTADOS.md](RESULTADOS.md).

Cobertura da compactação (só lê transcripts, sem custo): `python3 benchmark/compactacao/cobertura.py --desde AAAA-MM-DDTHH:MM` (UTC, como o timestamp do transcript). Base em `RESULTADOS.md` (11/11/2026).
