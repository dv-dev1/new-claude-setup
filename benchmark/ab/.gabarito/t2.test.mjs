import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const alvo = process.env.ALVO;
const { buscar } = await import(pathToFileURL(`${alvo}/src/catalogo.js`).href);
const { telaBusca } = await import(pathToFileURL(`${alvo}/src/tela.js`).href);

const P = () => [
  { id: 1, nome: 'Pão de Queijo', precoCentavos: 650, disponivel: true },
  { id: 2, nome: 'Pão Francês', precoCentavos: 120, disponivel: true },
  { id: 3, nome: 'Queijo Coalho', precoCentavos: 1200, disponivel: true },
  { id: 4, nome: 'Açaí na Tigela', precoCentavos: 1890, disponivel: true },
  { id: 5, nome: 'Suco de Açaí', precoCentavos: 1100, disponivel: true },
  { id: 6, nome: 'Suco de Uva', precoCentavos: 900, disponivel: false },
  { id: 7, nome: 'Éclair', precoCentavos: 950, disponivel: true },
  { id: 8, nome: 'bolo de cenoura', precoCentavos: 800, disponivel: true },
  { id: 9, nome: 'Cafe Coado', precoCentavos: 500, disponivel: true },
  { id: 10, nome: 'Suco de Laranja', precoCentavos: 850, disponivel: true },
];
const nomes = (r) => r.map((p) => (typeof p === 'string' ? p : p.nome));
const tela = (q) => String(telaBusca(P(), q)).replace(/\n+$/, '');
const TODOS = ['Açaí na Tigela', 'bolo de cenoura', 'Cafe Coado', 'Éclair', 'Pão de Queijo',
  'Pão Francês', 'Queijo Coalho', 'Suco de Açaí', 'Suco de Laranja'];

const casos = [
  ['pao', ['Pão de Queijo', 'Pão Francês']],
  ['PÃO   queijo ', ['Pão de Queijo']],
  ['queijo pao', ['Pão de Queijo']],
  ['ao', []],
  ['acai', ['Açaí na Tigela', 'Suco de Açaí']],
  ['suco', ['Suco de Açaí', 'Suco de Laranja']],
  ['uva', []],
  ['café', ['Cafe Coado']],
  ['ÉCLAIR', ['Éclair']],
  ['que', ['Queijo Coalho', 'Pão de Queijo']],
  ['de', ['bolo de cenoura', 'Pão de Queijo', 'Suco de Açaí', 'Suco de Laranja']],
  ['', TODOS],
  ['   ', TODOS],
];
for (const [q, esperado] of casos) {
  test(`buscar ${JSON.stringify(q)}`, () => assert.deepEqual(nomes(buscar(P(), q)), esperado));
}

test('telaBusca sem resultado', () => assert.equal(tela(' xyz '), 'Nenhum produto para "xyz"'));
test('telaBusca sem resultado mantém espaço do meio', () => assert.equal(tela('  xx   yy '), 'Nenhum produto para "xx   yy"'));
test('telaBusca 1 produto', () => assert.equal(tela('eclair'), '1 produto\n- Éclair — R$ 9,50'));
test('telaBusca n produtos', () => assert.equal(tela('suco'), '2 produtos\n- Suco de Açaí — R$ 11,00\n- Suco de Laranja — R$ 8,50'));
test('telaBusca prefixo parcial', () => assert.equal(tela('Pão  Fr'), '1 produto\n- Pão Francês — R$ 1,20'));
