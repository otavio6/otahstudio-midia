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
    ap.add_argument("pasta"); ap.add_argument("--musica"); ap.add_argument("--nivel_sfx", type=float, default=0.02)
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
    ganho = (-13.6 - float(li[-1])) if li else 0.0
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
    # Cauda: se a montagem passa do fim da fala (cartão final), completa com o som ambiente da própria gravação
    # (o trecho mais silencioso da voz, em laço com cruzamento), em vez de silêncio digital.
    mp = os.path.join(P, "montagem.json")
    dur_total = json.load(open(mp)).get("duracao", dur) if os.path.exists(mp) else dur
    if dur_total > dur + 0.05:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", out, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True).stdout
        x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
        falta = int((dur_total - len(x) / SR) * SR) + SR // 10
        rampa = np.linspace(0, 1, SR // 20)[:, None]
        # Revisor 27/11: laço de 0,5 s fazia "tic-tic" na cartela. Agora: um trecho CONTÍNUO de ambiente do bruto inteiro
        # (proxy_audio.wav), o mais calmo e sem transiente (menor pico de energia em quadros de 20 ms), com o mesmo tratamento da voz.
        bruto = os.path.join(P, "proxy_audio.wav")
        cauda = None
        if os.path.exists(bruto):
            rb = subprocess.run(["ffmpeg", "-v", "error", "-i", bruto, "-af", f"aresample=48000,highpass=f=70,volume={ganho:.2f}dB",
                                 "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True).stdout
            b = np.frombuffer(rb, np.float32).reshape(-1, 2)
            q = int(0.02 * SR); nq = len(b) // q
            if nq * q > falta + SR:
                e = np.sqrt((b[:nq * q, 0].reshape(nq, q) ** 2).mean(1)) + 1e-9
                from scipy.signal import butter, sosfilt  # agudo separado: estalo e tique aparecem ali antes
                hf = sosfilt(butter(4, 2500, "hp", fs=SR, output="sos"), b[:nq * q, 0])
                eh = np.sqrt((hf.reshape(nq, q) ** 2).mean(1)) + 1e-9
                nw = falta // q + 1
                pico = np.array([max(e[k:k + nw].max() / np.median(e[k:k + nw]), eh[k:k + nw].max() / np.median(eh[k:k + nw])) * e[k:k + nw].mean()
                                 for k in range(0, nq - nw, 5)])
                k0 = int(np.argmin(pico)) * 5
                cauda = b[k0 * q:k0 * q + falta].copy()
        if cauda is None:  # sem bruto: laço longo com cruzamento de 50 ms
            jan = int(1.5 * SR)
            rms = [np.sqrt((x[i:i + jan] ** 2).mean()) for i in range(0, max(1, len(x) - jan), jan // 4)]
            i0 = int(np.argmin(rms)) * (jan // 4)
            amb = x[i0:i0 + jan].copy(); cf = SR // 20
            partes = [amb]
            while sum(len(p_) for p_ in partes) - cf * (len(partes) - 1) < falta:
                ant = partes[-1]; nov = amb.copy()
                w = np.linspace(0, 1, cf)[:, None]
                ant[-cf:] = ant[-cf:] * (1 - w) + nov[:cf] * w
                partes.append(nov[cf:])
            cauda = np.vstack(partes)[:falta]
        cauda[:len(rampa)] *= rampa
        cauda[-len(rampa) * 4:] *= np.linspace(1, 0, len(rampa) * 4)[:, None]
        x = np.vstack([x, cauda])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-", "-c:a", "pcm_s24le", out], input=x.astype(np.float32).tobytes(), check=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r); TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    rel = {"lufs": float(I[-1]) if I else None, "pico_dbfs": float(TP[-1]) if TP else None, "efeitos": len(ev), "musica": bool(a.musica)}
    json.dump(rel, open(os.path.join(P, "06_som.json"), "w"), indent=1)
    print(json.dumps(rel))


if __name__ == "__main__":
    main()
