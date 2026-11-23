// uso: node render.js <pasta-do-post>   (lê spec.json, grava 01.png..NN.png, contato.png e qa.txt)
const { chromium } = require('/opt/npm-tools/node_modules/playwright');
const fs = require('fs'), path = require('path');

// ---------- revisão do texto do spec (maiúsculas, espaços, pontuação) ----------
const TXT = ['title','body','eyebrow','sub','foot','note','cta','a','b','from','to','q','t','s','big','word','def','ex','answer','text','myth','truth','sinal','passo','quote'];
function clean(s){ return String(s).replace(/\*\*|\*|\|\|/g,'').replace(/\s*\n\s*/g,' '); }
function lintText(s, where, allowLower){
  const out=[]; const c=clean(s);
  if (/ {2,}/.test(c)) out.push(`${where}: espaço duplo`);
  if (/ [,.;:!?]/.test(c)) out.push(`${where}: espaço antes da pontuação`);
  const first = c.replace(/^[\s“"(«—–-]+/,'')[0];
  if (first && /[a-zà-ú]/.test(first) && !allowLower) out.push(`${where}: começa com minúscula ("${c.slice(0,30)}")`);
  const re=/[.!?]\s+[“"(]?([a-zà-ú])/g; let m; while((m=re.exec(c))) out.push(`${where}: minúscula depois de ponto ("…${c.slice(Math.max(0,m.index-12),m.index+8)}…")`);
  const caps=(c.replace(/“[^”]*”|"[^"]*"/g,'').match(/\b[A-ZÀ-Ú]{4,}\b/g)||[]).filter(w=>!(global.ALLOWCAPS||[]).includes(w)); if(caps.length) out.push(`${where}: palavra toda em maiúscula (${caps.join(', ')})`);
  return out;
}
function lintSpec(spec){
  const out=[];
  spec.slides.forEach((s,i)=>{
    let prevEnd = '';
    const visit=(obj,key,where)=>{
      if (typeof obj==='string'){ if(TXT.includes(key)){ const cont = prevEnd && !/[.!?…]$/.test(prevEnd.trim()); out.push(...lintText(obj,where, cont || key==='word' || s.lower===true)); prevEnd=clean(obj);} return; }
      if (Array.isArray(obj)) obj.forEach((v,k)=>visit(v,key,`${where}[${k+1}]`));
      else if (obj && typeof obj==='object') for (const k in obj) visit(obj[k],k,`${where}.${k}`);
    };
    for (const k of ['eyebrow','label','title','a','b','body','sub','foot','items','pairs','rows','points','cta','note','from','to','word','def','ex','text','myth','truth','sinal','passo','quote']) if (s[k]!==undefined && k!=='label') visit(s[k],k,`slide ${String(i+1).padStart(2,'0')} ${k}`);
  });
  return out;
}

(async () => {
  const dir = path.resolve(process.argv[2]);
  const brand = JSON.parse(fs.readFileSync(path.join(__dirname, 'brand.json'), 'utf8'));
  const spec = JSON.parse(fs.readFileSync(path.join(dir, 'spec.json'), 'utf8'));
  global.ALLOWCAPS = spec.allowCaps || [];
  const qa = lintSpec(spec);
  for (const ext of ['jpg','jpeg','png','webp']) { const af = path.join(__dirname, 'avatar.' + ext); if (fs.existsSync(af)) { brand.avatar = 'data:image/' + (ext==='jpg'?'jpeg':ext) + ';base64,' + fs.readFileSync(af).toString('base64'); break; } }
  // fotos: campos "photo" apontam para arquivos na pasta do post (ex.: "fotos/capa.jpg"); sem arquivo, o slide mostra o espaço reservado
  const missing = [];
  for (const [i, s] of spec.slides.entries()) for (const k of ['photo','imgSrc']) { if (typeof s[k] === 'string' && !s[k].startsWith('data:')) { const f = path.join(dir, s[k]); if (fs.existsSync(f)) { const e = path.extname(f).slice(1).toLowerCase(); s[k] = 'data:image/' + (e==='jpg'?'jpeg':e) + ';base64,' + fs.readFileSync(f).toString('base64'); } else missing.push(`slide ${String(i+1).padStart(2,'0')}: ${s[k]} (${s.phLabel||'foto'})`); } }
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome' });
  const p = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + path.join(__dirname, 'template.html'));
  const n = await p.evaluate(([b_, s_]) => window.boot(b_, s_), [brand, spec]);
  await p.evaluate(() => document.fonts.ready);
  const outs = [];
  for (let i = 0; i < n; i++) {
    await p.evaluate(i => window.renderSlide(i), i);
    await p.waitForTimeout(120);
    const f = path.join(dir, String(i + 1).padStart(2, '0') + '.png');
    await p.locator('#slide').screenshot({ path: f });
    outs.push(f);
    const issues = await p.evaluate(() => window.qa());
    issues.forEach(x => qa.push(`slide ${String(i + 1).padStart(2, '0')}: ${x}`));
  }
  if (errs.length) console.error('ERROS:', errs);
  // folha de contato
  const imgs = outs.map(f => 'data:image/png;base64,' + fs.readFileSync(f).toString('base64'));
  const cols = Math.min(5, n), w = 324, h = 405, rows = Math.ceil(n / cols);
  await p.setViewportSize({ width: cols * (w + 12) + 12, height: rows * (h + 12) + 12 });
  await p.setContent(`<body style="margin:0;background:#2a2a2a;display:grid;grid-template-columns:repeat(${cols},${w}px);gap:12px;padding:12px">${imgs.map(s => `<img src="${s}" style="width:${w}px;height:${h}px">`).join('')}</body>`);
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(dir, 'contato.png'), fullPage: true });
  await b.close();
  const report = [`Revisão automática · ${spec.series || spec.id}`, '', qa.length ? 'Pontos a corrigir:' : 'Texto e margens: nada a corrigir.', ...qa.map(x => '- ' + x), '', missing.length ? 'Fotos que faltam:' : 'Fotos: nenhuma faltando.', ...missing.map(x => '- ' + x)].join('\n');
  fs.writeFileSync(path.join(dir, 'qa.txt'), report + '\n');
  console.log('ok', n, 'slides ·', qa.length, 'pontos ·', missing.length, 'fotos faltando');
  if (qa.length) console.log(qa.map(x => '  ' + x).join('\n'));
})();
