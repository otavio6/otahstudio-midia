"""Prévia local do timeline.json, com a mesma lógica da composição Remotion (camadas, curva, posições, cores).
Serve para revisar aqui antes de mandar para o estúdio no VPS, e como plano B se o VPS estiver fora.
Uso: python render_local.py PASTA [--saida previa.mp4]"""
import argparse, json, os, subprocess
import numpy as np
import cv2
from common import W, H, FPS, texto, Encoder, DEC_RGB

INK = np.array([0x0B, 0x0B, 0x0C], np.float32) / 255


def hx(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def e_out(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def e_in(x): x = min(max(x, 0.0), 1.0); return x ** 3
def e_io(x): x = min(max(x, 0.0), 1.0); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def anima(el, t):
    de, ds = el.get("dur_entrada", 0.25), el.get("dur_saida", 0.2)
    p = 1.0 if el.get("entrada") == "nenhuma" else e_out((t - el["ini"]) / de)
    q = 0.0 if el.get("saida") == "nenhuma" else e_in((t - (el["fim"] - ds)) / ds)
    dx = dy = 0.0; s = 1.0
    e, sa = el.get("entrada"), el.get("saida")
    if e == "sobe": dy += (1 - p) * 70
    if e == "escala": s = 0.86 + 0.14 * p
    if e == "desliza-esq": dx -= (1 - p) * 90
    if e == "desliza-dir": dx += (1 - p) * 90
    if sa == "afasta-esq": dx -= q * 700
    if sa == "afasta-dir": dx += q * 700
    if sa == "desce": dy += q * 70
    return p * (1 - q) * el.get("opacidade", 1.0), dx, dy, s


def pos(el, t):
    ks = el.get("chaves")
    if not ks:
        return el.get("x", 540), el.get("y", 960), el.get("w", 0), el.get("h", 0)
    ts = [k["t"] for k in ks]
    f = lambda key, d: float(np.interp(t, ts, [k.get(key, d) for k in ks]))
    return f("x", 540), f("y", 960), f("w", el.get("w", 0)), f("h", el.get("h", 0))


_cache = {}
def mtexto(s, fonte, tam, track):
    k = (s, fonte, tam, track)
    if k not in _cache:
        _cache[k] = texto(s, fonte, int(tam), track)
    return _cache[k]


def colar_texto(img, m, cx, cy, cor, op, s=1.0, escuro=False, sombra=False):
    if op <= 0.005:
        return img
    if s != 1.0:
        m = cv2.resize(m, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
    h, w = m.shape
    pad = 24
    big = np.zeros((h + 2 * pad, w + 2 * pad), np.float32); big[pad:pad + h, pad:pad + w] = m
    x0, y0 = int(round(cx - w / 2 - pad)), int(round(cy - h / 2 - pad))
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0, dx1, dy1 = max(0, x0), max(0, y0), min(W, x0 + big.shape[1]), min(H, y0 + big.shape[0])
    if dx1 <= dx0 or dy1 <= dy0:
        return img
    reg = img[dy0:dy1, dx0:dx1]
    mm = big[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0]
    if escuro:
        st = cv2.dilate(mm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
        sh = cv2.GaussianBlur(mm, (0, 0), 8) * 0.45
        reg[:] = reg * (1 - (np.maximum(st, sh) * op)[..., None]) + INK * (np.maximum(st, sh) * op)[..., None]
    elif sombra:
        sh = cv2.GaussianBlur(mm, (0, 0), 9) * 0.45
        reg[:] = reg * (1 - (sh * op)[..., None])
    reg[:] = reg * (1 - (mm * op)[..., None]) + cor * (mm * op)[..., None]
    return img


def mira(img, el, t, op, s):
    x, y, w, h = pos(el, t)
    w, h = w * s, h * s
    L = int(min(w, h) * 0.18)
    x0, y0, x1, y1 = int(x - w / 2), int(y - h / 2), int(x + w / 2), int(y + h / 2)
    lay = np.zeros((H, W), np.float32); dark = np.zeros((H, W), np.float32)
    esp = int(el.get("espessura", 6))
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        for m_, e_ in ((dark, esp + 5), (lay, esp)):
            cv2.line(m_, (cx, cy), (cx + dx * L, cy), 1.0, e_); cv2.line(m_, (cx, cy), (cx, cy + dy * L), 1.0, e_)
    if el.get("contorno_escuro"):
        img = img * (1 - (dark * op * 0.85)[..., None]) + INK * (dark * op * 0.85)[..., None]
    img = img * (1 - (lay * op)[..., None]) + hx(el["cor"]) * (lay * op)[..., None]
    if el.get("rotulo"):
        m = mtexto(el["rotulo"], "Inter-Medium.otf", 24, 0.16)
        img = colar_texto(img, m, x, y0 - 40 + m.shape[0] / 2, hx(el["cor"]), op, escuro=el.get("contorno_escuro", False))
    return img


def leitor_rgba(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 4)
        if len(b) < W * H * 4:
            return
        yield np.frombuffer(b, np.uint8).reshape(H, W, 4).astype(np.float32) / 255


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("pasta"); ap.add_argument("--saida", default="previa.mp4")
    ap.add_argument("--quadros", default="", help="só estes tempos (s), separados por vírgula: gera PNGs para revisão rápida")
    a = ap.parse_args(); P = a.pasta
    tl = json.load(open(os.path.join(P, "timeline.json")))
    els = tl["elementos"]
    grid = np.zeros((H, W), np.float32)
    grid[:, ::108] = 1; grid[::108, :] = 1
    base = subprocess.Popen(["ffmpeg", "-v", "error", "-i", os.path.join(P, "base.mp4"), "-vf", DEC_RGB, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    pessoa = leitor_rgba(os.path.join(P, "pessoa.webm"))
    tem_contorno = any(e["tipo"] == "contorno" for e in els) and os.path.exists(os.path.join(P, "contorno.webm"))
    contorno = leitor_rgba(os.path.join(P, "contorno.webm")) if tem_contorno else None
    so = sorted({int(round(float(x) * FPS)) for x in a.quadros.split(",") if x.strip()})
    enc = None if so else Encoder(os.path.join(P, "_previa.mp4"))
    n = int(tl["duracao"] * FPS) if not so else so[-1] + 1
    amostras = {}
    for i in range(n):
        b = base.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        t = i / FPS
        f = np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
        pr = next(pessoa, None)
        cr = next(contorno, None) if contorno else None
        if so and i not in so:
            continue
        img = f.copy()
        for el in els:
            if el["camada"] != "atras" or not (el["ini"] <= t < el["fim"]):
                continue
            op, dx, dy, s = anima(el, t)
            if el["tipo"] == "fundo":
                bg = hx(el.get("cor", "#0B0B0C")) + (grid[..., None] * 0.06 if el.get("grade") else 0)
                img = img * (1 - op) + bg * op
            elif el["tipo"] == "texto":
                m = mtexto(el["texto"], el["fonte"], el["tamanho"], el.get("tracking", 0))
                x, y, _, _ = pos(el, t)
                img = colar_texto(img, m, x + dx, y + dy, hx(el["cor"]), op, s, el.get("contorno_escuro", False), el.get("sombra", False))
        if pr is not None and any(e["camada"] == "atras" and e["ini"] <= t < e["fim"] for e in els):  # recorte só com algo atrás
            al = pr[..., 3:4]
            img = img * (1 - al) + pr[..., :3] * al
        for z in tl.get("zoom", []):
            if z["ini"] <= t < z["fim"]:
                k = z["de"] + (z["ate"] - z["de"]) * e_io((t - z["ini"]) / (z["fim"] - z["ini"]))
                M = np.float32([[k, 0, (1 - k) * z["cx"]], [0, k, (1 - k) * z["cy"]]])
                img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        for el in els:
            if el["camada"] != "frente" or not (el["ini"] <= t < el["fim"]):
                continue
            op, dx, dy, s = anima(el, t)
            if el["tipo"] == "contorno" and cr is not None:
                al = cr[..., 3:4] * op
                img = img * (1 - al) + cr[..., :3] * al
            elif el["tipo"] == "texto":
                m = mtexto(el["texto"], el["fonte"], el["tamanho"], el.get("tracking", 0))
                x, y, _, _ = pos(el, t)
                img = colar_texto(img, m, x + dx, y + dy, hx(el["cor"]), op, s, el.get("contorno_escuro", False), el.get("sombra", False))
            elif el["tipo"] == "mira":
                img = mira(img, el, t, op, s)
        for w in tl.get("legenda", []):
            if w["ini"] <= t < w["fim"]:
                pop = 0.86 + 0.14 * e_out((t - w["ini"]) / 0.09)
                m = mtexto(w["texto"], tl.get("fonte_legenda", "Inter-SemiBold.otf"), w["tamanho"], 0.01)
                if w.get("tarja"):  # faixa atrás da palavra, mesma medida da composição Remotion
                    tm = w["tamanho"] * pop
                    bw, bh = m.shape[1] * pop + 0.68 * tm, 1.1 * tm + 0.22 * tm
                    x0, y0 = int(w["x"] - bw / 2), int(w["y"] - bh / 2)
                    lay = np.zeros((H, W), np.float32)
                    cv2.rectangle(lay, (x0 + 14, y0), (x0 + int(bw) - 14, y0 + int(bh)), 1.0, -1)
                    cv2.rectangle(lay, (x0, y0 + 14), (x0 + int(bw), y0 + int(bh) - 14), 1.0, -1)
                    for cx_, cy_ in ((x0 + 14, y0 + 14), (x0 + int(bw) - 14, y0 + 14), (x0 + 14, y0 + int(bh) - 14), (x0 + int(bw) - 14, y0 + int(bh) - 14)):
                        cv2.circle(lay, (cx_, cy_), 14, 1.0, -1)
                    img = img * (1 - lay[..., None]) + hx(w["tarja"]) * lay[..., None]
                img = colar_texto(img, m, w["x"], w["y"], hx(w["cor"]), 1.0, pop, w.get("contorno_escuro", False), w.get("sombra", True))
        if so:
            cv2.imwrite(os.path.join(P, f"q_{t:06.2f}.jpg"), cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
            continue
        enc.write(img)
        amostras[round(t, 2)] = None
    base.terminate()
    if so:
        print("ok quadros", len(so)); return
    enc.close()
    out = os.path.join(P, a.saida)
    mix = os.path.join(P, "mix.wav")
    if os.path.exists(mix):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(P, "_previa.mp4"), "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-shortest", out], check=True)
        os.remove(os.path.join(P, "_previa.mp4"))
    else:
        os.replace(os.path.join(P, "_previa.mp4"), out)
    print("ok", out)


if __name__ == "__main__":
    main()
