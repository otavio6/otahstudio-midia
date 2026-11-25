// Carrossel com motion: anima o MESMO layout do engine/render.js e grava um MP4 por slide.
// uso: node engine/motion_carrossel.js <pasta-do-post> [--dur 5] [--estaticos 1,7]
//  - textos entram em sequência (sobe 28 px + aparece), em até ~0,6 s
//  - número gigante de passo (01, 02...) sobe por trás
//  - imagens (gfx/*.png) aparecem por partes: cada balão de conversa / cada card entra na sua vez
//  - tudo termina em ~2 s e o slide fica parado até o fim, para a pessoa ler
//  - slide 1: o título já aparece no quadro 0 (é a miniatura do carrossel); só a imagem anima
// saída: <pasta>/motion/NN.mp4 (1080x1350, H.264), <pasta>/motion/previa.mp4 (todos em sequência)
const { chromium } = require('/opt/npm-tools/node_modules/playwright');
const fs = require('fs'), path = require('path'), { execSync } = require('child_process');

const args = process.argv.slice(2);
const dir = path.resolve(args[0]);
const opt = (k, d) => { const i = args.indexOf(k); return i > -1 ? args[i + 1] : d; };
const DUR = parseFloat(opt('--dur', '5'));
const ESTATICOS = (opt('--estaticos', '') || '').split(',').filter(Boolean).map(Number);
const FPS = 30;

// faixas de conteúdo de cada imagem (onde está cada balão/card), medidas pelos pixels
function bandas(file) {
  const py = `
import sys,json
from PIL import Image
import numpy as np
im=Image.open(sys.argv[1]).convert('RGBA'); a=np.asarray(im).astype(int)
if (a[...,3]<250).any(): m=a[...,3]>8
else:
    bg=a[2,2,:3]; m=np.abs(a[...,:3]-bg).sum(2)>30
def b(v,g=6):
    o=[];s=None
    for i,x in enumerate(v):
        if x and s is None: s=i
        if (not x) and s is not None: o.append([s,i]); s=None
    if s is not None: o.append([s,len(v)])
    return [x for x in o if x[1]-x[0]>g]
r=b(m.any(1)); c=b(m.any(0))
ax='x' if len(c)>len(r) else 'y'
opaque=not (a[...,3]<250).any()
print(json.dumps({'w':im.width,'h':im.height,'axis':ax,'bands':c if ax=='x' else r,'bg':[int(x) for x in a[2,2,:3]] if opaque else None}))`;
  return JSON.parse(execSync(`python3 -c "${py.replace(/"/g, '\\"')}" "${file}"`).toString());
}

