import { formatarDataBR, diaDaSemana, diasAte } from './datas.js';

function quando(faltam) {
  if (faltam === 0) return 'hoje';
  if (faltam === 1) return 'amanhã';
  return `em ${faltam} dias`;
}

export function textoConfirmacao(consulta, hoje) {
  const { medico, data, hora } = consulta;
  return `Consulta com ${medico}: ${diaDaSemana(data)}, ${formatarDataBR(data)} às ${hora} (${quando(diasAte(data, hoje))}).`;
}
