// Motor das cenas em motion (HTML/SVG animado quadro a quadro).
// Cada cena é um .html que inclui este arquivo e define `cena(t)`: recebe o tempo em segundos e deixa a tela
// exatamente como ela deve estar naquele instante (determinístico, sem setTimeout nem animação CSS solta).
// motion.py abre a cena no Chromium, chama quadro(t) para cada quadro e grava a imagem.

const MARCA = { ink: "#0B0B0C", lima: "#D4FF3A", papel: "#F2F2EF", cinza: "#8C8F94", cinzaEscuro: "#2A2B2E" };
const W = 1080, H = 1920;
const SEGURA = { topo: 250, base: 340, esq: 60, dir: 140 }; // zona segura do Reels
const EIXO_X = W / 2; // eixo de centralização = meio do quadro (a zona segura só limita a largura)

// ---------- tempo e movimento (uma curva para o vídeo inteiro) ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const entra = (x) => 1 - Math.pow(1 - clamp(x), 3);          // rápido e assenta suave
const sai = (x) => Math.pow(clamp(x), 3);
const vaiVem = (x) => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
// progresso de entrada (0→1) a partir de `ini`, durando `dur`
const p = (t, ini, dur = 0.35) => entra((t - ini) / dur);
// visível entre ini e fim, com entrada e saída
function vida(t, ini, fim, de = 0.3, ds = 0.25) {
  if (t < ini || t >= fim) return 0;
  return entra((t - ini) / de) * (1 - sai((t - (fim - ds)) / ds));
}

// ---------- DOM ----------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
function css(el, estilos) { if (typeof el === "string") el = $(el); if (el) Object.assign(el.style, estilos); return el; }
function mostra(el, op, dy = 0, escala = 1) {
  return css(el, { opacity: op, transform: `translate(-50%, -50%) translateY(${(1 - op) * dy}px) scale(${escala})` });
}
// conta de a até b no intervalo (número formatado em pt-BR)
function conta(a, b, t, ini, dur, casas = 0) {
  const v = lerp(a, b, entra((t - ini) / dur));
  return v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

// ---------- pronto para o motion.py ----------
window.quadro = (t) => { if (typeof cena === "function") cena(t); return true; };
window.__pronto = document.fonts.ready.then(() => true);
