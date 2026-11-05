import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const alvo = process.env.ALVO;
const { buscar } = await import(pathToFileURL(`${alvo}/src/catalogo.js`).href);

const P = () => [
  { id: 1, nome: 'Pão de Queijo', precoCentavos: 650, disponivel: true },
  { id: 2, nome: 'Suco de Uva', precoCentavos: 900, disponivel: true },
  { id: 3, nome: 'Açaí na Tigela', precoCentavos: 1890, disponivel: true },
];
const nomes = (r) => r.map((p) => (typeof p === 'string' ? p : p.nome));

test('não reordena a lista de quem chamou', () => {
  const lista = P();
  buscar(lista, '');
  assert.deepEqual(nomes(lista), ['Pão de Queijo', 'Suco de Uva', 'Açaí na Tigela']);
});

test('tab e quebra de linha contam como espaço', () => {
  assert.deepEqual(nomes(buscar(P(), 'pao\tqueijo\n')), ['Pão de Queijo']);
});
