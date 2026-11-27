"""Etapa 3 · Corte (montador). Corta pela transcrição, palavra por palavra: vícios, repetições e pausas longas,
deixando o respiro certo. Com proxy_audio.wav na pasta (o normal), TODO corte cai dentro de um silêncio medido no
áudio (plano_no_silencio): vício colado numa palavra que fica não sai (vai para `mantidas` e some só da legenda).
Sem o wav, cai no plano antigo pelo tempo do Whisper (plano_de_corte), que pode deixar sobra de palavra.
Uso: python cortar.py PASTA [--entrada base_cor.mp4] [--saida base.mp4] [--remover i,j,k] [--manter i,j] [--folga-db 9]
Lê 01_analise.json. Gera 03_cortes.json (segmentos, palavras com o tempo novo, mantidas e checagens) e o vídeo cortado.
Depois dele vem SEMPRE a revisão do áudio: conferir_audio.py preparar → transcrever → conferir_audio.py comparar."""
import argparse, json, os, subprocess
from common import FPS, CRF_INTERMEDIARIO

RESPIRO = 0.22        # pausa máxima mantida entre palavras da mesma ideia
RESPIRO_FORTE = 0.40  # pausa mantida antes de frase nova (respiro de efeito)
PAD_INI, PAD_FIM = 0.05, 0.09


def plano_de_corte(palavras, remover=(), manter=()):
    keep = []
    for i, w in enumerate(palavras):
        tirar = (w.get("vicio") or w.get("repeticao")) and i not in manter
        if i in remover:
            tirar = True
        if not tirar:
            keep.append(i)
    segs = []
    for k, i in enumerate(keep):
        w = palavras[i]
        ini, fim = w["inicio"] - PAD_INI, w["fim"] + PAD_FIM
        if segs:
            j = keep[k - 1]
            gap = w["inicio"] - palavras[j]["fim"]
            contiguo = (i == j + 1)
            nova_frase = palavras[j]["texto"].rstrip().endswith((".", "!", "?"))
            limite = RESPIRO_FORTE if nova_frase else RESPIRO
            if contiguo and gap <= limite + PAD_INI + PAD_FIM:
                segs[-1]["fim"] = max(segs[-1]["fim"], fim)
                segs[-1]["palavras"].append(i)
                continue
            # corte: fecha o anterior deixando o respiro, sem invadir a próxima palavra
            resp = min(limite, gap) if contiguo else 0.06
            segs[-1]["fim"] = min(palavras[j]["fim"] + max(PAD_FIM, resp / 2), w["inicio"] - 0.02)
            ini = max(w["inicio"] - max(PAD_INI, resp / 2), palavras[j]["fim"] + 0.02)
            if ini < segs[-1]["fim"]:  # palavras coladas: corta no meio do vão, sem sobrepor
                meio = (palavras[j]["fim"] + w["inicio"]) / 2
                segs[-1]["fim"] = ini = meio
        segs.append({"ini": max(0.0, ini), "fim": fim, "palavras": [i]})
    return segs


