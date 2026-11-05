import { readFileSync } from 'node:fs';
import * as calculo from './calculo.js';

const acoes = JSON.parse(readFileSync(new URL('../config/acoes.json', import.meta.url), 'utf8'));

export function executarRota(rota, itens) {
  const funcao = calculo[acoes[rota]];
  if (!funcao) throw new Error(`rota sem função: ${rota}`);
  return funcao(itens);
}
