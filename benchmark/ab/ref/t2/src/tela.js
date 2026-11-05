import { listarDisponiveis, formatarPreco, buscar } from './catalogo.js';

export function linhaProduto(produto) {
  return `- ${produto.nome} — ${formatarPreco(produto.precoCentavos)}`;
}

export function telaCatalogo(produtos) {
  return listarDisponiveis(produtos).map(linhaProduto).join('\n');
}

export function telaBusca(produtos, consulta) {
  const achados = buscar(produtos, consulta);
  if (achados.length === 0) return `Nenhum produto para "${consulta.trim()}"`;
  const cabecalho = achados.length === 1 ? '1 produto' : `${achados.length} produtos`;
  return [cabecalho, ...achados.map(linhaProduto)].join('\n');
}
