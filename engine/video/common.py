"""Base do kit do editor: formato, marca, leitura e escrita de vídeo, texto, contraste e modelos."""
import json, os, subprocess, urllib.request
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
# Zona segura do Reels (1080×1920): a interface cobre o topo, a base e a coluna de botões à direita.
SAFE = {"top": 250, "bottom": 340, "left": 60, "right": 140}
FONT_DIR = "/usr/share/fonts/opentype/inter/"

# Paletas por marca. A cor de destaque só entra onde o contraste permite.
MARCAS = {
    "otavio": {"ink": (0x0B, 0x0B, 0x0C), "branco": (0xF7, 0xF7, 0xF5), "destaque": (0xD4, 0xFF, 0x3A),
               "destaque_claro": (0x1F, 0x4F, 0xFF), "fonte": "Inter-SemiBold.otf", "fonte_display": "InterDisplay-Black.otf"},
}

MODELOS = {
    "rvm.onnx": "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx",
    "yunet.onnx": "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
}
MODEL_DIR = os.environ.get("VIDEO_MODELOS", os.path.expanduser("~/.cache/otahstudio-video"))


def modelo(nome):
    """Caminho do arquivo do modelo (só dados, rodam no onnxruntime/OpenCV). Baixa se faltar."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    p = os.path.join(MODEL_DIR, nome)
    if not os.path.exists(p) or os.path.getsize(p) < 100_000:
        urllib.request.urlretrieve(MODELOS[nome], p)
    return p


def rgb(c):
    return np.array(c, np.float32) / 255


# ---------- vídeo ----------
def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height,r_frame_rate,color_transfer,color_primaries",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    num, den = v["r_frame_rate"].split("/")
    return {"duracao": float(j["format"]["duration"]), "w": v["width"], "h": v["height"], "fps": float(num) / float(den),
            "trc": v.get("color_transfer", ""), "hdr": v.get("color_transfer", "") in ("arib-std-b67", "smpte2084"),
            "audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def proxy_sdr(src, dst, ini=None, dur=None):
    """Converte o bruto para 1080×1920, 30 fps, SDR bt709 (iPhone grava em HDR/HLG)."""
    info = probe(src)
    vf = []
    if info["hdr"]:
        vf.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
    vf.append(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}")
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if ini is not None:
        cmd += ["-ss", str(ini)]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-i", src, "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", dst]
    subprocess.run(cmd, check=True)
    return dst


def frames(path, w=W, h=H, step=1):
    """Lê quadros RGB float32 (0–1). step=3 lê um a cada 3."""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-"], stdout=subprocess.PIPE)
    i = 0
    try:
        while True:
            b = p.stdout.read(w * h * 3)
            if len(b) < w * h * 3:
                break
            if i % step == 0:
                yield i, np.frombuffer(b, np.uint8).reshape(h, w, 3).astype(np.float32) / 255
            i += 1
    finally:
        p.stdout.close(); p.terminate()


class Encoder:
    def __init__(self, path, w=W, h=H, fps=FPS, crf=16):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                                   "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
                                   "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", path], stdin=subprocess.PIPE)

    def write(self, f):
        self.p.stdin.write((np.clip(f, 0, 1) * 255).astype(np.uint8).tobytes())

    def close(self):
        self.p.stdin.close(); self.p.wait()


# ---------- curvas de movimento (uma por vídeo) ----------
def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------- texto ----------
def texto(s, fonte="Inter-SemiBold.otf", tam=84, track=0.0):
    """Máscara (float 0–1) do texto, recortada justa."""
    f = ImageFont.truetype(FONT_DIR + fonte, tam)
    ws = [(f.getbbox(c)[2] - f.getbbox(c)[0]) if c != " " else tam * 0.28 for c in s]
    tw = int(sum(ws) + track * tam * max(0, len(s) - 1)) + 30
    asc, desc = f.getmetrics()
    im = Image.new("L", (tw, asc + desc + 16), 0)
    d = ImageDraw.Draw(im)
    x = 15
    for c, w in zip(s, ws):
        d.text((x, 8), c, font=f, fill=255)
        x += w + track * tam
    a = np.asarray(im, np.float32) / 255
    ys, xs = np.where(a > 0.02)
    if not len(ys):
        return a
    return a[max(0, ys.min() - 4):ys.max() + 5, max(0, xs.min() - 4):xs.max() + 5]


def colar(canvas, camada, cx, cy, escala=1.0, alfa=1.0):
    """Cola a máscara centrada em (cx, cy) num canvas H×W (máximo). Devolve a caixa usada (x0, y0, x1, y1)."""
    if alfa <= 0:
        return None
    if escala != 1.0:
        camada = cv2.resize(camada, None, fx=escala, fy=escala, interpolation=cv2.INTER_LINEAR)
    h, w = camada.shape
    Hc, Wc = canvas.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0, dx1, dy1 = max(0, x0), max(0, y0), min(Wc, x0 + w), min(Hc, y0 + h)
    if dx1 <= dx0 or dy1 <= dy0:
        return None
    canvas[dy0:dy1, dx0:dx1] = np.maximum(canvas[dy0:dy1, dx0:dx1], camada[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0] * alfa)
    return (x0, y0, x0 + w, y0 + h)


def pintar(img, mascara, cor, opacidade=1.0):
    m = (mascara * opacidade)[..., None]
    return img * (1 - m) + np.asarray(cor, np.float32) * m


# ---------- contraste (regra: a cor sai do fundo) ----------
def luminancia(c):
    c = np.asarray(c, np.float32)
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def razao_contraste(c1, c2):
    l1, l2 = float(luminancia(c1)), float(luminancia(c2))
    a, b = max(l1, l2), min(l1, l2)
    return (a + 0.05) / (b + 0.05)


def cor_pelo_fundo(img, caixa, marca="otavio", destaque=False, grande=True):
    """Escolhe a cor do texto pela região de fundo (pior caso: percentis claro e escuro da região).
    Fundo claro → preto. Fundo escuro → branco, ou o destaque se ele tiver contraste. Devolve (cor, razão, precisa_sombra)."""
    m = MARCAS[marca]
    x0, y0, x1, y1 = [int(v) for v in caixa]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(img.shape[1], x1), min(img.shape[0], y1)
    reg = img[y0:y1, x0:x1].reshape(-1, 3)
    if not len(reg):
        return rgb(m["branco"]), 21.0, False
    L = luminancia(reg)
    claro, escuro = reg[np.argmin(np.abs(L - np.percentile(L, 90)))], reg[np.argmin(np.abs(L - np.percentile(L, 10)))]
    minimo = 3.0 if grande else 4.5
    opcoes = []
    if destaque:
        opcoes += [m["destaque"], m["destaque_claro"]]
    opcoes += [m["branco"], m["ink"]]
    melhor = None
    for c in opcoes:
        r = min(razao_contraste(rgb(c), claro), razao_contraste(rgb(c), escuro))
        if r >= minimo:
            return rgb(c), r, False
        if melhor is None or r > melhor[1]:
            melhor = (rgb(c), r)
    return melhor[0], melhor[1], True  # nenhuma passa sozinha: usar sombra/faixa ou trocar de lugar
