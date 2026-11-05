import { listarDisponiveis, formatarPreco } from './catalogo.js';

export function linhaProduto(produto) {
  return `- ${produto.nome} — ${formatarPreco(produto.precoCentavos)}`;
}

export function telaCatalogo(produtos) {
  return listarDisponiveis(produtos).map(linhaProduto).join('\n');
}
