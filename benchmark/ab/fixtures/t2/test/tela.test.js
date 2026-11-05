import { test } from 'node:test';
import assert from 'node:assert/strict';
import { telaCatalogo } from '../src/tela.js';

const produtos = [
  { id: 1, nome: 'Pão de Queijo', precoCentavos: 650, disponivel: true },
  { id: 2, nome: 'Suco de Uva', precoCentavos: 900, disponivel: false },
  { id: 3, nome: 'Café Coado', precoCentavos: 500, disponivel: true },
];

test('lista só os disponíveis, com preço', () => {
  assert.equal(telaCatalogo(produtos), '- Pão de Queijo — R$ 6,50\n- Café Coado — R$ 5,00');
});