def bandas(wav):
    """Energia em 3 faixas (grave 150–900 Hz, médio 900–3000 Hz, agudo 3–8 kHz) a cada 5 ms, janela de 20 ms.
    O agudo é o que pega consoante sem voz (f, s, x, ch): no volume total elas parecem silêncio, e o corte comia
    o "fi" de "ficaram" e o "ss" de "isso"."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    x = np.concatenate([np.zeros(120, np.float32), x, np.zeros(200, np.float32)])  # centra a janela de 20 ms no quadro
    fr = np.lib.stride_tricks.sliding_window_view(x, 320)[::80]
    F = np.abs(np.fft.rfft(fr * np.hanning(320), axis=1)) ** 2
    b = lambda a, c: 10 * np.log10(F[:, a // 50:c // 50].sum(1) + 1e-12)
    return b(150, 900), b(900, 3000), b(3000, 8000)


def silencios(wav, minimo=0.04, folga_db=9):
    """Trechos de silêncio de verdade, a cada 5 ms.
    1) Volume total suavizado abaixo do piso da sala + folga_db, por pelo menos 40 ms (acha as pausas).
    2) Cada pausa encolhe nas pontas enquanto qualquer faixa (grave, médio, agudo) ainda tem som colado na fala,
       até 300 ms: consoante surda (f, s, x, ch) e o rabo do "s" final (plural!) pertencem à palavra, não à pausa.
       Sem isso o corte comia o "fi" de "ficaram"."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    n = 80
    q = x[: len(x) // n * n].reshape(-1, n)
    e = np.convolve(10 * np.log10((q ** 2).mean(1) + 1e-10), np.ones(3) / 3, "same")
    sil = e < np.percentile(e, 10) + folga_db
    lo, mi, hi = bandas(wav)
    m = min(len(sil), len(lo))
    som = np.zeros(len(sil), bool)
    som[:m] = (lo[:m] >= np.percentile(lo, 10) + 6) | (mi[:m] >= np.percentile(mi, 10) + 6) | (hi[:m] >= np.percentile(hi, 10) + 6)
    out, k = [], 0
    while k < len(sil):
        if sil[k]:
            j = k
            while j < len(sil) and sil[j]:
                j += 1
            out.append([k, j]); k = j
        else:
            k += 1
    junt = []
    for a, b in out:  # junta silêncios separados por um estalo de até 15 ms
        if junt and a - junt[-1][1] <= 3:
            junt[-1][1] = b
        else:
            junt.append([a, b])
    res = []
    for a, b in junt:
        a0, b0 = a, b
        while a < b and a - a0 < 60 and som[a]:  # som colado no fim da palavra anterior
            a += 1
        while b > a and b0 - b < 60 and som[b - 1]:  # som colado no começo da próxima palavra
            b -= 1
        if (b - a) * 0.005 >= minimo:
            res.append((a * 0.005, b * 0.005))
    return res, len(sil) * 0.005


def plano_no_silencio(palavras, remover=(), manter=(), wav=None, minimo=0.04, folga_db=9):
    """Plano de corte em que TODO corte cai dentro de um silêncio medido no áudio, nunca no tempo do Whisper
    (que erra dezenas de ms e deixava pedaços: "é de", "re", "recosto", ou comia começo de palavra).
    O áudio vira "ilhas" de fala separadas por silêncio. Cada palavra pertence às ilhas que ela cobre.
    - Uma ilha só sai inteira, e só se for feita de palavras a tirar (vício, repetição, --remover).
      Se o vício estiver colado numa palavra que fica (mesma ilha), ele FICA (melhor "na verdade" inteiro
      do que meia palavra) e vai para `mantidas` com o motivo.
    - Ilha sem nenhuma palavra (respiro, estalo) no meio de uma pausa sai junto com a pausa.
    - Pausa longa entre palavras vira respiro (RESPIRO / RESPIRO_FORTE), cortando no meio do silêncio.
    Devolve (segmentos, mantidas)."""
    sils, dur_audio = silencios(wav, minimo, folga_db)
    tirar = [bool(((w.get("vicio") or w.get("repeticao")) and i not in manter) or i in remover) for i, w in enumerate(palavras)]
    ilhas, t = [], 0.0
    for a, b in sils:
        if a > t:
            ilhas.append([t, a])
        t = b
    if t < dur_audio:
        ilhas.append([t, dur_audio])
    sobre = lambda w, il: max(0.0, min(w["fim"], il[1]) - max(w["inicio"], il[0]))
    info = []
    for il in ilhas:
        ws = [(k, sobre(w, il)) for k, w in enumerate(palavras) if sobre(w, il) > 0]
        fica = sum(o for k, o in ws if not tirar[k]); sai = sum(o for k, o in ws if tirar[k])
        L = il[1] - il[0]
        if not ws:
            estado = "ruido" if L < 0.35 else "fica"   # fala sem palavra longa demais: na dúvida, fica
        elif sai > fica and fica < max(0.03, 0.3 * L):
            estado = "sai"
        else:
            estado = "fica"
        info.append({"il": il, "ws": [k for k, o in ws if o >= 0.25 * min(L, palavras[k]["fim"] - palavras[k]["inicio"] + 1e-6)], "estado": estado})
    for n, x in enumerate(info):
        if x["estado"] == "ruido":
            viz = [info[m] for m in (n - 1, n + 1) if 0 <= m < len(info) and info[m]["estado"] == "fica"]
            if any(min(abs(v["il"][0] - x["il"][1]), abs(x["il"][0] - v["il"][1])) <= 0.06 for v in viz):
                x["estado"] = "fica"  # som colado numa palavra (ex.: o "fi" de "ficaram"): nunca sai
    # palavras a tirar que não saíram (coladas numa palavra que fica)
    saiu = set()
    for x in info:
        if x["estado"] == "sai":
            saiu.update(x["ws"])
    vivos = sorted({k for x in info if x["estado"] == "fica" for k in x["ws"]})
    mantidas, visto = [], set()
    for x in info:
        if x["estado"] == "fica":
            ks = [k for k in x["ws"] if tirar[k] and k not in visto]
            if ks:
                visto.update(ks)
                mantidas.append({"palavras": " ".join(palavras[k]["texto"] for k in ks), "indices": ks,
                                 "motivo": "colada em palavra que fica (sem silêncio entre elas): sair deixaria pedaço de palavra"})
    def respiro_apos(k):
        return RESPIRO_FORTE if palavras[k]["texto"].rstrip().endswith((".", "!", "?", ":")) else RESPIRO
    # trechos que ficam = ilhas "fica"; entre duas ilhas que ficam, o silêncio (com o que saiu no meio) vira um respiro
    fic = [x for x in info if x["estado"] == "fica"]
    segs = []
    for n, x in enumerate(fic):
        a, b = x["il"]
        if n == 0:
            ini = max(0.0, a - 0.06)
        else:
            ant = fic[n - 1]
            vao = a - ant["il"][1]  # silêncio total entre as duas ilhas (inclui o que saiu)
            ult = max(ant["ws"]) if ant["ws"] else None
            lim = respiro_apos(ult) if ult is not None else RESPIRO
            contiguo = not any(y["estado"] == "sai" for y in info if ant["il"][1] <= y["il"][0] < a)
            if contiguo and vao <= lim + 0.06:
                segs[-1]["fim"] = b; segs[-1]["palavras"] += x["ws"]; continue
            meia = min(lim, vao) / 2
            s_ant = next(s for s in sils if abs(s[0] - ant["il"][1]) < 1e-6)
            s_dep = next(s for s in sils if abs(s[1] - a) < 1e-6)
            segs[-1]["fim"] = s_ant[0] + min(meia, (s_ant[1] - s_ant[0]) * 0.7)
            segs[-1]["sil"][1] = s_ant
            ini = s_dep[1] - min(meia, (s_dep[1] - s_dep[0]) * 0.7)
        s_dep = next((s for s in sils if abs(s[1] - a) < 1e-6), None)
        segs.append({"ini": ini, "fim": b, "palavras": list(x["ws"]), "sil": [s_dep, None]})
    if segs:
        s_fim = next((s for s in sils if abs(s[0] - segs[-1]["fim"]) < 1e-6), None)
        segs[-1]["fim"] = min(dur_audio, segs[-1]["fim"] + 0.12); segs[-1]["sil"][1] = s_fim
    centro = lambda w: (w["inicio"] + w["fim"]) / 2
    for sg in segs:
        sg["palavras"] = []; sg["sil"] = tuple(sg["sil"])
    for k, w in enumerate(palavras):
        if k in saiu or (tirar[k] and not any(k in m["indices"] for m in mantidas)):
            continue
        c = centro(w)
        alvo = min(segs, key=lambda sg: 0 if sg["ini"] <= c < sg["fim"] else min(abs(c - sg["ini"]), abs(c - sg["fim"])))
        alvo["palavras"].append(k)
    ruido = [x["il"] for x in info if x["estado"] == "ruido"]
    return segs, mantidas


def encaixar(segs, fps=FPS):
    """Põe os cortes no quadro exato: vídeo e áudio de cada trecho ficam com a mesma duração (sem atraso acumulado)."""
    import math
    q = lambda t: round(t * fps) / fps
    def no_quadro(t, sil):
        if sil:  # o quadro mais próximo que ainda cai dentro do silêncio da borda
            cands = [k / fps for k in range(math.ceil(sil[0] * fps), math.floor(sil[1] * fps) + 1)]
            if cands:
                return min(cands, key=lambda c: abs(c - t))
        return q(t)
    for s in segs:
        sa, sb = s.get("sil") or (None, None)
        s["ini"] = no_quadro(s["ini"], sa)
        s["fim"] = max(no_quadro(s["fim"], sb), s["ini"] + 1 / fps)
    for a, b in zip(segs, segs[1:]):
        if b["ini"] < a["fim"]:
            b["ini"] = a["fim"]
    return segs


def remapear(palavras, segs):
    out, t = [], 0.0
    for s in segs:
        for i in s["palavras"]:
            w = palavras[i]
            out.append({**{k: w[k] for k in ("texto", "inicio", "fim")}, "inicio": round(t + w["inicio"] - s["ini"], 3), "fim": round(t + w["fim"] - s["ini"], 3), "orig": i})
        t += s["fim"] - s["ini"]
    return out, t


def checar(palavras, segs):
    """Cada borda de trecho tem de cair num silêncio medido (senão corta fala) e nenhum trecho pode sobrepor o seguinte."""
    problemas = []
    for k, s in enumerate(segs):
        sa, sb = s.get("sil") or (None, None)
        if k > 0 and not (sa and sa[0] - 0.002 <= s["ini"] <= sa[1] + 0.002):
            problemas.append(f"começo do trecho {k} fora do silêncio ({s['ini']:.3f})")
        if k < len(segs) - 1 and not (sb and sb[0] - 0.002 <= s["fim"] <= sb[1] + 0.002):
            problemas.append(f"fim do trecho {k} fora do silêncio ({s['fim']:.3f})")
    for a, b in zip(segs, segs[1:]):
        if b["ini"] < a["fim"]:
            problemas.append(f"segmentos sobrepostos em {a['fim']:.2f}")
    return problemas


def renderizar(src, segs, dst):
    """Cada trecho vira um arquivo (pouca memória, serve para vídeo longo) e depois tudo é emendado sem recodificar."""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="cortes_", dir=os.path.dirname(os.path.abspath(dst)))
    lista = []
    for k, s in enumerate(segs):
        # Tudo no quadro exato (revisor, 27/11): o tempo arredondado em 3 casas (77,667 > 77,6667) pulava o 1º quadro
        # e o áudio de cada trecho saía uns ms mais curto que o vídeo, adiantando a voz a cada emenda (46 ms no fim).
        k0 = round(s["ini"] * FPS); n = max(1, round((s["fim"] - s["ini"]) * FPS))
        t0, d = k0 / FPS, n / FPS
        out = os.path.join(tmp, f"{k:03d}.mkv")
        wav = os.path.join(os.path.dirname(os.path.abspath(src)), "proxy_audio.wav")
        entradas = ["-ss", f"{max(0, t0 - 0.25 / FPS):.5f}", "-i", src]   # meio quadro antes: pega o quadro k0 certo
        mapa = []
        if os.path.exists(wav):  # voz sem perda, cortada no mesmo ponto do vídeo
            entradas += ["-ss", f"{t0:.5f}", "-i", wav]
            mapa = ["-map", "0:v", "-map", "1:a"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", *entradas, *mapa, "-t", f"{d:.5f}",
                        "-af", f"atrim=end={d:.5f},afade=t=in:d=0.015,afade=t=out:st={max(0, d - 0.015):.5f}:d=0.015,apad=whole_dur={d:.5f}",
                        "-frames:v", str(n), "-c:v", "libx264", "-preset", "medium", "-crf", str(CRF_INTERMEDIARIO), "-pix_fmt", "yuv420p", "-r", str(FPS),
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                        "-c:a", "pcm_s24le", "-ar", "48000", out], check=True)
        lista.append(f"file '{out}'")
    lp = os.path.join(tmp, "lista.txt")
    open(lp, "w").write("\n".join(lista) + "\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lp, "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
                    "-movflags", "+faststart", dst], check=True)
    # Voz cortada sem perda, para o som (o AAC do mp4 é só para conferência)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lp, "-vn", "-c:a", "pcm_s24le",
                    os.path.join(os.path.dirname(os.path.abspath(dst)), "base_audio.wav")], check=True)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def renderizar_filtro(src, segs, dst):
    fc, n = [], len(segs)
    for k, s in enumerate(segs):
        d = s["fim"] - s["ini"]
        fc.append(f"[0:v]trim=start={s['ini']:.3f}:end={s['fim']:.3f},setpts=PTS-STARTPTS[v{k}]")
        fc.append(f"[0:a]atrim=start={s['ini']:.3f}:end={s['fim']:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.008,afade=t=out:st={max(0, d - 0.008):.3f}:d=0.008[a{k}]")
    fc.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "aac", "-b:a", "192k", dst], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta"); ap.add_argument("--entrada", default="base_cor.mp4"); ap.add_argument("--saida", default="base.mp4")
    ap.add_argument("--remover", default=""); ap.add_argument("--manter", default="")
    ap.add_argument("--folga-db", type=float, default=9, help="pausa = piso da sala + isto (depois encolhe onde ainda há consoante colada)")
    ap.add_argument("--min-silencio", type=float, default=0.04)
    a = ap.parse_args()
    an = json.load(open(os.path.join(a.pasta, "01_analise.json")))
    pal = an.get("palavras")
    if not pal:
        raise SystemExit("Sem transcrição na análise: o montador não corta no escuro.")
    rem = {int(x) for x in a.remover.split(",") if x.strip()}
    man = {int(x) for x in a.manter.split(",") if x.strip()}
    wav = os.path.join(a.pasta, "proxy_audio.wav")
    mantidas = []
    if os.path.exists(wav):
        segs, mantidas = plano_no_silencio(pal, rem, man, wav, a.min_silencio, a.folga_db)
    else:
        segs = plano_de_corte(pal, rem, man)
    segs = encaixar(segs)
    novas, dur = remapear(pal, segs)
    colados = {k for m in mantidas for k in m["indices"]}
    for w in novas:  # vício que ficou no áudio (colado) não entra na legenda
        if w["orig"] in colados:
            w["vicio"] = True
    probs = checar(pal, segs)
    removidas = [pal[i]["texto"] for i in range(len(pal)) if not any(i in s["palavras"] for s in segs)]
    res = {"segmentos": [{"ini": round(s["ini"], 3), "fim": round(s["fim"], 3)} for s in segs], "duracao_final": round(dur, 3),
           "duracao_original": round(pal[-1]["fim"] - pal[0]["inicio"], 3), "removidas": removidas, "mantidas": mantidas, "palavras": novas, "problemas": probs}
    json.dump(res, open(os.path.join(a.pasta, "03_cortes.json"), "w"), ensure_ascii=False, indent=1)
    renderizar(os.path.join(a.pasta, a.entrada), segs, os.path.join(a.pasta, a.saida))
    print(json.dumps({k: res[k] for k in ("duracao_original", "duracao_final", "removidas", "mantidas", "problemas")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
