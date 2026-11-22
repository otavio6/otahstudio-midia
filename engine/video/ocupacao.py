"""Mapa de ocupação: onde estão o rosto e o corpo (com as mãos) em cada momento, e onde há espaço livre na grade."""
import numpy as np
import cv2
import onnxruntime as ort
from common import W, H, SAFE, modelo

GRADE = (6, 10)  # colunas × linhas dentro da zona segura


class Rastreador:
    """Recorte da pessoa (RVM) + rosto (YuNet), quadro a quadro, com suavização."""

    def __init__(self, downsample=0.25):
        self.sess = ort.InferenceSession(modelo("rvm.onnx"), providers=["CPUExecutionProvider"])
        self.rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
        self.dr = np.array([downsample], np.float32)
        self.det = cv2.FaceDetectorYN.create(modelo("yunet.onnx"), "", (W // 2, H // 2), 0.6, 0.3, 50)
        self.face = None

    def __call__(self, frame):
        _, pha, *self.rec = self.sess.run(None, {"src": frame.transpose(2, 0, 1)[None].copy(), "r1i": self.rec[0], "r2i": self.rec[1],
                                                 "r3i": self.rec[2], "r4i": self.rec[3], "downsample_ratio": self.dr})
        alpha = np.clip((pha[0, 0] - 0.04) / 0.92, 0, 1)
        small = cv2.cvtColor((frame[::2, ::2] * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        _, fs = self.det.detect(np.ascontiguousarray(small))
        if fs is not None and len(fs):
            b = fs[np.argmax(fs[:, 2] * fs[:, 3])][:4] * 2
            f = np.array([b[0] + b[2] / 2, b[1] + b[3] / 2, b[2], b[3]], np.float32)
            self.face = f if self.face is None else self.face * 0.75 + f * 0.25
        return alpha, (None if self.face is None else self.face.copy())


def ocupado(alpha, face, margem_rosto=0.35, dilata=40):
    """Máscara do que não pode ser coberto: corpo (com mãos) dilatado + rosto com margem."""
    occ = cv2.dilate((alpha > 0.35).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilata * 2 + 1, dilata * 2 + 1)))
    if face is not None:
        fx, fy, fw, fh = face
        x0, y0 = int(fx - fw * (0.5 + margem_rosto)), int(fy - fh * (0.75 + margem_rosto))
        x1, y1 = int(fx + fw * (0.5 + margem_rosto)), int(fy + fh * (0.62 + margem_rosto))
        occ[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = 1
    return occ.astype(np.float32)


def fora_da_zona_segura(caixa):
    x0, y0, x1, y1 = caixa
    return x0 < SAFE["left"] or y0 < SAFE["top"] or x1 > W - SAFE["right"] or y1 > H - SAFE["bottom"]


def sobreposicao(caixa, occ):
    x0, y0, x1, y1 = [int(v) for v in caixa]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return 1.0
    return float(occ[y0:y1, x0:x1].mean())


def achar_lugar(occs, w, h, preferencias=("topo", "esquerda", "direita", "base"), max_sobrepor=0.02):
    """Procura, na grade dentro da zona segura, um lugar onde um elemento w×h fica livre durante TODA a sua vida
    (occs = lista de máscaras de ocupação amostradas no intervalo). Devolve (cx, cy) ou None."""
    occ = np.max(np.stack(occs), 0) if len(occs) > 1 else occs[0]
    x_min, x_max = SAFE["left"] + w / 2, W - SAFE["right"] - w / 2
    y_min, y_max = SAFE["top"] + h / 2, H - SAFE["bottom"] - h / 2
    if x_min > x_max or y_min > y_max:
        return None
    cols, rows = GRADE
    xs = np.linspace(x_min, x_max, cols * 2 + 1)
    ys = np.linspace(y_min, y_max, rows * 2 + 1)
    cand = []
    for cy in ys:
        for cx in xs:
            cx_, cy_ = float(cx), float(cy)
            s = sobreposicao((cx_ - w / 2, cy_ - h / 2, cx_ + w / 2, cy_ + h / 2), occ)
            if s <= max_sobrepor:
                cand.append((cx_, cy_, s))
    if not cand:
        return None

    def score(c):
        cx, cy, s = c
        pen = s * 10
        for k, p in enumerate(preferencias):  # quanto mais cedo na lista, melhor
            ok = (p == "topo" and cy < H * 0.42) or (p == "base" and cy > H * 0.6) or (p == "esquerda" and cx < W * 0.42) or (p == "direita" and cx > W * 0.58) or (p == "centro" and abs(cx - W / 2) < W * 0.12)
            if ok:
                return pen + k
        return pen + len(preferencias)
    cand.sort(key=score)
    return cand[0][0], cand[0][1]
