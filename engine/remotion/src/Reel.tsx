import React, { useEffect, useState } from "react";
import {
  AbsoluteFill, Audio, Easing, Img, OffthreadVideo, continueRender, delayRender, interpolate, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import type { Chave, Elemento, Palavra, ReelProps, Zoom } from "./tipos";

// Uma curva de movimento para o vídeo inteiro: entra rápido, assenta suave.
const ENTRA = Easing.out(Easing.cubic);
const SAI = Easing.in(Easing.cubic);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const FONTES: Record<string, string> = {
  "Inter-SemiBold.otf": "InterSemi",
  "Inter-Medium.otf": "InterMedium",
  "InterDisplay-Black.otf": "InterBlack",
  "InterDisplay-SemiBold.otf": "InterDisplaySemi",
  "InterDisplay-Bold.otf": "InterDisplayBold",
};
const familia = (f?: string) => FONTES[f ?? "Inter-SemiBold.otf"] ?? "InterSemi";

// Contorno escuro fino (para fundo misto, onde nenhuma cor sozinha tem contraste) + sombra suave.
const CONTORNO = (() => {
  const s: string[] = [];
  for (let a = 0; a < 16; a++) {
    const r = 3.2;
    s.push(`${(Math.cos((a / 16) * Math.PI * 2) * r).toFixed(2)}px ${(Math.sin((a / 16) * Math.PI * 2) * r).toFixed(2)}px 0 #0B0B0C`);
  }
  s.push("0 4px 16px rgba(0,0,0,.45)");
  return s.join(", ");
})();
const SOMBRA = "0 3px 18px rgba(0,0,0,.45)";

function useFontes() {
  const [h] = useState(() => delayRender("fontes"));
  useEffect(() => {
    const css = Object.entries(FONTES)
      .map(([arq, fam]) => `@font-face{font-family:${fam};src:url(${staticFile(`fonts/${arq}`)}) format("opentype");font-display:block}`)
      .join("");
    const st = document.createElement("style");
    st.innerHTML = css;
    document.head.appendChild(st);
    Promise.all(Object.values(FONTES).map((fam) => document.fonts.load(`64px ${fam}`)))
      .then(() => continueRender(h))
      .catch(() => continueRender(h));
  }, [h]);
}

function posicao(el: Elemento, t: number) {
  const ks: Chave[] | undefined = el.chaves;
  if (!ks || ks.length === 0) return { x: el.x ?? 540, y: el.y ?? 960, w: el.w ?? 0, h: el.h ?? 0 };
  if (ks.length === 1) return { x: ks[0].x, y: ks[0].y, w: ks[0].w ?? el.w ?? 0, h: ks[0].h ?? el.h ?? 0 };
  const ts = ks.map((k) => k.t);
  const at = (f: (k: Chave) => number) => interpolate(t, ts, ks.map(f), clamp);
  return { x: at((k) => k.x), y: at((k) => k.y), w: at((k) => k.w ?? el.w ?? 0), h: at((k) => k.h ?? el.h ?? 0) };
}

function anima(el: Elemento, t: number) {
  const de = el.dur_entrada ?? 0.25;
  const ds = el.dur_saida ?? 0.2;
  const p = el.entrada === "nenhuma" ? 1 : interpolate(t, [el.ini, el.ini + de], [0, 1], { ...clamp, easing: ENTRA });
  const q = el.saida === "nenhuma" ? 0 : interpolate(t, [el.fim - ds, el.fim], [0, 1], { ...clamp, easing: SAI });
  let dx = 0, dy = 0, s = 1;
  let op = p * (1 - q);
  if (el.entrada === "sobe") dy += (1 - p) * 70;
  if (el.entrada === "escala") s = 0.86 + 0.14 * p;
  if (el.entrada === "desliza-esq") dx += (1 - p) * -90;
  if (el.entrada === "desliza-dir") dx += (1 - p) * 90;
  if (el.saida === "afasta-esq") dx -= q * 700;
  if (el.saida === "afasta-dir") dx += q * 700;
  if (el.saida === "desce") dy += q * 70;
  return { op: op * (el.opacidade ?? 1), dx, dy, s };
}

const Mira: React.FC<{ w: number; h: number; cor: string; esp: number; escuro?: boolean }> = ({ w, h, cor, esp, escuro }) => {
  const L = Math.min(w, h) * 0.18;
  const d = [`M0 ${L}V0H${L}`, `M${w - L} 0H${w}V${L}`, `M0 ${h - L}V${h}H${L}`, `M${w - L} ${h}H${w}V${h - L}`].join(" ");
  return (
    <svg width={w} height={h} style={{ overflow: "visible" }}>
      {escuro ? <path d={d} fill="none" stroke="#0B0B0C" strokeWidth={esp + 5} strokeLinecap="square" opacity={0.85} /> : null}
      <path d={d} fill="none" stroke={cor} strokeWidth={esp} strokeLinecap="square" />
    </svg>
  );
};

const Camada: React.FC<{ el: Elemento; t: number }> = ({ el, t }) => {
  if (t < el.ini || t >= el.fim) return null;
  const { op, dx, dy, s } = anima(el, t);
  const { x, y, w, h } = posicao(el, t);
  const base: React.CSSProperties = {
    position: "absolute", left: x, top: y, opacity: op,
    transform: `translate(-50%, -50%) translate(${dx}px, ${dy}px) scale(${s})`,
  };
  if (el.tipo === "fundo") {
    return (
      <AbsoluteFill
        style={{
          opacity: op, backgroundColor: el.cor ?? "#0B0B0C",
          backgroundImage: el.grade ? "linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px)" : undefined,
          backgroundSize: el.grade ? "108px 108px" : undefined,
        }}
      />
    );
  }
  if (el.tipo === "texto") {
    return (
      <div
        style={{
          ...base, fontFamily: familia(el.fonte), fontSize: el.tamanho ?? 84, color: el.cor ?? "#F7F7F5", whiteSpace: "pre", lineHeight: 1.02,
          letterSpacing: `${el.tracking ?? 0}em`, textAlign: "center",
          textShadow: el.contorno_escuro ? CONTORNO : el.sombra ? SOMBRA : undefined,
        }}
      >
        {el.texto}
      </div>
    );
  }
  if (el.tipo === "caixa") {
    return <div style={{ ...base, width: w, height: h, borderRadius: el.raio ?? 18, background: el.cor ?? "#0B0B0C" }} />;
  }
  if (el.tipo === "mira") {
    return (
      <div style={base}>
        <Mira w={w} h={h} cor={el.cor ?? "#D4FF3A"} esp={el.espessura ?? 6} escuro={el.contorno_escuro} />
        {el.rotulo ? (
          <div style={{ position: "absolute", left: "50%", top: -40, transform: "translateX(-50%)", fontFamily: familia("Inter-Medium.otf"), fontSize: 24, letterSpacing: "0.16em", color: el.cor ?? "#D4FF3A", whiteSpace: "nowrap", textShadow: el.contorno_escuro ? CONTORNO : undefined }}>
            {el.rotulo}
          </div>
        ) : null}
      </div>
    );
  }
  if (el.tipo === "imagem" && el.src) {
    return <Img src={staticFile(el.src)} style={{ ...base, width: w, height: h, objectFit: "cover", borderRadius: el.raio ?? 24 }} />;
  }
  if (el.tipo === "contorno" && el.src) {
    return (
      <AbsoluteFill style={{ opacity: op }}>
        <OffthreadVideo src={staticFile(el.src)} transparent muted />
      </AbsoluteFill>
    );
  }
  return null;
};

function escalaZoom(zs: Zoom[], t: number) {
  for (const z of zs) {
    if (t >= z.ini && t < z.fim) {
      const k = interpolate(t, [z.ini, z.fim], [z.de, z.ate], { ...clamp, easing: Easing.inOut(Easing.cubic) });
      return { k, cx: z.cx, cy: z.cy };
    }
  }
  return { k: 1, cx: 540, cy: 960 };
}

const Legenda: React.FC<{ palavras: Palavra[]; t: number; fonte?: string }> = ({ palavras, t, fonte }) => {
  const w = palavras.find((p) => t >= p.ini && t < p.fim);
  if (!w) return null;
  const pop = interpolate(t, [w.ini, w.ini + 0.09], [0.86, 1], { ...clamp, easing: ENTRA });
  return (
    <div
      style={{
        position: "absolute", left: w.x, top: w.y, transform: `translate(-50%, -50%) scale(${pop})`,
        fontFamily: familia(fonte ?? "Inter-SemiBold.otf"), fontSize: w.tamanho, color: w.cor, whiteSpace: "nowrap",
        letterSpacing: "0.01em", textShadow: w.contorno_escuro ? CONTORNO : w.sombra === false ? undefined : "0 3px 14px rgba(0,0,0,.5)",
      }}
    >
      {w.texto}
    </div>
  );
};

export const Reel: React.FC<ReelProps> = (p) => {
  useFontes();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const z = escalaZoom(p.zoom ?? [], t);
  const atras = p.elementos.filter((e) => e.camada === "atras");
  const frente = p.elementos.filter((e) => e.camada === "frente");
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${z.k})`, transformOrigin: `${z.cx}px ${z.cy}px` }}>
        <OffthreadVideo src={staticFile(p.base)} muted />
        {atras.map((el) => <Camada key={el.id} el={el} t={t} />)}
        {p.pessoa ? <OffthreadVideo src={staticFile(p.pessoa)} transparent muted style={{ position: "absolute", inset: 0 }} /> : null}
      </AbsoluteFill>
      {frente.map((el) => <Camada key={el.id} el={el} t={t} />)}
      <Legenda palavras={p.legenda ?? []} t={t} fonte={p.fonte_legenda} />
      {p.audio ? <Audio src={staticFile(p.audio)} /> : null}
    </AbsoluteFill>
  );
};
