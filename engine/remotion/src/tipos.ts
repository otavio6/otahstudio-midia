// Contrato entre a esteira (Python) e a composição. A esteira decide posição, cor e tempo; aqui só se desenha.
export type Entrada = "sobe" | "escala" | "desliza-esq" | "desliza-dir" | "fade" | "nenhuma";
export type Saida = "fade" | "afasta-esq" | "afasta-dir" | "desce" | "nenhuma";
export type Chave = { t: number; x: number; y: number; w?: number; h?: number };

export type Elemento = {
  id: string;
  tipo: "texto" | "caixa" | "mira" | "imagem" | "fundo" | "contorno";
  camada: "atras" | "frente";
  ini: number;
  fim: number;
  texto?: string;
  fonte?: string;
  tamanho?: number;
  tracking?: number;
  cor?: string;
  sombra?: boolean;
  contorno_escuro?: boolean;
  x?: number;
  y?: number;
  w?: number;
  h?: number;
  raio?: number;
  opacidade?: number;
  grade?: boolean;
  src?: string;
  rotulo?: string;
  espessura?: number;
  chaves?: Chave[];
  entrada?: Entrada;
  saida?: Saida;
  dur_entrada?: number;
  dur_saida?: number;
};

export type Palavra = {
  texto: string;
  ini: number;
  fim: number;
  destaque?: boolean;
  cor: string;
  x: number;
  y: number;
  tamanho: number;
  sombra?: boolean;
  contorno_escuro?: boolean;
};

export type Zoom = { ini: number; fim: number; de: number; ate: number; cx: number; cy: number };

export type ReelProps = {
  duracao: number;
  base: string;
  pessoa?: string | null;
  audio?: string | null;
  elementos: Elemento[];
  legenda: Palavra[];
  zoom: Zoom[];
  fonte_legenda?: string;
};
