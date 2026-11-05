import { readFile } from 'node:fs/promises';

const ARQUIVO = new URL('../data/consultas.json', import.meta.url);

export async function lerConsultas(arquivo = ARQUIVO) {
  return JSON.parse(await readFile(arquivo, 'utf8'));
}
