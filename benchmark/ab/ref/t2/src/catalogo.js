export function listarDisponiveis(produtos) {
  return produtos.filter((p) => p.disponivel);
}

export function formatarPreco(centavos) {
  const reais = Math.floor(centavos / 100);
  const resto = String(centavos % 100).padStart(2, '0');
  return `R$ ${reais},${resto}`;
}

const normalizar = (texto) => texto.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
const palavras = (texto) => normalizar(texto).split(/\s+/).filter(Boolean);

function porNome(a, b) {
  const x = normalizar(a.nome);
  const y = normalizar(b.nome);
  return x < y ? -1 : x > y ? 1 : 0;
}

export function buscar(produtos, consulta) {
  const termos = palavras(consulta);
  const achados = listarDisponiveis(produtos)
    .filter((p) => termos.every((t) => palavras(p.nome).some((w) => w.startsWith(t))))
    .sort(porNome);
  if (termos.length === 0) return achados;
  const comeca = (p) => normalizar(p.nome).startsWith(termos[0]);
  return [...achados.filter(comeca), ...achados.filter((p) => !comeca(p))];
}
