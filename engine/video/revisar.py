"""Revisão (portões das etapas e revisão final). Monta a folha de revisão de um vídeo: um quadro no meio de cada
elemento, nas entradas e saídas, e na troca das legendas, lado a lado com quadros da referência (opcional).
Junta as checagens automáticas (relatório do timeline, cortes, som) num resumo para o revisor dar a nota.
Uso: python revisar.py PASTA [--video previa.mp4] [--referencia pasta_ou_folha.jpg]"""
import argparse, json, os, subprocess
import numpy as np
import cv2


def quadro(video, t, w=270):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", video, "-frames:v", "1", "-vf", f"scale={w}:-1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    h = int(round(w * 16 / 9))
    if len(r.stdout) < w * h * 3:
        return np.zeros((h, w, 3), np.uint8)
    return np.frombuffer(r.stdout[:w * h * 3], np.uint8).reshape(h, w, 3).copy()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("pasta"); ap.add_argument("--video", default="previa.mp4"); ap.add_argument("--referencia")
    a = ap.parse_args(); P = a.pasta
    tl = json.load(open(os.path.join(P, "timeline.json")))
    momentos = []
    for el in tl["elementos"]:
        momentos.append((el["ini"] + 0.30, f"{el['id']} entra"))
        momentos.append(((el["ini"] + el["fim"]) / 2, f"{el['id']} meio"))
    for w in tl["legenda"][::2]:
        momentos.append((w["ini"] + 0.06, f"leg: {w['texto'][:14]}"))
    momentos = sorted({round(t, 2): l for t, l in momentos}.items())
    vid = os.path.join(P, a.video)
    cards = []
    for t, l in momentos:
        q = quadro(vid, t)
        cv2.rectangle(q, (0, 0), (q.shape[1], 22), (0, 0, 0), -1)
        cv2.putText(q, f"{t:.2f}s {l}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
        cards.append(q)
    cols = 8
    rows = int(np.ceil(len(cards) / cols))
    h, w = cards[0].shape[:2]
    folha = np.zeros((rows * h, cols * w, 3), np.uint8)
    for k, c in enumerate(cards):
        r, cc = divmod(k, cols)
        folha[r * h:(r + 1) * h, cc * w:(cc + 1) * w] = c
    if a.referencia and os.path.exists(a.referencia):
        ref = cv2.imread(a.referencia)
        ref = cv2.resize(ref, (folha.shape[1], int(ref.shape[0] * folha.shape[1] / ref.shape[1])))
        folha = np.vstack([folha, np.full((12, folha.shape[1], 3), 40, np.uint8), ref])
    saida = os.path.join(P, "revisao_folha.jpg")
    cv2.imwrite(saida, folha, [cv2.IMWRITE_JPEG_QUALITY, 86])
    resumo = {"folha": saida, "momentos": len(momentos)}
    for nome in ("03_cortes.json", "05_relatorio.json", "06_som.json"):
        p = os.path.join(P, nome)
        if os.path.exists(p):
            j = json.load(open(p))
            resumo[nome] = {k: j[k] for k in ("problemas", "lufs", "pico_dbfs", "removidas", "duracao_final") if k in j}
    json.dump(resumo, open(os.path.join(P, "revisao_checagens.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(resumo, ensure_ascii=False))


if __name__ == "__main__":
    main()
