import { test } from 'node:test';
import assert from 'node:assert/strict';
import { textoConfirmacao } from '../src/confirmacao.js';
import { diasAte } from '../src/datas.js';

test('conta os dias até a consulta', () => {
  assert.equal(diasAte('2026-03-10', '2026-03-01'), 9);
  assert.equal(diasAte('2026-03-01', '2026-03-01'), 0);
});

test('monta o texto da confirmação', () => {
  const consulta = { medico: 'Dra. Ana', data: '2026-03-10', hora: '14:30' };
  assert.equal(
    textoConfirmacao(consulta, '2026-03-09'),
    'Consulta com Dra. Ana: terça, 10/03/2026 às 14:30 (amanhã).'
  );
});
