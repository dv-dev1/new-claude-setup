export function listarDisponiveis(produtos) {
  return produtos.filter((p) => p.disponivel);
}

export function formatarPreco(centavos) {
  const reais = Math.floor(centavos / 100);
  const resto = String(centavos % 100).padStart(2, '0');
  return `R$ ${reais},${resto}`;
}
