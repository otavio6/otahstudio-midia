"""Renderiza uma cena em motion (HTML/SVG animado) quadro a quadro, no Chromium do próprio ambiente.
A cena define cena(t) e deixa a tela exata para cada instante (veja motion/base.js).

Uso:
  python motion.py CENA.html SAIDA_DIR --dur 4.5 [--fps 24] [--transparente]   → PNGs 0000.png, 0001.png…
  python motion.py CENA.html QUADRO.png --em 1.2                                 → um quadro só (storyboard)
"""
import argparse, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import FPS, W, H


def abrir(pw, cena, transparente):
    nav = pw.chromium.launch()
    pag = nav.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    pag.goto(Path(cena).resolve().as_uri())
    pag.evaluate("window.__pronto")
    if transparente:
        pag.evaluate("document.documentElement.style.background='transparent';document.body.style.background='transparent'")
    return nav, pag


def quadros(cena, saida_dir, dur, fps=FPS, transparente=False, t0=0.0):
    os.makedirs(saida_dir, exist_ok=True)
    n = max(1, round(dur * fps))
    with sync_playwright() as pw:
        nav, pag = abrir(pw, cena, transparente)
        for i in range(n):
            pag.evaluate(f"quadro({t0 + i / fps:.5f})")
            pag.screenshot(path=os.path.join(saida_dir, f"{i:04d}.png"), omit_background=transparente, type="png")
        nav.close()
    return n


def um_quadro(cena, png, t, transparente=False):
    with sync_playwright() as pw:
        nav, pag = abrir(pw, cena, transparente)
        pag.evaluate(f"quadro({t:.5f})")
        pag.screenshot(path=png, omit_background=transparente, type="png")
        nav.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cena"); ap.add_argument("saida")
    ap.add_argument("--dur", type=float); ap.add_argument("--em", type=float)
    ap.add_argument("--fps", type=int, default=FPS); ap.add_argument("--transparente", action="store_true")
    a = ap.parse_args()
    if a.em is not None:
        um_quadro(a.cena, a.saida, a.em, a.transparente); print("ok", a.saida)
    else:
        print("ok", quadros(a.cena, a.saida, a.dur, a.fps, a.transparente), "quadros")
