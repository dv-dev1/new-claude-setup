import { calcularTotal, calcularMedia } from './calculo.js';

export function resumoVendas(itens) {
  return {
    total: calcularTotal(itens),
    media: calcularMedia(itens),
    quantidade: itens.length,
  };
}
