"""Etapa 2 · Cor (colorista).
Diagnóstico do bruto e grading natural, levemente cinematográfico:
pretos firmes, contraste leve, o resto mais neutro e esbranquiçado, pele natural e boca rosada.
Uso: python cor.py diagnostico PASTA            → 02_cor.json + 02_cor_antes_depois.jpg
     python cor.py aplicar PASTA [--entrada proxy.mp4] [--saida base_cor.mp4]"""
import argparse, json, os
import numpy as np
import cv2
from common import W, H, frames, Encoder, probe

PADRAO = {"preto": 0.035, "branco": 0.965, "contraste": 0.35, "sat_resto": 0.18, "sat_pele": 0.92, "calor_pele": 0.015,
          "brilho": 0.0, "wb_a": 0.0, "wb_b": 0.0}


def mascara_pele(rgb):
    """Pele e lábios (vermelho > azul, matiz quente), suavizada. Inclui a boca para manter o rosa."""
    u8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV).astype(np.float32)
    Hh, S, V = hsv[..., 0], hsv[..., 1] / 255, hsv[..., 2] / 255
    Hd = np.where(Hh > 170, Hh - 180, Hh)
    mh = np.clip((Hd + 12) / 4, 0, 1) * np.clip((24 - Hd) / 5, 0, 1)
    ms = np.clip((S - 0.10) / 0.08, 0, 1) * np.clip((0.88 - S) / 0.1, 0, 1)
    mv = np.clip((V - 0.16) / 0.10, 0, 1)
    mo = np.clip((rgb[..., 0] - rgb[..., 2] - 0.02) / 0.05, 0, 1)
    m = mh * ms * mv * mo
    w = rgb.shape[1]
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((max(3, w // 360) | 1,) * 2, np.uint8))
    kc = max(5, w // 45) | 1
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kc, kc)))
    return np.clip(cv2.GaussianBlur(m, (0, 0), w / 270) * 1.15, 0, 1)


def diagnostico(path, n=12):
    info = probe(path)
    total = int(info["duracao"] * 30)
    passo = max(1, total // n)
    L, S, A, B, pele_s, pele_h, amostras = [], [], [], [], [], [], []
    for i, f in frames(path, step=passo):
        lab = cv2.cvtColor(f, cv2.COLOR_RGB2LAB)
        lum = lab[..., 0] / 100
        L.append(np.percentile(lum, [1, 50, 99]))
        hsv = cv2.cvtColor((f * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        S.append(hsv[..., 1].mean() / 255)
        neutro = (np.hypot(lab[..., 1], lab[..., 2]) < 12) & (lum > 0.25) & (lum < 0.9)
        if neutro.mean() > 0.02:
            A.append(lab[..., 1][neutro].mean()); B.append(lab[..., 2][neutro].mean())
        m = mascara_pele(f) > 0.5
        if m.mean() > 0.005:
            pele_s.append(hsv[..., 1][m].mean() / 255); pele_h.append(hsv[..., 0][m].mean() * 2)
        amostras.append(f)
    L = np.array(L)
    d = {
        "preto_p1": round(float(L[:, 0].mean()), 3), "meio_p50": round(float(L[:, 1].mean()), 3), "branco_p99": round(float(L[:, 2].mean()), 3),
        "saturacao_media": round(float(np.mean(S)), 3),
        "dominante_a": round(float(np.mean(A)), 2) if A else 0.0, "dominante_b": round(float(np.mean(B)), 2) if B else 0.0,
        "pele_saturacao": round(float(np.mean(pele_s)), 3) if pele_s else None, "pele_matiz": round(float(np.mean(pele_h)), 1) if pele_h else None,
        "variacao_entre_quadros": round(float(L[:, 1].std()), 3),
    }
    leitura = []
    if d["preto_p1"] > 0.08: leitura.append("pretos lavados: firmar o ponto preto")
    if d["branco_p99"] < 0.85: leitura.append("imagem escura: subir os brancos")
    if abs(d["dominante_b"]) > 3: leitura.append("dominante " + ("amarela" if d["dominante_b"] > 0 else "azul") + ": corrigir o branco")
    if abs(d["dominante_a"]) > 3: leitura.append("dominante " + ("magenta" if d["dominante_a"] > 0 else "verde") + ": corrigir o branco")
    if d["variacao_entre_quadros"] > 0.05: leitura.append("exposição varia entre trechos: igualar")
    d["leitura"] = leitura or ["bruto equilibrado"]
    return d, amostras


def parametros(d):
    p = dict(PADRAO)
    p["wb_a"], p["wb_b"] = -d["dominante_a"], -d["dominante_b"]  # neutraliza a dominante
    p["preto"] = float(np.clip(d["preto_p1"] + 0.02, 0.02, 0.09))  # o p1 vira preto firme
    # Não esticar demais o branco: com o branco em 0,82 a pele estourou no vermelho (reprovado pelo revisor em 23/11).
    p["branco"] = float(np.clip(d["branco_p99"] + 0.06, 0.92, 0.99))
    return p


def aplicar(f, p, pele=None):
    lab = cv2.cvtColor(f, cv2.COLOR_RGB2LAB)
    lab[..., 1] += p["wb_a"]; lab[..., 2] += p["wb_b"]
    f = np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0, 1)
    x = np.clip((f - p["preto"]) / (p["branco"] - p["preto"]), 0, 1)
    s = x * x * (3 - 2 * x)
    x = np.clip(x * (1 - p["contraste"]) + s * p["contraste"] + p["brilho"], 0, 1)
    m = mascara_pele(f) if pele is None else pele
    cinza = (0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2])[..., None]
    sat = p["sat_resto"] * (1 - m[..., None]) + p["sat_pele"] * m[..., None]
    out = cinza + (x - cinza) * sat
    out[..., 0] += p["calor_pele"] * m; out[..., 2] -= p["calor_pele"] * m
    return joelho(out)


def joelho(x, inicio=0.86):
    """Altas luzes descem suave por canal em vez de bater no 1,0: a pele mantém textura (nada de vermelho chapado em 255)."""
    acima = x > inicio
    folga = 1.0 - inicio
    y = x.copy()
    y[acima] = inicio + folga * np.tanh((x[acima] - inicio) / folga)
    return np.clip(y, 0, 1)


def estouro_pele(f, m=None):
    """Fração da pele com algum canal acima de 0,985 (o revisor reprova acima de ~1%)."""
    m = mascara_pele(f) if m is None else m
    sel = m > 0.5
    if not sel.any():
        return 0.0
    return float((f[sel].max(-1) > 0.985).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["diagnostico", "aplicar"]); ap.add_argument("pasta")
    ap.add_argument("--entrada", default="proxy.mp4"); ap.add_argument("--saida", default="base_cor.mp4")
    a = ap.parse_args()
    ent = os.path.join(a.pasta, a.entrada)
    jp = os.path.join(a.pasta, "02_cor.json")
    if a.modo == "diagnostico":
        d, am = diagnostico(ent)
        p = parametros(d)
        json.dump({"diagnostico": d, "parametros": p}, open(jp, "w"), ensure_ascii=False, indent=1)
        idx = [0, len(am) // 2, len(am) - 1]
        linhas = []
        for k in idx:
            antes = (am[k] * 255).astype(np.uint8); depois = (aplicar(am[k], p) * 255).astype(np.uint8)
            linhas.append(np.hstack([cv2.resize(antes, (360, 640)), cv2.resize(depois, (360, 640))]))
        cv2.imwrite(os.path.join(a.pasta, "02_cor_antes_depois.jpg"), cv2.cvtColor(np.hstack(linhas), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(json.dumps(d, ensure_ascii=False))
    else:
        p = json.load(open(jp))["parametros"]
        info = probe(ent)
        enc = Encoder(os.path.join(a.pasta, "_cor_video.mp4"))
        for _, f in frames(ent):
            enc.write(aplicar(f, p))
        enc.close()
        out = os.path.join(a.pasta, a.saida)
        os.system(f'ffmpeg -v error -y -i "{os.path.join(a.pasta, "_cor_video.mp4")}" -i "{ent}" -map 0:v -map 1:a? -c copy "{out}" && rm "{os.path.join(a.pasta, "_cor_video.mp4")}"')
        print("ok", out, info["duracao"])


if __name__ == "__main__":
    main()
