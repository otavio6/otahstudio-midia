"""Etapa 3 · Corte (montador). Corta pela transcrição, palavra por palavra: vícios, repetições e pausas longas,
deixando o respiro certo. Nenhuma palavra é cortada pela metade (margem antes e depois de cada palavra).
Uso: python cortar.py PASTA [--entrada base_cor.mp4] [--saida base.mp4] [--remover i,j,k] [--manter i,j]
Lê 01_analise.json. Gera 03_cortes.json (segmentos, palavras com o tempo novo e checagens) e o vídeo cortado."""
import argparse, json, os, subprocess

RESPIRO = 0.20        # pausa máxima mantida entre palavras da mesma ideia
RESPIRO_FORTE = 0.38  # pausa mantida antes de frase nova (respiro de efeito)
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
        segs.append({"ini": max(0.0, ini), "fim": fim, "palavras": [i]})
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
    problemas = []
    for s in segs:
        for i in s["palavras"]:
            w = palavras[i]
            if w["inicio"] < s["ini"] - 1e-3 or w["fim"] > s["fim"] + 1e-3:
                problemas.append(f"palavra cortada: '{w['texto']}' ({w['inicio']:.2f}–{w['fim']:.2f})")
    for a, b in zip(segs, segs[1:]):
        if b["ini"] < a["fim"]:
            problemas.append(f"segmentos sobrepostos em {a['fim']:.2f}")
    return problemas


def renderizar(src, segs, dst):
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
    a = ap.parse_args()
    an = json.load(open(os.path.join(a.pasta, "01_analise.json")))
    pal = an.get("palavras")
    if not pal:
        raise SystemExit("Sem transcrição na análise: o montador não corta no escuro.")
    rem = {int(x) for x in a.remover.split(",") if x.strip()}
    man = {int(x) for x in a.manter.split(",") if x.strip()}
    segs = plano_de_corte(pal, rem, man)
    novas, dur = remapear(pal, segs)
    probs = checar(pal, segs)
    removidas = [pal[i]["texto"] for i in range(len(pal)) if not any(i in s["palavras"] for s in segs)]
    res = {"segmentos": [{"ini": round(s["ini"], 3), "fim": round(s["fim"], 3)} for s in segs], "duracao_final": round(dur, 3),
           "duracao_original": round(pal[-1]["fim"] - pal[0]["inicio"], 3), "removidas": removidas, "palavras": novas, "problemas": probs}
    json.dump(res, open(os.path.join(a.pasta, "03_cortes.json"), "w"), ensure_ascii=False, indent=1)
    renderizar(os.path.join(a.pasta, a.entrada), segs, os.path.join(a.pasta, a.saida))
    print(json.dumps({k: res[k] for k in ("duracao_original", "duracao_final", "removidas", "problemas")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
