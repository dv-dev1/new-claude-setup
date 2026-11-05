const DIAS = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];

function dataLocal(iso) {
  const [ano, mes, dia] = iso.split('-').map(Number);
  return new Date(ano, mes - 1, dia);
}

export function formatarDataBR(iso) {
  const [ano, mes, dia] = iso.split('-');
  return `${dia}/${mes}/${ano}`;
}

export function diaDaSemana(iso) {
  return DIAS[dataLocal(iso).getDay()];
}

export function diasAte(isoAlvo, isoHoje) {
  return Math.round((dataLocal(isoAlvo) - dataLocal(isoHoje)) / 86_400_000);
}
