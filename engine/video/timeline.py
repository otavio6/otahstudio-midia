"""Etapa 5 (base) · Do plano do diretor para a linha do tempo resolvida.
O diretor escreve 04_plano.json (o quê e quando, ligado às palavras). Aqui se decide ONDE (área livre do mapa de
ocupação, na grade e na zona segura, durante toda a vida do elemento) e QUAL COR (medindo o fundo).
Sai timeline.json (para o Remotion e para a prévia local), eventos de som e 05_relatorio.json com as checagens.
Uso: python timeline.py PASTA"""
import json, os, re, unicodedata
import numpy as np
import cv2
from common import W, H, FPS, SAFE, MARCAS, texto, cor_pelo_fundo, frames, rgb, razao_contraste, luminancia
from ocupacao import ocupado, achar_lugar, sobreposicao, fora_da_zona_segura

ESTILOS = {
    "titulo": ("InterDisplay-Black.otf", 200, -0.02),
    "numero": ("InterDisplay-Black.otf", 260, -0.03),
    "rotulo": ("InterDisplay-Black.otf", 96, 0.0),
    "frase": ("InterDisplay-SemiBold.otf", 72, 0.0),
    "etiqueta": ("Inter-Medium.otf", 26, 0.16),
}
LEG_TAM, LEG_TAM_DESTAQUE = 84, 104


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def hexcor(c):
    c = (np.asarray(c) * 255).round().astype(int)
    return "#%02X%02X%02X" % tuple(c)


