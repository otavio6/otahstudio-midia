import React from "react";
import { Composition } from "remotion";
import { Reel } from "./Reel";
import type { ReelProps } from "./tipos";

const padrao: ReelProps = { duracao: 5, base: "job/base.mp4", pessoa: null, audio: null, elementos: [], legenda: [], zoom: [] };

export const Root: React.FC = () => (
  <Composition
    id="Reel"
    component={Reel as unknown as React.FC<Record<string, unknown>>}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={150}
    defaultProps={padrao as unknown as Record<string, unknown>}
    calculateMetadata={({ props }: { props: Record<string, unknown> }) => ({ durationInFrames: Math.max(1, Math.ceil(Number((props as unknown as ReelProps).duracao) * 30)) })}
  />
);
