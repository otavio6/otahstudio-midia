"""Montagem final por cenas (substitui o fundo-preto-e-texto fixo): cada trecho do vídeo é uma cena com um modo.
  pessoa   → o vídeo dele (com zoom opcional) e, por cima, uma camada em motion transparente (opcional)
  cheia    → só a cena em motion, ele sai de cena (a voz continua)
  canto    → a cena em motion na tela toda e ele pequeno numa moldura arredondada
  dividida → a cena em motion na metade de cima e ele na metade de baixo (sem reduzir: nitidez total)
As cenas são HTML/SVG animados (motion/base.js), renderizados quadro a quadro pelo motion.py.
O vídeo sai com UM encode só, aqui, na taxa de quadros do bruto.

Uso: VIDEO_FPS=24 python montar.py PASTA [--plano montagem.json] [--saida final.mp4] [--quadros 1.0,5.2]
A PASTA tem base.mp4 (cortado e com cor), mix.wav, 03_cortes.json e o montagem.json."""
import argparse, json, os, re, subprocess, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import W, H, FPS, SAFE, MARCAS, modelo, texto, DEC_RGB, ENC_YUV
import motion

INK = np.array(MARCAS["otavio"]["ink"], np.float32) / 255
LIMA = np.array(MARCAS["otavio"]["destaque"], np.float32) / 255
FONTE_LEG = "Inter-SemiBold.otf"


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


