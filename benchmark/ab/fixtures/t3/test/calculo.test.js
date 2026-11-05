import { test } from 'node:test';
import assert from 'node:assert/strict';
import { calcularTotal, calcularMedia } from '../src/calculo.js';
import { resumoVendas } from '../src/relatorio.js';

const itens = [
  { quantidade: 2, precoCentavos: 1500 },
  { quantidade: 1, precoCentavos: 999 },
];

test('soma os itens', () => {
  assert.equal(calcularTotal(itens), 3999);
});

test('ticket médio', () => {
  assert.equal(calcularMedia(itens), 2000);
});

test('resumo', () => {
  assert.deepEqual(resumoVendas(itens), { total: 3999, media: 2000, quantidade: 2 });
});
