import { somarItens, calcularMedia } from './calculo.js';

export function resumoVendas(itens) {
  return {
    total: somarItens(itens),
    media: calcularMedia(itens),
    quantidade: itens.length,
  };
}
