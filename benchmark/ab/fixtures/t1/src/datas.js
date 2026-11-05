// O formulário manda a data como 'AAAA-MM-DD'.
const DIAS = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];

export function formatarDataBR(iso) {
  const d = new Date(iso);
  const dia = String(d.getDate()).padStart(2, '0');
  const mes = String(d.getMonth() + 1).padStart(2, '0');
  return `${dia}/${mes}/${d.getFullYear()}`;
}

export function diaDaSemana(iso) {
  return DIAS[new Date(iso).getDay()];
}

export function diasAte(isoAlvo, isoHoje) {
  return Math.round((new Date(isoAlvo) - new Date(isoHoje)) / 86_400_000);
}
