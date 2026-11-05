import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const alvo = process.env.ALVO;
const datas = await import(pathToFileURL(`${alvo}/src/datas.js`).href);
const conf = await import(pathToFileURL(`${alvo}/src/confirmacao.js`).href);

const casos = [
  ['2026-03-01', '01/03/2026', 'domingo'],
  ['2026-01-01', '01/01/2026', 'quinta'],
  ['2024-02-29', '29/02/2024', 'quinta'],
  ['2026-11-02', '02/11/2026', 'segunda'],
  ['2026-12-31', '31/12/2026', 'quinta'],
];

for (const [iso, br, dia] of casos) {
  test(`formatarDataBR ${iso}`, () => assert.equal(datas.formatarDataBR(iso), br));
  test(`diaDaSemana ${iso}`, () => assert.equal(datas.diaDaSemana(iso), dia));
}

test('diasAte', () => {
  assert.equal(datas.diasAte('2026-03-01', '2026-02-28'), 1);
  assert.equal(datas.diasAte('2026-11-02', '2026-11-02'), 0);
  assert.equal(datas.diasAte('2026-03-09', '2026-03-08'), 1);
  assert.equal(datas.diasAte('2026-11-02', '2026-10-31'), 2);
});

test('textoConfirmacao do relato', () => {
  assert.equal(
    conf.textoConfirmacao({ medico: 'Dra. Ana', data: '2026-03-01', hora: '09:00' }, '2026-02-27'),
    'Consulta com Dra. Ana: domingo, 01/03/2026 às 09:00 (em 2 dias).'
  );
  assert.equal(
    conf.textoConfirmacao({ medico: 'Dr. Caio', data: '2026-11-03', hora: '08:15' }, '2026-11-02'),
    'Consulta com Dr. Caio: terça, 03/11/2026 às 08:15 (amanhã).'
  );
});
