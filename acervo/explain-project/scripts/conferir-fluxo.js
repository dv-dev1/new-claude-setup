// Uso: node conferir-fluxo.js <pagina.html>
const fs = require("fs");

const html = fs.readFileSync(process.argv[2], "utf8");
const inicio = html.indexOf("var FLUXO = ");
if (inicio < 0) { console.log("sem var FLUXO"); process.exit(1); }
const FLUXO = eval("(" + html.slice(inicio + 12, html.indexOf("\n};", inicio) + 2) + ")");
const FINS = ["end", "human"];
const erros = [];

for (const [nome, fx] of Object.entries(FLUXO)) {
  const nos = fx.nos, usados = new Set(), arestas = new Set();
  const liga = (a, b) => arestas.add(a + ">" + b);
  // `de` aceita um id ou uma lista: a faixa continua de cada um deles.
  const origens = (lane) => [].concat(lane.de || []);
  const continuam = new Set(fx.lanes.flatMap(origens));
  const existe = (id, onde) => { usados.add(id); if (!nos[id]) erros.push(`${nome}: ${onde} usa ${id}, que não existe`); return !!nos[id]; };
  for (const lane of fx.lanes) {
    for (const de of origens(lane)) if (existe(de, `faixa ${lane.titulo}`)) liga(de, lane.passos[0].id);
    lane.passos.forEach((p, i) => {
      if (!existe(p.id, "passo")) return;
      const n = nos[p.id], prox = lane.passos[i + 1], lados = p.lados || [];
      if (n.k === "q" && lados.length + (p.desce ? 1 : 0) < 2) erros.push(`${nome}: pergunta ${p.id} com menos de dois ramos`);
      if (n.k !== "q" && lados.length) erros.push(`${nome}: ${p.id} tem desvio sem ser pergunta`);
      if (p.desce && !prox) erros.push(`${nome}: ${p.id} desce, mas é o último da faixa`);
      if (n.vai && existe(n.vai, p.id)) liga(p.id, n.vai);
      if (prox && !FINS.includes(n.k) && (n.k !== "q" || p.desce)) liga(p.id, prox.id);
      if (!prox && !FINS.includes(n.k) && !n.vai && !lados.length && !continuam.has(p.id)) erros.push(`${nome}: ${p.id} não tem saída`);
      for (const [, alvo] of lados) {
        if (!existe(alvo, p.id)) continue;
        liga(p.id, alvo);
        const a = nos[alvo];
        if (a.vai) { if (existe(a.vai, alvo)) liga(alvo, a.vai); }
        else if (!FINS.includes(a.k)) {
          if (prox && p.desce) liga(alvo, prox.id); else erros.push(`${nome}: desvio ${alvo} não tem para onde voltar`);
        }
      }
    });
  }
  for (const [id, n] of Object.entries(nos)) {
    if (!usados.has(id)) erros.push(`${nome}: ${id} solto`);
    for (const campo of ["k", "t", "c", "f"]) if (!n[campo]) erros.push(`${nome}: ${id} sem ${campo}`);
    if (n.porque && !n.fonte) erros.push(`${nome}: ${id} tem porquê sem fonte (use "inferido")`);
  }
  // O caso só anda por aresta desenhada: um salto mostraria um caminho que o código não faz.
  const passos = (fx.caso || { passos: [] }).passos.map((p) => p[0]);
  passos.forEach((id, i) => {
    if (!nos[id]) erros.push(`${nome}: passo do caso ${id} sem nó`);
    else if (i && !arestas.has(passos[i - 1] + ">" + id)) erros.push(`${nome}: caso pula de ${passos[i - 1]} para ${id} sem aresta`);
  });
}

const n = Object.keys(FLUXO).length;
console.log(erros.length ? erros.join("\n") : `OK: ${n} fluxo${n > 1 ? "s" : ""}`);
process.exit(erros.length ? 1 : 0);
