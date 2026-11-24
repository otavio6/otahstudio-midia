"""Revisão do áudio (etapa obrigatória depois do corte e antes da entrega).
O áudio cortado é transcrito de novo (Whisper no VPS) e comparado palavra por palavra com a fala que deveria ficar:
palavra faltando, sobrando ou trocada (inclusive plural x singular: "produto" x "produtos") vira problema com o tempo.
Também mede cada ponto de corte: energia alta na emenda (palavra comida) e "s" repetido (chiado dos dois lados do corte).

Uso:
  python conferir_audio.py preparar PASTA [--audio base_audio.wav]   → PASTA/conferir.mp3 e PASTA/esperado.json
     (suba conferir.mp3 para o repositório privado e rode a ferramenta `transcrever` nele; salve o JSON em PASTA/transcricao_corte.json)
  python conferir_audio.py comparar PASTA                              → PASTA/07_audio.json e a lista de problemas
"""
import argparse, difflib, json, os, re, subprocess, unicodedata
import numpy as np

SR = 16000


# Grafias que o Whisper troca sem a fala ter mudado (não é defeito de corte): viram aviso, não problema.
VARIANTES = [("futurebrand", "future brand"), ("high-ticket", "high -tech"), ("high-ticket", "high-tech"), ("posts", "postos"),
             ("do", "de"), ("dois", "2"), ("superfaturado", "super faturado"), ("abaixar", "rebaixar")]
NUM = {"dois": "2", "três": "3", "quatro": "4", "cinco": "5", "mil": "mil"}


def norm(p):
    p = unicodedata.normalize("NFKC", p.lower()).strip()
    p = re.sub(r"[^\w%\-]", "", p)
    return {"pro": "para o", "tá": "está", "pra": "para", "tô": "estou"}.get(p, NUM.get(p, p))


def variante(esperado, ouvido):
    e, o = esperado.replace(" ", ""), ouvido.replace(" ", "")
    if e == o:
        return True
    return any({e, o} == {a.replace(" ", ""), b.replace(" ", "")} for a, b in VARIANTES)


def ler_audio(path, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def energia(x, sr=SR, passo=0.005):
    """Energia total e energia de chiado (4–8 kHz, onde mora o 's') a cada 5 ms, em dB."""
    n = int(sr * passo)
    q = x[: len(x) // n * n].reshape(-1, n)
    tot = 20 * np.log10(np.sqrt((q ** 2).mean(1)) + 1e-7)
    d = np.diff(x, prepend=0)  # derivada realça agudos (chiado)
    qd = d[: len(d) // n * n].reshape(-1, n)
    hf = 20 * np.log10(np.sqrt((qd ** 2).mean(1)) + 1e-7)
    return tot, hf, passo


def preparar(pasta, audio):
    src = os.path.join(pasta, audio)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", "-b:a", "96k", os.path.join(pasta, "conferir.mp3")], check=True)
    cortes = json.load(open(os.path.join(pasta, "03_cortes.json")))
    esperado = {"palavras": [w["texto"] for w in cortes["palavras"]],
                "emendas": list(np.cumsum([s["fim"] - s["ini"] for s in cortes["segmentos"]])[:-1].round(3))}
    json.dump(esperado, open(os.path.join(pasta, "esperado.json"), "w"), ensure_ascii=False)
    print("ok", os.path.join(pasta, "conferir.mp3"), len(esperado["palavras"]), "palavras,", len(esperado["emendas"]), "emendas")


def comparar(pasta, audio="base_audio.wav"):
    esp = json.load(open(os.path.join(pasta, "esperado.json")))
    tr = json.load(open(os.path.join(pasta, "transcricao_corte.json")))
    ouvidas = tr["palavras"]
    a = [norm(p) for p in esp["palavras"]]
    b = [norm(w["texto"]) for w in ouvidas]
    # quebra "para o" em duas para alinhar com o Whisper
    a = " ".join(a).split(); b = " ".join(b).split()
    problemas, avisos = [], []
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    tempos_b = []
    for w in ouvidas:
        for _ in norm(w["texto"]).split():
            tempos_b.append(w["inicio"])
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        t = tempos_b[min(j1, len(tempos_b) - 1)] if tempos_b else 0
        esperado = " ".join(a[i1:i2]); ouvido = " ".join(b[j1:j2])
        plural = (op == "replace" and i2 - i1 == j2 - j1 == 1 and (a[i1].rstrip("s") == b[j1].rstrip("s")))
        item = {"tempo": round(t, 2), "tipo": "plural/singular" if plural else {"replace": "trocada", "delete": "faltando", "insert": "sobrando"}[op],
                "esperado": esperado, "ouvido": ouvido}
        if op == "replace" and not plural and variante(esperado, ouvido):
            avisos.append({**item, "tipo": "grafia do Whisper (fala igual)"})
        else:
            problemas.append(item)
    # emendas: palavra comida (energia alta no ponto do corte) e "s" repetido (chiado dos dois lados)
    x = ler_audio(os.path.join(pasta, audio))
    tot, hf, passo = energia(x)
    piso = np.percentile(tot, 10)
    for e in esp["emendas"]:
        k = int(e / passo)
        if k <= 4 or k >= len(tot) - 4:
            continue
        no_corte = tot[k - 1:k + 2].max()
        antes = hf[max(0, k - 16):k].mean(); depois = hf[k:k + 16].mean()
        chiado = (antes > piso + 30) and (depois > piso + 30) and hf[k - 2:k + 2].max() > np.percentile(hf, 85)
        if no_corte > piso + 32:
            problemas.append({"tempo": round(float(e), 2), "tipo": "emenda com voz (palavra pode ter sido comida)", "nivel_db": round(float(no_corte - piso), 1)})
        if chiado:
            problemas.append({"tempo": round(float(e), 2), "tipo": "chiado dos dois lados da emenda ('s' repetido)"})
    problemas.sort(key=lambda p: p["tempo"])
    rel = {"palavras_esperadas": len(a), "palavras_ouvidas": len(b), "acerto": round(sm.ratio(), 4), "problemas": problemas, "avisos": avisos,
           "como_ler": "Cada problema é ouvido no trecho indicado antes de decidir. Palavra 'sobrando' que é vício colado (ver 03_cortes.json → mantidas) é esperada. "
                       "'trocada' fora de emenda costuma ser o Whisper ouvindo diferente nas duas passadas: confirme de ouvido; dentro de emenda é defeito de corte."}
    json.dump(rel, open(os.path.join(pasta, "07_audio.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rel, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("modo", choices=["preparar", "comparar"]); ap.add_argument("pasta"); ap.add_argument("--audio", default="base_audio.wav")
    a = ap.parse_args()
    preparar(a.pasta, a.audio) if a.modo == "preparar" else comparar(a.pasta, a.audio)
