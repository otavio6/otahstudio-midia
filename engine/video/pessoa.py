"""Recorte da pessoa no vídeo já cortado: gera pessoa.webm (com transparência, para as camadas de trás no Remotion),
contorno.webm (linha em volta do corpo, opcional) e ocupacao.npz (rosto e corpo a 10 quadros/s) do vídeo final.
Uso: python pessoa.py PASTA [--entrada base.mp4] [--contorno #D4FF3A]"""
import argparse, os, subprocess
import numpy as np
import cv2
from common import W, H, FPS, frames
from ocupacao import Rastreador


def enc_alpha(path):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "30", "-row-mt", "1",
                             "-deadline", "realtime", "-cpu-used", "8", path], stdin=subprocess.PIPE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta"); ap.add_argument("--entrada", default="base.mp4"); ap.add_argument("--contorno", default="")
    a = ap.parse_args()
    tr = Rastreador()
    pe = enc_alpha(os.path.join(a.pasta, "pessoa.webm"))
    ce = enc_alpha(os.path.join(a.pasta, "contorno.webm")) if a.contorno else None
    cor = np.array([int(a.contorno[i:i + 2], 16) for i in (1, 3, 5)], np.uint8) if a.contorno else None
    ts, faces, mattes = [], [], []
    for i, f in frames(os.path.join(a.pasta, a.entrada)):
        alpha, face = tr(f)
        rgba = np.dstack([(f * 255).astype(np.uint8), (alpha * 255).astype(np.uint8)])
        pe.stdin.write(rgba.tobytes())
        if ce:
            dil = cv2.dilate((alpha > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
            st = np.clip(cv2.GaussianBlur(dil.astype(np.float32), (0, 0), 1.1) - alpha, 0, 1)
            c = np.zeros((H, W, 4), np.uint8); c[..., :3] = cor; c[..., 3] = (st * 255).astype(np.uint8)
            ce.stdin.write(c.tobytes())
        if i % (FPS // 10) == 0:
            ts.append(i / FPS)
            faces.append(face if face is not None else np.array([np.nan] * 4, np.float32))
            mattes.append(cv2.resize((alpha * 255).astype(np.uint8), (W // 8, H // 8), interpolation=cv2.INTER_AREA))
    for e in (pe, ce):
        if e:
            e.stdin.close(); e.wait()
    np.savez_compressed(os.path.join(a.pasta, "ocupacao_final.npz"), t=np.array(ts), face=np.stack(faces), matte=np.stack(mattes))
    print("ok", len(ts), "amostras")


if __name__ == "__main__":
    main()