# ---------- rosto (para enquadrar a pessoa nas molduras) ----------
def rastrear_rosto(base, passo_s=1 / 6):
    det = cv2.FaceDetectorYN.create(modelo("yunet.onnx"), "", (W // 2, H // 2), 0.6)
    cap = cv2.VideoCapture(base)
    fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    passo = max(1, int(round(fps * passo_s)))
    ts, fs, i = [], [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % passo == 0:
            _, f = cap.retrieve()
            pequeno = cv2.resize(f, (W // 2, H // 2))
            _, r = det.detect(pequeno)
            if r is not None and len(r):
                x, y, w, h = (r[np.argmax(r[:, 2] * r[:, 3])][:4] * 2).tolist()
                ts.append(i / fps); fs.append([x + w / 2, y + h / 2, w, h])
        i += 1
    cap.release()
    fs = np.array(fs, np.float32)
    if len(fs) > 4:  # suaviza (sem tremer a moldura)
        k = np.ones(5) / 5
        fs = np.stack([np.convolve(np.pad(fs[:, j], 2, mode="edge"), k, "valid") for j in range(4)], 1)
    return np.array(ts), fs


def rosto_em(track, t):
    ts, fs = track
    if not len(ts):
        return np.array([W / 2, H * 0.45, 420, 560], np.float32)
    return np.array([np.interp(t, ts, fs[:, j]) for j in range(4)], np.float32)


# ---------- legenda (1 ou 2 palavras, faixa lima com texto preto) ----------
LIGA = {"a", "o", "as", "os", "de", "do", "da", "dos", "das", "que", "e", "com", "se", "um", "uma", "no", "na", "nos", "nas",
        "em", "pro", "pra", "por", "eu", "ele", "ela", "eles", "numa", "num", "sem", "seu", "sua", "é", "aí", "tá", "me", "mais", "muito"}


def grupos_legenda(palavras, max_chars=16, max_pal=4):
    """Legenda em unidades de sentido (2 a 4 palavras), sem terminar em artigo ou preposição, sem atravessar pausa ou pontuação."""
    out, atual = [], []
    def fecha():
        if atual:
            txt = " ".join(re.sub(r"[,.;:!?…]", "", w["texto"]) for w in atual).upper()
            out.append({"texto": txt, "ini": atual[0]["inicio"], "fim": atual[-1]["fim"], "palavras": [w["texto"] for w in atual]})
            atual.clear()
    lig = lambda w: re.sub(r"[,.;:!?…]", "", w["texto"]).lower() in LIGA
    for k, w in enumerate(palavras):
        atual.append(w)
        prox = palavras[k + 1] if k + 1 < len(palavras) else None
        pontua = w["texto"][-1:] in ",.;:!?…"
        pausa = prox is None or prox["inicio"] - w["fim"] > 0.28
        tamanho = len(" ".join(x["texto"] for x in atual))
        if prox is None or pontua or pausa:
            fecha(); continue
        if tamanho >= max_chars or len(atual) >= max_pal:
            if lig(w) and len(atual) > 1:  # não termina em artigo/preposição: a palavra de ligação abre a próxima
                atual.pop(); fecha(); atual.append(w)
            else:
                fecha()
    # palavra solta (pausa logo depois) gruda na anterior quando cabe
    juntos = []
    for g in out:
        if juntos and len(g["palavras"]) == 1 and g["ini"] - juntos[-1]["fim"] < 0.5 and len(juntos[-1]["texto"]) + 1 + len(g["texto"]) <= 24:
            j = juntos[-1]; j["texto"] += " " + g["texto"]; j["fim"] = g["fim"]; j["palavras"] += g["palavras"]
        else:
            juntos.append(g)
    out = juntos
    for k, g in enumerate(out):
        prox = out[k + 1]["ini"] if k + 1 < len(out) else g["fim"] + 0.5
        g["fim"] = min(prox, g["fim"] + 0.6)
    return out


_cache_txt = {}


def mascara_txt(s, tam):
    k = (s, tam)
    if k not in _cache_txt:
        _cache_txt[k] = texto(s, FONTE_LEG, tam, 0.01)
    return _cache_txt[k]


def pinta_legenda(img, g, t, y, tam=84):
    m = mascara_txt(g["texto"], tam)
    larg_max = 2 * min(W / 2 - SAFE["left"], W - SAFE["right"] - W / 2) - 0.75 * tam - 12  # a faixa inteira cabe na zona segura
    if m.shape[1] > larg_max:
        tam = int(tam * larg_max / m.shape[1]); m = mascara_txt(g["texto"], tam)
        larg_max = 2 * min(W / 2 - SAFE["left"], W - SAFE["right"] - W / 2) - 0.75 * tam - 12
        if m.shape[1] > larg_max:
            tam = int(tam * larg_max / m.shape[1]); m = mascara_txt(g["texto"], tam)
    pop = 0.88 + 0.12 * ease_out((t - g["ini"]) / 0.08)
    if pop != 1:
        m = cv2.resize(m, None, fx=pop, fy=pop, interpolation=cv2.INTER_LINEAR)
    h, w = m.shape
    cx = W / 2  # eixo do quadro (não o meio da zona segura: isso jogava a legenda 40 px para a esquerda)
    px, py = int(0.34 * tam * pop), int(0.2 * tam * pop)
    x0, y0, x1, y1 = int(cx - w / 2 - px), int(y - h / 2 - py), int(cx + w / 2 + px), int(y + h / 2 + py)
    faixa = np.zeros((H, W), np.uint8)
    r = int(0.16 * tam)
    cv2.rectangle(faixa, (x0 + r, y0), (x1 - r, y1), 255, -1); cv2.rectangle(faixa, (x0, y0 + r), (x1, y1 - r), 255, -1)
    for (a_, b_) in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv2.circle(faixa, (a_, b_), r, 255, -1, cv2.LINE_AA)
    faixa = faixa.astype(np.float32)[..., None] / 255
    img[:] = img * (1 - faixa) + LIMA * faixa
    tx0, ty0 = int(cx - w / 2), int(y - h / 2)
    sub = img[ty0:ty0 + h, tx0:tx0 + w]
    mm = m[:sub.shape[0], :sub.shape[1], None]
    sub[:] = sub * (1 - mm) + INK * mm


# ---------- camadas ----------
def ler_png(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        return None
    im = im.astype(np.float32) / 255
    if im.shape[2] == 4:
        return np.dstack([im[..., 2::-1], im[..., 3:4]])
    return im[..., ::-1]


def sobre(img, rgba):
    a = rgba[..., 3:4]
    return img * (1 - a) + rgba[..., :3] * a


def recorte_pessoa(frame, rosto, w, h, face_frac=0.42):
    fx, fy, fw, fh = rosto
    cw = min(W, fw / face_frac)
    ch = cw * h / w
    if ch > H:
        ch = H; cw = ch * w / h
    x0 = int(np.clip(fx - cw / 2, 0, W - cw)); y0 = int(np.clip(fy - ch * 0.40, 0, H - ch))
    crop = frame[y0:y0 + int(ch), x0:x0 + int(cw)]
    return cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA if cw > w else cv2.INTER_LANCZOS4)


def moldura_redonda(w, h, raio):
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (raio, 0), (w - raio, h), 255, -1); cv2.rectangle(m, (0, raio), (w, h - raio), 255, -1)
    for (cx, cy) in ((raio, raio), (w - raio, raio), (raio, h - raio), (w - raio, h - raio)):
        cv2.circle(m, (cx, cy), raio, 255, -1, cv2.LINE_AA)
    return cv2.GaussianBlur(m, (3, 3), 0).astype(np.float32)[..., None] / 255


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta"); ap.add_argument("--plano", default="montagem.json"); ap.add_argument("--saida", default="final.mp4")
    ap.add_argument("--quadros", default="")
    a = ap.parse_args(); P = a.pasta
    plano = json.load(open(os.path.join(P, a.plano)))
    pal = json.load(open(os.path.join(P, "03_cortes.json")))["palavras"]
    dur = float(plano.get("duracao") or json.load(open(os.path.join(P, "03_cortes.json")))["duracao_final"])
    base = os.path.join(P, plano.get("base", "base.mp4"))
    leg = grupos_legenda(pal)
    # Pontos de corte (fim de cada trecho) para disfarçar o salto com troca de escala, como um editor faz
    segs = json.load(open(os.path.join(P, "03_cortes.json")))["segmentos"]
    bordas, acc = [], 0.0
    for sg in segs:
        acc += sg["fim"] - sg["ini"]; bordas.append(acc)
    def escala_salto(t):
        k = sum(1 for b_ in bordas if b_ <= t + 1e-3)
        return plano.get("escala_salto", 1.10) if k % 2 == 1 else 1.0
    track = rastrear_rosto(base)
    so = sorted({int(round(float(x) * FPS)) for x in a.quadros.split(",") if x.strip()})

    # cenas em motion → quadros PNG (cache por cena)
    for k, c in enumerate(plano["cenas"]):
        if not c.get("html"):
            continue
        d = os.path.join(P, "_cenas", f"{k:02d}")
        c["_dir"] = d
        n = max(1, round((c["ate"] - c["de"]) * FPS))
        marca = os.path.join(d, ".ok")
        assinatura = f"{os.path.getmtime(os.path.join(P, c['html']))}:{n}:{c.get('transparente', False)}"
        if not (os.path.exists(marca) and open(marca).read() == assinatura):
            os.makedirs(d, exist_ok=True)
            if so:  # revisão rápida: só os quadros pedidos
                for i in so:
                    if c["de"] * FPS <= i < c["ate"] * FPS:
                        motion.um_quadro(os.path.join(P, c["html"]), os.path.join(d, f"{i - round(c['de'] * FPS):04d}.png"), i / FPS - c["de"], c.get("transparente", False))
            else:
                motion.quadros(os.path.join(P, c["html"]), d, c["ate"] - c["de"], FPS, c.get("transparente", False))
                open(marca, "w").write(assinatura)

    cenas = plano["cenas"]

    def cena_em(t):
        for k, c in enumerate(cenas):
            if c["de"] <= t < c["ate"]:
                return k, c
        return -1, {"modo": "pessoa"}

    def png_da_cena(c, i):
        if not c.get("_dir"):
            return None
        n = max(1, round((c["ate"] - c["de"]) * FPS))
        return ler_png(os.path.join(c["_dir"], f"{min(max(0, i - round(c['de'] * FPS)), n - 1):04d}.png"))

    def desenha(c, i, t, f, rosto, encolhe=1.0):
        """Uma cena num instante. encolhe<1 = transição 'encolhe' (a pessoa sai da tela cheia até a moldura)."""
        modo = c.get("modo", "pessoa")
        q = png_da_cena(c, i)
        if modo == "pessoa":
            img = f
            ks = escala_salto(t) if c.get("disfarca_saltos", True) else 1.0
            if ks != 1.0:
                M = np.float32([[ks, 0, (1 - ks) * rosto[0]], [0, ks, (1 - ks) * rosto[1]]])
                img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
            for z in plano.get("zoom", []):
                if z["de"] <= t < z["ate"]:
                    k = 1 + (z.get("escala", 1.06) - 1) * ease_io((t - z["de"]) / max(0.01, z["ate"] - z["de"]))
                    M = np.float32([[k, 0, (1 - k) * rosto[0]], [0, k, (1 - k) * rosto[1]]])
                    img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
            if q is not None:
                img = sobre(img, q) if q.shape[2] == 4 else q[..., :3]
            return img
        fundo = q[..., :3].copy() if q is not None else np.zeros((H, W, 3), np.float32) + INK
        if modo == "cheia":
            return fundo
        if modo == "canto":
            pc = c["pessoa"]
            e = ease_io(encolhe)
            w = int(lerp(W, pc["w"], e)); h = int(lerp(H, pc["h"], e))
            cx, cy = lerp(W / 2, pc["x"], e), lerp(H / 2, pc["y"], e)
            if e >= 0.999:
                pes = recorte_pessoa(f, rosto, w, h)
            else:  # interpola o recorte do quadro inteiro até o recorte do rosto
                fx, fy, fw, fh = rosto
                cw1 = min(W, fw / 0.42); ch1 = cw1 * pc["h"] / pc["w"]
                x1 = float(np.clip(fx - cw1 / 2, 0, W - cw1)); y1 = float(np.clip(fy - ch1 * 0.40, 0, H - ch1))
                x0r, y0r = lerp(0, x1, e), lerp(0, y1, e); cw, ch = lerp(W, cw1, e), lerp(H, ch1, e)
                pes = cv2.resize(f[int(y0r):int(y0r + ch), int(x0r):int(x0r + cw)], (w, h), interpolation=cv2.INTER_AREA)
            mk = moldura_redonda(w, h, max(1, int(pc.get("raio", 36) * e)))
            x0, y0 = int(cx - w / 2), int(cy - h / 2)
            img = fundo if e >= 0.999 else fundo * e + f * (1 - e)
            reg = img[max(0, y0):y0 + h, max(0, x0):x0 + w]
            pes = pes[max(0, -y0):max(0, -y0) + reg.shape[0], max(0, -x0):max(0, -x0) + reg.shape[1]]
            mk = mk[max(0, -y0):max(0, -y0) + reg.shape[0], max(0, -x0):max(0, -x0) + reg.shape[1]]
            reg[:] = reg * (1 - mk) + pes * mk
            return img
        if modo == "dividida":
            meio = int(c.get("meio", H // 2))
            y0 = int(np.clip(rosto[1] - (H - meio) * 0.40, 0, meio))
            fundo[meio:] = f[y0:y0 + (H - meio)]
            return fundo
        return f

    def lerp(a_, b_, k_):
        return a_ + (b_ - a_) * k_

    TRANS = 0.32  # duração das transições com movimento
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", base, "-vf", DEC_RGB, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = None
    if not so:
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                "-i", os.path.join(P, plano.get("audio", "mix.wav")), "-map", "0:v", "-map", "1:a",
                                "-vf", ENC_YUV, "-af", "apad", "-t", f"{dur:.3f}",
                                "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-profile:v", "high",
                                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                                "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", os.path.join(P, a.saida)], stdin=subprocess.PIPE)
    n = int(round(dur * FPS))
    f_ult = None
    for i in range(n):
        b = dec.stdout.read(W * H * 3)
        if len(b) >= W * H * 3:
            f_ult = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        elif f_ult is None:
            break
        if so and i not in so:
            continue
        t = i / FPS
        f = f_ult.astype(np.float32) / 255  # depois do fim da fala, o último quadro segura (cartão final por cima)
        k, c = cena_em(t)
        rosto = rosto_em(track, t)
        prev = cenas[k - 1] if k > 0 else None
        tipo = c.get("transicao", "corte")
        dt = t - c.get("de", 0)
        if prev is not None and tipo == "encolhe" and dt < TRANS * 1.4 and c.get("modo") == "canto":
            img = desenha(c, i, t, f, rosto, encolhe=dt / (TRANS * 1.4))
        elif prev is not None and tipo in ("desliza", "funde") and dt < TRANS:
            antes = desenha(prev, i, t, f, rosto)
            depois = desenha(c, i, t, f, rosto)
            e = ease_io(dt / TRANS)
            if tipo == "funde":
                img = antes * (1 - e) + depois * e
            else:  # a cena nova sobe e empurra a anterior para cima
                o = int(round((1 - e) * H))
                img = np.empty_like(depois)
                if o:
                    img[:o] = antes[H - o:]
                img[o:] = depois[:H - o]
        else:
            img = desenha(c, i, t, f, rosto)
        img = img.copy()
        em_transicao = prev is not None and tipo != "corte" and dt < TRANS * 1.4
        prox = cenas[k + 1] if 0 <= k < len(cenas) - 1 else None
        antes_troca = prox is not None and prox.get("modo") != c.get("modo") and prox["de"] - t < 0.12
        if c.get("legenda", True) and not em_transicao and not antes_troca:
            g = next((g for g in leg if g["ini"] <= t < g["fim"]), None)
            ocultar = {re.sub(r"[,.;:!?…]", "", x).lower() for x in c.get("legenda_ocultar", [])}
            if g and any(re.sub(r"[,.;:!?…]", "", w).lower() in ocultar for w in g["palavras"]):
                g = None
            if g:
                pinta_legenda(img, g, t, c.get("legenda_y", H - SAFE["bottom"] - 70))
        out = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        if so:
            cv2.imwrite(os.path.join(P, f"m_{t:06.2f}.jpg"), cv2.cvtColor(out, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
        else:
            enc.stdin.write(out.tobytes())
    dec.terminate()
    if enc:
        enc.stdin.close(); enc.wait()
        print("ok", os.path.join(P, a.saida))
    else:
        print("ok quadros", len(so))


if __name__ == "__main__":
    main()
