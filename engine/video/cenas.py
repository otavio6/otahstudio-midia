"""Prepara as cenas em motion para o montar.py, amarradas à fala.
Lê o roteiro de cenas (cada cena começa numa palavra) e o 03_cortes.json, calcula onde cada cena começa e termina
e injeta em cada HTML os tempos de todas as palavras daquela cena (T["palavra"] = segundos desde o início da cena).
Assim, se o corte mudar, as animações continuam no tempo da fala.

Uso: python cenas.py PASTA roteiro_cenas.json
roteiro_cenas.json:
{"cenas": [
  {"html": "cenas_t/1_gancho.html", "modo": "pessoa", "transparente": true},
  {"html": "cenas_t/2_estudo.html", "modo": "canto", "comeca": "Não", "transicao": "encolhe", "pessoa": {...}, "legenda_y": 905},
  ...],
 "fim": {"html": "cenas_t/8_fim.html", "dur": 1.8},
 "zoom": [{"de_palavra": "inflado.", "ate_palavra": "inflado.", "escala": 1.05}]}
Gera cenas/*.html e montagem.json na PASTA."""
import json, os, re, sys

MOTION = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion")


def main(pasta, roteiro):
    r = json.load(open(os.path.join(pasta, roteiro)))
    pal = json.load(open(os.path.join(pasta, "03_cortes.json")))["palavras"]
    fim_fala = pal[-1]["fim"]
    cursor = 0.0
    inicios = []
    for c in r["cenas"]:
        if "comeca" not in c:
            inicios.append(0.0); continue
        alvo = c["comeca"]
        w = next((w for w in pal if w["inicio"] >= cursor - 1e-3 and w["texto"] == alvo), None)
        if w is None:
            raise SystemExit(f"Palavra de início não encontrada: {alvo!r} depois de {cursor:.2f}s")
        de = max(0.0, w["inicio"] - 0.04)
        inicios.append(de); cursor = w["inicio"] + 0.01
    fim_video = fim_fala + 0.45
    os.makedirs(os.path.join(pasta, "cenas"), exist_ok=True)
    cenas = []
    for k, c in enumerate(r["cenas"]):
        de = inicios[k]; ate = inicios[k + 1] if k + 1 < len(inicios) else fim_video
        tempos = {}
        for w in pal:
            if de - 0.05 <= w["inicio"] < ate + 0.3 and w["texto"] not in tempos:
                tempos[w["texto"]] = round(w["inicio"] - de, 3)
        cenas.append({**{x: y for x, y in c.items() if x not in ("comeca", "html")}, "de": round(de, 3), "ate": round(ate, 3),
                      "html": escreve(pasta, c["html"], tempos)})
    if r.get("fim"):
        f = r["fim"]
        cenas.append({"modo": f.get("modo", "cheia"), "de": round(fim_video, 3), "ate": round(fim_video + f["dur"], 3), "legenda": False,
                      "transicao": f.get("transicao", "desliza"), "html": escreve(pasta, f["html"], {})})
    zoom = []
    for z in r.get("zoom", []):
        a = next(w for w in pal if w["texto"] == z["de_palavra"])["inicio"]
        b = next(w for w in pal if w["texto"] == z["ate_palavra"] and w["inicio"] >= a)["fim"]
        zoom.append({"de": round(a, 3), "ate": round(b, 3), "escala": z.get("escala", 1.06)})
    plano = {"cenas": cenas, "zoom": zoom, "duracao": round(cenas[-1]["ate"], 3)}
    json.dump(plano, open(os.path.join(pasta, "montagem.json"), "w"), ensure_ascii=False, indent=1)
    for c in cenas:
        print(f"{c['de']:6.2f}–{c['ate']:6.2f}  {c.get('modo'):9s} {c['html']}")


def escreve(pasta, html, tempos):
    s = open(os.path.join(pasta, html)).read()
    s = s.replace("__M__", MOTION).replace("__TEMPOS__", json.dumps(tempos, ensure_ascii=False))
    destino = os.path.join("cenas", os.path.basename(html))
    open(os.path.join(pasta, destino), "w").write(s)
    return destino


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
