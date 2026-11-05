import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const alvo = process.env.ALVO;
const calculo = await import(pathToFileURL(`${alvo}/src/calculo.js`).href);
const { resumoVendas } = await import(pathToFileURL(`${alvo}/src/relatorio.js`).href);
const { executarRota } = await import(pathToFileURL(`${alvo}/src/rotas.js`).href);

const itens = [
  { quantidade: 2, precoCentavos: 1500 },
  { quantidade: 1, precoCentavos: 999 },
];

test('somarItens soma', () => assert.equal(calculo.somarItens(itens), 3999));
test('média segue', () => assert.equal(calculo.calcularMedia(itens), 2000));
test('resumo segue', () => assert.deepEqual(resumoVendas(itens), { total: 3999, media: 2000, quantidade: 2 }));
test('rota total pelo config', () => assert.equal(executarRota('total', itens), 3999));
test('rota media pelo config', () => assert.equal(executarRota('media', itens), 2000));
