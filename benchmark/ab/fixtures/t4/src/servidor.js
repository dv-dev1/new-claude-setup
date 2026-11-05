import { createServer } from 'node:http';
import { lerConsultas } from './agenda.js';
import { textoConfirmacao } from './confirmacao.js';

const PORTA = Number(process.env.PORT ?? 3000);

function hojeEmSaoPaulo() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' }).format(new Date());
}

function responder(res, status, corpo) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(corpo));
}

const servidor = createServer(async (req, res) => {
  const consultas = await lerConsultas();
  if (req.url === '/consultas') return responder(res, 200, consultas);
  const rota = req.url.match(/^\/consultas\/([^/]+)\/confirmacao$/);
  const consulta = rota && consultas.find((c) => c.id === rota[1]);
  if (!consulta) return responder(res, 404, { erro: 'não encontrado' });
  return responder(res, 200, { texto: textoConfirmacao(consulta, hojeEmSaoPaulo()) });
});

servidor.listen(PORTA, () => console.log(`agenda-consultas na porta ${PORTA}`));
