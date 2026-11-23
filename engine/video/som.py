"""Etapa 6 · Som (sound designer). Efeitos gerados por código, só nas entradas que importam, mais a voz nivelada
e a música (opcional) abaixando sozinha quando a voz entra.
Uso: python som.py PASTA [--musica faixa.mp3] [--nivel_sfx 0.22]
Lê eventos_som.json e o áudio de base.mp4. Gera mix.wav (48 kHz) e o relatório de volume."""
import argparse, json, os, re, subprocess, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def whoosh(d=0.30):
    n = int(d * SR); x = rng.standard_normal(n).astype(np.float32)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    out = np.zeros(n, np.float32); y1 = y2 = 0.0
    for k in range(n):  # passa-faixa que sobe
        th = 2 * np.pi * (300 + 3500 * k / n) / SR; r = 0.97
        y = x[k] * (1 - r) + 2 * r * np.cos(th) * y1 - r * r * y2
        out[k] = y; y2, y1 = y1, y
    return out / (np.abs(out).max() + 1e-6) * env


def pop(f=1500, d=0.05):
    t = np.arange(int(d * SR)) / SR
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 70)).astype(np.float32)


def click(d=0.03):
    t = np.arange(int(d * SR)) / SR
    return ((np.sin(2 * np.pi * 2400 * t) + 0.5 * rng.standard_normal(len(t))) * np.exp(-t * 160)).astype(np.float32) * 0.7


def impacto(d=0.45):
    t = np.arange(int(d * SR)) / SR
    corpo = np.sin(2 * np.pi * (70 - 30 * t / d) * t) * np.exp(-t * 9)
    return (corpo + rng.standard_normal(len(t)) * np.exp(-t * 120) * 0.4).astype(np.float32)


SONS = {"whoosh": (whoosh, 0.9), "pop": (pop, 0.9), "click": (click, 0.8), "impacto": (impacto, 1.3)}


def main():
    ap = argparse.ArgumentParser()
    # efeitos mais baixos por padrão: a voz manda
    ap.add_argument("pasta"); ap.add_argument("--musica"); ap.add_argument("--nivel_sfx", type=float, default=0.06)
    a = ap.parse_args()
    P = a.pasta
    ev = json.load(open(os.path.join(P, "eventos_som.json")))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(P, "base.mp4")], capture_output=True, text=True).stdout)
    L = int(dur * SR)
    sfx = np.zeros(L, np.float32)
    ultimo = -9.0
    for e in sorted(ev, key=lambda x: x["t"]):
        if e["t"] - ultimo < 0.18 and e["som"] != "impacto":  # nada de efeito em cima de efeito
            continue
        fn, g = SONS[e["som"]]
        sig = fn() * g * a.nivel_sfx
        s = max(0, int((e["t"] - (0.12 if e["som"] == "whoosh" else 0)) * SR)); f = min(L, s + len(sig))
        if s >= L:  # depois do fim da fala (cartão final): fica para a montagem
            continue
        sfx[s:f] += sig[:f - s]
        ultimo = e["t"]
    sp = os.path.join(P, "_sfx.wav")
    with wave.open(sp, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(sfx, -1, 1) * 32767).astype(np.int16).tobytes())
    # Voz com o mínimo de tratamento (Otávio, 23/11: "parece que mexeu muito no áudio"):
    # só corta o grave inútil e acerta o volume com ganho fixo medido. Sem redutor de ruído, sem compressão que bombeia.
    fonte_voz = os.path.join(P, "base_audio.wav") if os.path.exists(os.path.join(P, "base_audio.wav")) else os.path.join(P, "base.mp4")
    medida = subprocess.run(["ffmpeg", "-hide_banner", "-i", fonte_voz, "-af", "highpass=f=70,ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    li = re.findall(r"I:\s+(-?[\d.]+) LUFS", medida)
    ganho = (-14.5 - float(li[-1])) if li else 0.0
    voz = f"[0:a]aresample=48000,highpass=f=70,volume={ganho:.2f}dB[v]"
    if a.musica:
        fc = voz + ";[v]asplit[v1][v2];[2:a]aresample=48000,volume=0.16[m0];[m0][v1]sidechaincompress=threshold=0.03:ratio=4:attack=40:release=400[m];[1:a]aresample=48000[s];[v2][s][m]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.84:attack=5:release=50:level=false,aresample=48000[a]"
        ins = ["-i", fonte_voz, "-i", sp, "-stream_loop", "-1", "-i", a.musica]
    else:
        fc = voz + ";[1:a]aresample=48000[s];[v][s]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.84:attack=5:release=50:level=false,aresample=48000[a]"
        ins = ["-i", fonte_voz, "-i", sp]
    out = os.path.join(P, "mix.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[a]", "-ac", "2", "-c:a", "pcm_s24le", "-t", f"{dur:.3f}", out], check=True)
    os.remove(sp)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r); TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    rel = {"lufs": float(I[-1]) if I else None, "pico_dbfs": float(TP[-1]) if TP else None, "efeitos": len(ev), "musica": bool(a.musica)}
    json.dump(rel, open(os.path.join(P, "06_som.json"), "w"), indent=1)
    print(json.dumps(rel))


if __name__ == "__main__":
    main()
