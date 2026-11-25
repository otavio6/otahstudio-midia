// uso: node engine/story/render_story.js <pasta>  (lê story.json, grava 01.png..NN.png 1080x1920 e contato.png)
// Zona segura: 250 px livres em cima e 340 px embaixo (interface do Instagram).
const { chromium } = require('/opt/npm-tools/node_modules/playwright');
const fs = require('fs'), path = require('path');
const dir = path.resolve(process.argv[2]);
const spec = JSON.parse(fs.readFileSync(path.join(dir, 'story.json'), 'utf8'));
const root = path.join(__dirname, '..');
const b64 = f => 'data:image/' + (f.endsWith('.png') ? 'png' : 'jpeg') + ';base64,' + fs.readFileSync(f).toString('base64');
const avatar = b64(path.join(root, 'avatar.jpg'));
const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
const rich = s => esc(s).replace(/\*([^*]+)\*/g,'<span class="acc">$1</span>').replace(/\|\|(.*)$/s,'<span class="mut">$1</span>').replace(/\n/g,'<br>');
function page(t){
  const dark = t.theme !== 'light';
  const C = dark ? {bg:'#0B0B0C',ink:'#F4F4F1',mut:'#8C8F94',acc:'#D4FF3A',line:'rgba(255,255,255,.12)'} : {bg:'#F2F2EE',ink:'#111214',mut:'#5F6268',acc:'#1F4FFF',line:'rgba(17,18,20,.12)'};
  const img = t.image ? `<div style="position:absolute;left:${t.imgX??240}px;top:${t.imgTop??1000}px;width:${t.imgW??600}px;height:${(t.imgW??600)*1.25}px;border-radius:28px;background:url('${b64(path.join(dir,t.image))}') center/cover;box-shadow:0 40px 80px -30px rgba(0,0,0,.45);transform:rotate(${t.rot??-3}deg)"></div>` : '';
  const big = t.big ? `<div style="position:absolute;left:76px;top:${t.bigTop??1060}px;font:400 ${t.bigSize??420}px/.85 'Inter Display';letter-spacing:-.06em;color:${C.acc}">${esc(t.big)}</div>` : '';
  return `<html><head><meta charset="utf-8"><style>
  body{margin:0}.s{width:1080px;height:1920px;position:relative;overflow:hidden;background:${C.bg};color:${C.ink};font-family:Inter;-webkit-font-smoothing:antialiased}
  .mut{color:${C.mut}}.acc{color:${C.acc}}
  .hd{position:absolute;left:80px;top:300px;display:flex;align-items:center;gap:18px}
  .hd .av{width:72px;height:72px;border-radius:50%;background:url('${avatar}') center/cover;border:3px solid ${dark?'#F4F4F1':'#fff'}}
  .hd b{font:600 30px/1.1 Inter;display:flex;align-items:center;gap:8px}.hd small{font:400 24px/1.3 Inter;color:${C.mut}}
  .lbl{font:400 30px/1 'DejaVu Sans Mono';letter-spacing:.12em;text-transform:uppercase;color:${C.mut}}
  .t{font:400 ${t.size??84}px/1.04 'Inter Display';letter-spacing:-.035em}
  .bd{font:400 36px/1.4 Inter;color:${C.mut}}
  .src{position:absolute;left:80px;right:80px;bottom:370px;font:400 22px/1.3 'DejaVu Sans Mono';color:${C.mut};letter-spacing:.02em}
  .reply{position:absolute;left:80px;bottom:380px;font:500 34px/1 Inter;color:${C.ink};display:flex;align-items:center;gap:16px}
  .grain{position:absolute;inset:0;opacity:.09;mix-blend-mode:overlay;pointer-events:none}
  </style></head><body><div class="s">
  <div class="hd"><div class="av"></div><div><b>Otávio Henrique <svg width="26" height="26" viewBox="0 0 24 24"><path d="M12 1l2.6 2.2 3.4-.4.9 3.3 3 1.7-1.3 3.2 1.3 3.2-3 1.7-.9 3.3-3.4-.4L12 23l-2.6-2.2-3.4.4-.9-3.3-3-1.7L3.4 13 2.1 9.8l3-1.7.9-3.3 3.4.4z" fill="#3897F0"/><path d="M7.5 12.2l3 3 6-6.2" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></b><small>@otaviohenriqve</small></div></div>
  <div style="position:absolute;left:80px;right:80px;top:${t.top??520}px">${t.label?`<div class="lbl" style="margin-bottom:40px">${esc(t.label)}</div>`:''}${t.eyebrow?`<div class="bd" style="margin-bottom:28px;color:${C.ink}">${rich(t.eyebrow)}</div>`:''}${t.title?`<div class="t">${rich(t.title)}</div>`:''}${t.body?`<div class="bd" style="margin-top:40px">${rich(t.body)}</div>`:''}</div>
  ${big}${img}
  ${(t.pics||[]).map(q=>`<div style="position:absolute;left:${q.x??80}px;top:${q.y}px;width:${q.w}px;height:${q.h}px;background:url('${b64(path.join(dir,q.src))}') center/contain no-repeat;${q.r?`border-radius:${q.r}px;`:''}${q.shadow?'box-shadow:0 40px 80px -30px rgba(0,0,0,.5);':''}${q.border?'outline:2px solid rgba(255,255,255,.28);outline-offset:6px;':''}"></div>${q.cap?`<div class="lbl" style="position:absolute;left:${(q.x??80)+q.w+32}px;top:${q.capY??(q.y+q.h-30)}px">${esc(q.cap)}</div>`:''}`).join('')}
  ${t.cta?`<div style="position:absolute;left:80px;right:80px;top:${t.ctaTop??1200}px;font:500 ${t.ctaSize??52}px/1.15 Inter;color:${C.ink}">${rich(t.cta)}</div>`:''}
  ${t.foot?`<div style="position:absolute;left:80px;right:80px;top:1530px;display:flex;justify-content:space-between" class="lbl"><span>${esc(t.foot[0])}</span><span>${esc(t.foot[1])}</span></div>`:''}
  ${t.after?`<div style="position:absolute;left:80px;right:80px;top:${t.after.top}px"><div class="t" style="font-size:${t.after.size??72}px">${rich(t.after.title)}</div></div>`:''}
  ${t.outline?`<div style="position:absolute;${t.outlineRight?'right:'+(t.outlineR??40)+'px':'left:70px'};top:${t.outlineTop??1000}px;font:400 ${t.outlineSize??400}px/.8 'Inter Display';letter-spacing:-.05em;color:transparent;-webkit-text-stroke:${t.outlineW??3}px ${dark?'rgba(255,255,255,'+(t.outlineA??.16)+')':'rgba(17,18,20,'+(t.outlineA??.16)+')'}">${esc(t.outline)}</div>`:''}
  ${t.source?`<div class="src" style="${t.srcTop?`top:${t.srcTop}px;bottom:auto`:''}">${esc(t.source)}</div>`:''}
  ${t.reply?`<div class="reply">${esc(t.reply)} <span style="font-size:44px">↓</span></div>`:''}
  <svg class="grain" width="1080" height="1920"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>
  </div></body></html>`;
}
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome' });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  const outs = [];
  for (const [i, t] of spec.telas.entries()) {
    await p.setContent(page(t)); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(150);
    const f = path.join(dir, String(i + 1).padStart(2, '0') + '.png'); await p.screenshot({ path: f }); outs.push(f);
  }
  const n = outs.length, w = 300, h = 533;
  await p.setViewportSize({ width: n * (w + 12) + 12, height: h + 24 });
  await p.setContent(`<body style="margin:0;background:#2a2a2a;display:flex;gap:12px;padding:12px">${outs.map(f => `<div style="position:relative"><img src="${b64(f)}" style="width:${w}px;height:${h}px;display:block"><div style="position:absolute;left:0;right:0;top:0;height:${250*w/1080}px;background:rgba(229,72,77,.18)"></div><div style="position:absolute;left:0;right:0;bottom:0;height:${340*w/1080}px;background:rgba(229,72,77,.18)"></div></div>`).join('')}</body>`);
  await p.screenshot({ path: path.join(dir, 'contato.png') });
  await b.close(); console.log('ok', n, 'telas (faixas vermelhas no contato = zona coberta pela interface)');
})();