(async () => {
  const brand = JSON.parse(fs.readFileSync(path.join(__dirname, 'brand.json'), 'utf8'));
  const spec = JSON.parse(fs.readFileSync(path.join(dir, 'spec.json'), 'utf8'));
  for (const ext of ['jpg', 'jpeg', 'png', 'webp']) { const af = path.join(__dirname, 'avatar.' + ext); if (fs.existsSync(af)) { brand.avatar = 'data:image/' + (ext === 'jpg' ? 'jpeg' : ext) + ';base64,' + fs.readFileSync(af).toString('base64'); break; } }
  const info = [];
  for (const s of spec.slides) {
    const inf = {};
    for (const k of ['photo', 'imgSrc']) if (typeof s[k] === 'string' && !s[k].startsWith('data:')) {
      const f = path.join(dir, s[k]);
      if (fs.existsSync(f)) { inf[k] = bandas(f); const e = path.extname(f).slice(1).toLowerCase(); s[k] = 'data:image/' + (e === 'jpg' ? 'jpeg' : e) + ';base64,' + fs.readFileSync(f).toString('base64'); }
    }
    info.push(inf);
  }
  const out = path.join(dir, 'motion'); fs.rmSync(out, { recursive: true, force: true }); fs.mkdirSync(out);
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome' });
  const p = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  await p.goto('file://' + path.join(__dirname, 'template.html'));
  const n = await p.evaluate(([b_, s_]) => window.boot(b_, s_), [brand, spec]);
  await p.evaluate(() => document.fonts.ready);
  const mp4s = [];
  for (let i = 0; i < n; i++) {
    await p.evaluate(i => { window.__mine = []; window.renderSlide(i); }, i);
    await p.evaluate(() => Promise.all([...document.images].map(im => im.decode().catch(() => {}))));
    await p.locator('#slide').screenshot(); await p.waitForTimeout(300);   // força decodificar o avatar
    const nome = String(i + 1).padStart(2, '0');
    const fdir = path.join(out, 'q' + nome); fs.mkdirSync(fdir);
    let T = 0;
    if (!ESTATICOS.includes(i + 1)) {
      T = await p.evaluate(([inf, first]) => {
        const S = document.getElementById('slide');
        document.getAnimations().forEach(a => { try { a.finish(); } catch (e) { a.cancel(); } });
        const mine = [];
        const ease = 'cubic-bezier(.2,.7,.2,1)';
        const inChrome = el => el.closest('.hdr,.ftr,.grain');
        let t = 0, end = 0;
        const anim = (el, kf, delay, dur) => { mine.push(el.animate(kf, { duration: dur, delay, fill: 'both', easing: ease })); end = Math.max(end, delay + dur); };
        // número gigante do passo
        for (const el of S.querySelectorAll(':scope > div')) {
          if (parseFloat(getComputedStyle(el).fontSize) >= 200 && el.textContent.trim().length <= 3) { el.style.clipPath = 'inset(0 0 0 0)'; anim(el, [{ transform: 'translateY(90px)', opacity: 0 }, { transform: 'none', opacity: 1 }], 0, 650); t = 120; }
        }
        // textos, na ordem em que aparecem
        const txt = [...S.querySelectorAll('.eb,.h1,.h2,.h3,.bd,.label,.cta,.swipe,.note')].filter(el => !inChrome(el) && !el.parentElement.closest('.eb,.h1,.h2,.h3,.bd,.label,.cta'));
        txt.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
        if (!first) for (const el of txt) { anim(el, [{ transform: 'translateY(28px)', opacity: 0 }, { transform: 'none', opacity: 1 }], t, 520); t += 110; }
        // imagens por partes (cada balão / card na sua vez)
        let tImg = first ? 250 : Math.max(450, t);
        const boxes = [...S.querySelectorAll('.phb,.ph')].filter(el => !inChrome(el) && getComputedStyle(el).backgroundImage.startsWith('url'));
        for (const box of boxes) {
          const src = getComputedStyle(box).backgroundImage;
          const key = Object.keys(inf).find(k => src.includes(inf[k].__src));
          const bi = key ? inf[key] : null;
          if (!bi) { anim(box, [{ opacity: 0, transform: 'translateY(20px)' }, { opacity: 1, transform: 'none' }], tImg, 500); tImg += 400; continue; }
          const r = box.getBoundingClientRect(), sx = r.width / bi.w, sy = r.height / bi.h;
          let last = box;
          for (const [a0, a1] of bi.bands) {
            const c = box.cloneNode(true);
            const ins = bi.axis === 'y' ? `inset(${Math.max(0, a0 * sy - 2)}px 0 ${Math.max(0, r.height - a1 * sy - 2)}px 0)` : `inset(0 ${Math.max(0, r.width - a1 * sx - 2)}px 0 ${Math.max(0, a0 * sx - 2)}px)`;
            c.style.clipPath = ins;
            last.after(c); last = c;
            const from = bi.axis === 'y' ? 'translateY(18px) scale(.985)' : 'translateY(14px)';
            anim(c, [{ opacity: 0, transform: from }, { opacity: 1, transform: 'none' }], tImg, 420);
            tImg += bi.axis === 'y' ? 520 : 260;
          }
          if (bi.bg) { box.style.backgroundImage = 'none'; box.style.backgroundColor = `rgb(${bi.bg.join(',')})`; }
          else box.style.visibility = 'hidden';
        }
        mine.forEach(a => a.pause()); window.__mine = mine;
        return end + 120;
      }, [Object.fromEntries(Object.entries(info[i]).map(([k, v]) => [k, { ...v, __src: spec.slides[i][k].slice(22, 80) }])), i === 0]);
    }
    const frames = Math.max(1, Math.ceil(T / 1000 * FPS));
    for (let f = 0; f < frames; f++) {
      await p.evaluate(ms => (window.__mine || []).forEach(a => { a.currentTime = ms; }), f * 1000 / FPS);
      await p.locator('#slide').screenshot({ path: path.join(fdir, String(f).padStart(4, '0') + '.png') });
    }
    const hold = Math.max(0.5, DUR - frames / FPS);
    const mp4 = path.join(out, nome + '.mp4');
    execSync(`ffmpeg -y -loglevel error -framerate ${FPS} -i "${fdir}/%04d.png" -vf "tpad=stop_mode=clone:stop_duration=${hold.toFixed(2)},format=yuv420p" -c:v libx264 -preset veryfast -crf 16 -r ${FPS} -movflags +faststart "${mp4}"`);
    fs.rmSync(fdir, { recursive: true, force: true });
    mp4s.push(mp4);
    console.log(nome, ESTATICOS.includes(i + 1) ? 'parado' : `anima ${(T / 1000).toFixed(2)} s`, '→', path.basename(mp4));
  }
  await b.close();
  fs.writeFileSync(path.join(out, 'lista.txt'), mp4s.map(f => `file '${f}'`).join('\n'));
  execSync(`ffmpeg -y -loglevel error -f concat -safe 0 -i "${out}/lista.txt" -c copy "${out}/previa.mp4"`);
  fs.rmSync(path.join(out, 'lista.txt'));
  console.log('ok', n, 'slides · previa.mp4');
})();
