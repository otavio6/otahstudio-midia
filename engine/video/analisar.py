"""Etapa 1 · Assistir e entender.
Uso: python analisar.py BRUTO PASTA [--transcricao palavras.json]
Gera: proxy.mp4 (SDR 1080×1920 30 fps), ocupacao.npz, folha.jpg (1 quadro por segundo) e 01_analise.json."""
import argparse, json, os, re, subprocess
import numpy as np
import cv2
from common import W, H, FPS, probe, proxy_sdr, frames
from ocupacao import Rastreador

VICIOS = {"né", "tipo", "éé", "ééé", "hã", "hum", "ahn", "eh", "é...", "assim"}
STOP = set("a o as os um uma de da do das dos e é em no na nos nas que com por para pra pro se não mais mas como eu você ele ela isso esse essa aqui lá já só também muito tá tem ter ser foi vai sua seu".split())


def ler_transcricao(p):
    j = json.load(open(p))
    ws = j.get("palavras") or j.get("words") or j
    out = []
    for w in ws:
        if isinstance(w, dict) and w.get("type", "word") != "word":
            continue
        t = w.get("texto", w.get("text", "")).strip()
        a, b = w.get("inicio", w.get("start")), w.get("fim", w.get("end"))
        if t and a is not None:
            out.append({"texto": t, "inicio": float(a), "fim": float(b)})
    return out


def marcar(palavras):
    """Marca vícios, repetições, pausas e frases. Quem decide o que cortar é o montador (etapa 3)."""
    norm = [re.sub(r"[^\wáéíóúâêôãõç]", "", w["texto"].lower()) for w in palavras]
    for i, w in enumerate(palavras):
        w["vicio"] = norm[i] in VICIOS
        w["repeticao"] = i > 0 and norm[i] == norm[i - 1] and norm[i] != ""
        w["pausa_depois"] = round(palavras[i + 1]["inicio"] - w["fim"], 3) if i + 1 < len(palavras) else 0.0
        w["candidata_chave"] = len(norm[i]) >= 6 and norm[i] not in STOP
    # repetição de trecho de 2–3 palavras ("o erro o erro é")
    for n in (3, 2):
        for i in range(len(norm) - 2 * n + 1):
            if norm[i:i + n] == norm[i + n:i + 2 * n] and all(norm[i:i + n]):
                for k in range(i, i + n):
                    palavras[k]["repeticao"] = True
    frases, atual = [], []
    for w in palavras:
        atual.append(w)
        if re.search(r"[.!?]$", w["texto"]) or w["pausa_depois"] > 0.45:
            frases.append({"texto": " ".join(x["texto"] for x in atual), "inicio": atual[0]["inicio"], "fim": atual[-1]["fim"]})
            atual = []
    if atual:
        frases.append({"texto": " ".join(x["texto"] for x in atual), "inicio": atual[0]["inicio"], "fim": atual[-1]["fim"]})
    return palavras, frases


def audio_info(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "silencedetect=n=-35dB:d=0.3,ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    sil, ini = [], None
    for ln in r.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", ln)
        if m: ini = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+)", ln)
        if m and ini is not None:
            sil.append([round(ini, 3), round(float(m.group(1)), 3)]); ini = None
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    LRA = re.findall(r"LRA:\s+([\d.]+) LU", r)
    TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return {"lufs": float(I[-1]) if I else None, "lra": float(LRA[-1]) if LRA else None, "pico_dbfs": float(TP[-1]) if TP else None, "silencios": sil}


def cortes_de_cena(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "select='gt(scene,0.3)',showinfo", "-f", "null", "-"], capture_output=True, text=True).stderr
    return [round(float(x), 2) for x in re.findall(r"pts_time:([\d.]+)", r)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bruto"); ap.add_argument("pasta"); ap.add_argument("--transcricao")
    ap.add_argument("--ini", type=float); ap.add_argument("--dur", type=float)
    a = ap.parse_args()
    os.makedirs(a.pasta, exist_ok=True)
    info = probe(a.bruto)
    proxy = proxy_sdr(a.bruto, os.path.join(a.pasta, "proxy.mp4"), a.ini, a.dur)
    pinfo = probe(proxy)

    # mapa de ocupação a 10 quadros/s
    tr = Rastreador()
    ts, faces, mattes, thumbs = [], [], [], []
    passo = FPS // 10
    for i, f in frames(proxy):
        alpha, face = tr(f)  # roda em todo quadro (o recorte é recorrente)
        if i % passo == 0:
            ts.append(i / FPS)
            faces.append(face if face is not None else np.array([np.nan] * 4, np.float32))
            mattes.append(cv2.resize((alpha * 255).astype(np.uint8), (W // 8, H // 8), interpolation=cv2.INTER_AREA))
        if i % FPS == 0:
            thumbs.append(cv2.resize((f * 255).astype(np.uint8), (180, 320)))
    np.savez_compressed(os.path.join(a.pasta, "ocupacao.npz"), t=np.array(ts), face=np.stack(faces), matte=np.stack(mattes))

    # folha de contato (1 quadro por segundo) para assistir de relance
    cols = 10
    rows = int(np.ceil(len(thumbs) / cols))
    sheet = np.zeros((rows * 320, cols * 180, 3), np.uint8)
    for k, th in enumerate(thumbs):
        r, c = divmod(k, cols)
        sheet[r * 320:(r + 1) * 320, c * 180:(c + 1) * 180] = th
        cv2.putText(sheet, f"{k}s", (c * 180 + 6, r * 320 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    cv2.imwrite(os.path.join(a.pasta, "folha.jpg"), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])

    fa = np.stack(faces)
    ok = ~np.isnan(fa[:, 0])
    res = {
        "bruto": os.path.basename(a.bruto), "original": info, "proxy": pinfo,
        "audio": audio_info(proxy), "cortes_de_cena": cortes_de_cena(proxy),
        "rosto": {"detectado_em": round(float(ok.mean()), 3),
                  "centro_medio": [round(float(np.nanmean(fa[:, 0])), 1), round(float(np.nanmean(fa[:, 1])), 1)] if ok.any() else None,
                  "tamanho_medio": [round(float(np.nanmean(fa[:, 2])), 1), round(float(np.nanmean(fa[:, 3])), 1)] if ok.any() else None},
    }
    if a.transcricao:
        pal, fr = marcar(ler_transcricao(a.transcricao))
        if a.ini:
            for w in pal:
                w["inicio"] -= a.ini; w["fim"] -= a.ini
            pal = [w for w in pal if w["fim"] > 0 and (a.dur is None or w["inicio"] < a.dur)]
            pal, fr = marcar(pal)
        res["palavras"], res["frases"] = pal, fr
        res["resumo_fala"] = {"palavras": len(pal), "vicios": sum(w["vicio"] for w in pal), "repeticoes": sum(w["repeticao"] for w in pal),
                              "pausas_longas": sum(w["pausa_depois"] > 0.45 for w in pal)}
    else:
        res["aviso"] = "Sem transcrição: as etapas de corte e legenda precisam dela (Whisper no VPS)."
    json.dump(res, open(os.path.join(a.pasta, "01_analise.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("audio", "rosto")}, ensure_ascii=False)[:600])


if __name__ == "__main__":
    main()
