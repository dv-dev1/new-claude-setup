export function calcularTotal(itens) {
  return itens.reduce((soma, item) => soma + item.quantidade * item.precoCentavos, 0);
}

export function calcularMedia(itens) {
  if (itens.length === 0) return 0;
  return Math.round(calcularTotal(itens) / itens.length);
}