class Ocupacao:
    def __init__(self, path):
        z = np.load(path)
        self.t, self.face, self.matte = z["t"], z["face"], z["matte"]

    def idx(self, t):
        return int(np.clip(np.searchsorted(self.t, t), 0, len(self.t) - 1))

    def rosto(self, t):
        f = self.face[self.idx(t)]
        if np.isnan(f[0]):
            ok = ~np.isnan(self.face[:, 0])
            f = np.nanmedian(self.face[ok], 0) if ok.any() else np.array([W / 2, H * 0.45, 360, 480], np.float32)
        return f

    def mascara(self, t):
        a = cv2.resize(self.matte[self.idx(t)], (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
        return ocupado(a, self.rosto(t))

    def amostras(self, ini, fim, passo=0.2):
        ts = np.arange(ini, max(ini + 0.01, fim), passo)
        return [self.mascara(float(t)) for t in ts]


def quadros(path, tempos):
    """Pega os quadros do vídeo de base nos tempos pedidos (para medir o fundo)."""
    alvo = sorted({int(round(t * FPS)) for t in tempos})
    out = {}
    for i, f in frames(path):
        if i in alvo:
            out[i] = f
        if i > alvo[-1]:
            break
    return {k / FPS: v for k, v in out.items()}


def main(pasta):
    plano = json.load(open(os.path.join(pasta, "04_plano.json")))
    cortes = json.load(open(os.path.join(pasta, "03_cortes.json")))
    pal = cortes["palavras"]
    dur = cortes["duracao_final"]
    occ = Ocupacao(os.path.join(pasta, "ocupacao_final.npz"))
    marca = MARCAS[plano.get("marca", "otavio")]
    INK = rgb(marca["ink"])

    # --- tempos: gatilhos ligados às palavras, em ordem ---
    cursor = 0

    def tempo_da_palavra(p, apos=0.0):
        alvo = norm(p)
        for w in pal:
            if w["inicio"] >= apos - 1e-3 and norm(w["texto"]) == alvo:
                return w
        raise SystemExit(f"Palavra-gatilho não encontrada depois de {apos:.2f}s: '{p}'")

    els, eventos, relatorio = [], [], []
    tempos_fundo = []
    batidas = plano.get("batidas", [])
    for b in batidas:
        if "t" in b:
            ini = float(b["t"])
        else:
            ini = tempo_da_palavra(b.get("gatilho") or b["de"], b.get("apos", 0.0))["inicio"]
        if "ate" in b:
            fim = tempo_da_palavra(b["ate"], ini)["fim"] + b.get("folga", 0.15)
        else:
            fim = ini + float(b.get("dur", 1.2))
        b["_ini"], b["_fim"] = round(ini - b.get("antecipa", 0.04), 3), round(min(fim, dur), 3)
        if b["tipo"] == "fundo":
            tempos_fundo.append((b["_ini"], b["_fim"]))

    def pedacos(ini, fim):
        cortes = sorted({x for a_, b_ in tempos_fundo for x in (a_, b_) if ini + 0.05 < x < fim - 0.05})
        bordas = [ini] + cortes + [fim]
        return list(zip(bordas, bordas[1:]))

    medir = {round(t, 2) for b in batidas for a_, b_ in pedacos(b["_ini"], b["_fim"]) for t in (a_ + 0.05, (a_ + b_) / 2, b_ - 0.05)}
    medir |= {round(w["inicio"] + 0.03, 2) for w in pal}
    qs = quadros(os.path.join(pasta, "base.mp4"), medir)

    def quadro(t):
        k = min(qs, key=lambda x: abs(x - t))
        f = qs[k]
        if any(a <= t < b for a, b in tempos_fundo):  # atrás da pessoa o fundo é o da marca
            al = cv2.resize(occ.matte[occ.idx(t)], (W, H)).astype(np.float32)[..., None] / 255
            f = f * al + INK * (1 - al)
        return f

    for k, b in enumerate(batidas):
        ini, fim = b["_ini"], b["_fim"]
        el = {"id": b.get("id", f"e{k}"), "ini": ini, "fim": fim, "camada": b.get("camada", "frente"),
              "entrada": b.get("entrada", "sobe"), "saida": b.get("saida", "fade")}
        nota = {"id": el["id"], "tipo": b["tipo"]}
        if b["tipo"] == "fundo":
            el.update(tipo="fundo", camada="atras", cor=hexcor(INK), grade=b.get("grade", True), entrada="fade", saida="fade", dur_entrada=0.18, dur_saida=0.18)
            eventos.append({"t": ini, "som": "whoosh"})
        elif b["tipo"] == "contorno":
            fim_fundo = min((b_ for a_, b_ in tempos_fundo if a_ <= ini + 0.05 < b_), default=fim)
            el["fim"] = round(min(fim, fim_fundo - 0.12), 3)
            el.update(tipo="contorno", camada="frente", src="job/contorno.webm", entrada="fade", saida="fade", dur_entrada=0.18, dur_saida=0.12)
        elif b["tipo"] == "zoom":
            f0 = occ.rosto(ini)
            els.append(None)  # zoom não é camada
            plano.setdefault("_zoom", []).append({"ini": ini, "fim": fim, "de": 1.0, "ate": float(b.get("escala", 1.08)), "cx": float(f0[0]), "cy": float(f0[1])})
            continue
        elif b["tipo"] == "mira":
            ks = []
            for t in np.arange(ini, fim + 0.1, 0.1):
                fx, fy, fw, fh = occ.rosto(float(t))
                ks.append({"t": round(float(t), 2), "x": round(float(fx), 1), "y": round(float(fy), 1), "w": round(float(fw * 1.25), 1), "h": round(float(fh * 1.35), 1)})
            fx, fy, fw, fh = occ.rosto((ini + fim) / 2)
            caixa = (fx - fw * 0.8, fy - fh * 0.85, fx + fw * 0.8, fy + fh * 0.85)
            # a mira fica no fundo em volta do rosto: mede o anel externo
            cor, r, _ = cor_pelo_fundo(quadro((ini + fim) / 2), caixa, destaque=True, grande=True)
            el.update(tipo="mira", chaves=ks, cor=hexcor(cor), espessura=6, rotulo=b.get("rotulo"), entrada="escala", saida="fade", contorno_escuro=r < 3)
            nota.update(contraste=round(r, 2), contorno_escuro=r < 3)
            eventos.append({"t": ini, "som": "click"})
        elif b["tipo"] in ("texto", "imagem"):
            if b["tipo"] == "texto":
                fonte, tam, track = ESTILOS[b.get("estilo", "rotulo")]
                tam = int(b.get("tamanho", tam))
                for tentativa in range(3):
                    m = texto(b["texto"], fonte, tam, track)
                    w, h = m.shape[1] + 24, m.shape[0] + 16
                    lugar = achar_lugar(occ.amostras(ini, fim), w, h, tuple(b.get("lugar", ["topo", "esquerda", "direita"])),
                                        max_sobrepor=0.08 if el["camada"] == "atras" else 0.0)
                    if lugar:
                        break
                    tam = int(tam * 0.85)
            else:
                w, h = int(b.get("w", 600)), int(b.get("h", 420))
                lugar = achar_lugar(occ.amostras(ini, fim), w, h, tuple(b.get("lugar", ["topo"])), 0.0)
            if not lugar:
                relatorio.append({**nota, "erro": "sem lugar livre durante a vida do elemento: mude o tempo, o tamanho ou corte o elemento"})
                continue
            cx, cy = lugar
            caixa = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if b["tipo"] == "texto":
                partes = pedacos(ini, fim)
                # pedaço curto (< 0,4 s) não vira troca de cor: o elemento termina na borda (sem pisca-pisca)
                if len(partes) > 1 and partes[-1][1] - partes[-1][0] < 0.4:
                    partes = partes[:-1]
                if len(partes) > 1 and partes[0][1] - partes[0][0] < 0.4:
                    partes = partes[1:]
                cont = []
                for n_, (a_, b_) in enumerate(partes):
                    piores = [cor_pelo_fundo(quadro(t), caixa, destaque=b.get("destaque", False), grande=tam >= 40) for t in (a_ + 0.05, (a_ + b_) / 2, b_ - 0.05)]
                    cor, r, sombra = min(piores, key=lambda x: x[1])
                    escuro = bool(sombra or r < 3)
                    pe = dict(el, id=f"{el['id']}" + (f"-{n_ + 1}" if len(partes) > 1 else ""), ini=round(a_, 3), fim=round(b_, 3),
                              tipo="texto", texto=b["texto"], fonte=fonte, tamanho=tam, tracking=track, cor=hexcor(cor), sombra=not escuro,
                              contorno_escuro=escuro, x=round(cx, 1), y=round(cy, 1))
                    if n_ > 0:
                        pe.update(entrada="nenhuma")
                    if n_ < len(partes) - 1:
                        pe.update(saida="nenhuma")
                    els.append(pe); cont.append(round(r, 2))
                nota.update(texto=b["texto"], tamanho=tam, contraste=min(cont), pedacos=len(partes))
                eventos.append({"t": ini, "som": "whoosh" if b.get("estilo") in ("titulo", "numero") else "pop"})
            else:
                el.update(tipo="imagem", src="job/" + b["src"], x=round(cx, 1), y=round(cy, 1), w=w, h=h, raio=b.get("raio", 24), entrada=b.get("entrada", "escala"))
                eventos.append({"t": ini, "som": "pop"})
            ocup = max(sobreposicao(caixa, m_) for m_ in occ.amostras(ini, fim))
            nota.update(caixa=[round(v) for v in caixa], sobreposicao_corpo=round(ocup, 3), zona_segura=not fora_da_zona_segura(caixa))
            if b.get("saida") in ("afasta-esq", "afasta-dir"):
                eventos.append({"t": fim - 0.2, "som": "whoosh"})
        if b.get("impacto"):
            eventos.append({"t": ini, "som": "impacto"})
        if b["tipo"] != "texto":
            els.append(el)
        relatorio.append(nota)

    # --- legenda palavra a palavra, embaixo do queixo, cor pelo fundo ---
    dest = {norm(x) for x in plano.get("destaques", [])}
    grupos, i = [], 0
    while i < len(pal):
        w = dict(pal[i]); txt = [w["texto"]]
        while (w["fim"] - w["inicio"]) < 0.14 and i + 1 < len(pal) and pal[i + 1]["inicio"] - w["fim"] < 0.25:
            i += 1; txt.append(pal[i]["texto"]); w["fim"] = pal[i]["fim"]
        grupos.append({"texto": " ".join(txt), "ini": w["inicio"], "fim": w["fim"]})
        i += 1
    legenda, leg_rel = [], []
    for k, g in enumerate(grupos):
        fim = min(grupos[k + 1]["ini"] if k + 1 < len(grupos) else g["fim"] + 0.5, g["fim"] + 0.9)
        limpo = re.sub(r"[,.;:!?]", "", g["texto"]).upper()
        destaque = any(norm(p) in dest for p in limpo.split())
        tam = LEG_TAM_DESTAQUE if destaque else LEG_TAM
        fx, fy, fw, fh = occ.rosto(g["ini"])
        y = float(np.clip(fy + fh * 0.62 + 150, H * 0.70, H - SAFE["bottom"] - 90))
        cx = (SAFE["left"] + W - SAFE["right"]) / 2
        larg_max = (W - SAFE["left"] - SAFE["right"]) * 0.92
        m = texto(limpo, MARCAS["otavio"]["fonte"], tam, 0.01)
        if m.shape[1] > larg_max:
            tam = int(tam * larg_max / m.shape[1]); m = texto(limpo, MARCAS["otavio"]["fonte"], tam, 0.01)
        caixa = (cx - m.shape[1] / 2 - 10, y - m.shape[0] / 2 - 8, cx + m.shape[1] / 2 + 10, y + m.shape[0] / 2 + 8)
        cor, r, sombra = cor_pelo_fundo(quadro(g["ini"] + 0.03), caixa, destaque=destaque, grande=True)
        escuro = bool(sombra or r < 3)
        if escuro and luminancia(cor) < 0.3:  # com contorno escuro a letra precisa ser clara
            cor = rgb(marca["destaque"]) if destaque else rgb(marca["branco"])
        legenda.append({"texto": limpo, "ini": round(g["ini"], 3), "fim": round(fim, 3), "destaque": destaque, "cor": hexcor(cor),
                        "x": round(cx, 1), "y": round(y, 1), "tamanho": tam, "sombra": not escuro, "contorno_escuro": escuro})
        boca = (fx - fw * 0.4, fy + fh * 0.15, fx + fw * 0.4, fy + fh * 0.62)
        cobre_boca = not (caixa[1] > boca[3] or caixa[3] < boca[1])
        leg_rel.append({"texto": limpo, "contraste": round(r, 2), "contorno_escuro": escuro, "cobre_boca": cobre_boca, "zona_segura": not fora_da_zona_segura(caixa)})

    tl = {"duracao": dur, "base": "job/base.mp4", "pessoa": "job/pessoa.webm", "audio": "job/mix.wav",
          "elementos": [e for e in els if e], "legenda": legenda, "zoom": plano.get("_zoom", []), "fonte_legenda": MARCAS["otavio"]["fonte"]}
    json.dump(tl, open(os.path.join(pasta, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(eventos, open(os.path.join(pasta, "eventos_som.json"), "w"), ensure_ascii=False, indent=1)
    problemas = [r for r in relatorio if r.get("erro") or r.get("sobreposicao_corpo", 0) > (0.08) or ((r.get("contraste") or 9) < 3 and not r.get("contorno_escuro")) or r.get("zona_segura") is False]
    problemas += [{"legenda": x["texto"], **x} for x in leg_rel if x["cobre_boca"] or (x["contraste"] < 3 and not x["contorno_escuro"]) or not x["zona_segura"]]
    rel = {"elementos": relatorio, "legenda": leg_rel, "problemas": problemas}
    json.dump(rel, open(os.path.join(pasta, "05_relatorio.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"elementos": len(tl["elementos"]), "legendas": len(legenda), "problemas": problemas}, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
