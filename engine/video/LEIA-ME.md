# Kit do editor de vídeo

> **Montagem por cenas (desde 23/11/2026).** A edição final é feita pelo `montar.py`: cada trecho do vídeo é uma cena
> (`pessoa`, `cheia`, `canto` ou `dividida`) e as cenas em motion são HTML/SVG animados (`motion/base.js` + `motion/base.css`),
> renderizados quadro a quadro pelo `motion.py` no Chromium local. Assim cabe qualquer motion 2D (gráfico, contador,
> comparação, post genérico, balão, botão), o vídeo sai com um encode só e na taxa de quadros do bruto (`VIDEO_FPS`).
> O `timeline.py` + Remotion continuam como alternativa para edições simples.

Uma ferramenta por etapa da esteira (veja `docs/EDICAO.md`). Rode na ordem, dentro de `engine/video/`. Cada etapa grava na pasta do trabalho e a revisão de cada portão usa o que ela gerou.

| Etapa | Comando | Gera |
|---|---|---|
| 1 · Assistir e entender | `python analisar.py BRUTO PASTA --transcricao palavras.json` | `proxy.mp4`, `ocupacao.npz`, `folha.jpg`, `01_analise.json` |
| 2 · Cor | `python cor.py diagnostico PASTA` e depois `python cor.py aplicar PASTA` | `02_cor.json`, `02_cor_antes_depois.jpg`, `base_cor.mp4` |
| 3 · Corte | `python cortar.py PASTA [--remover i,j] [--manter k]` | `03_cortes.json` (com checagem de palavra cortada), `base.mp4` |
| 3b · Recorte | `python pessoa.py PASTA --contorno "#D4FF3A"` | `pessoa.webm`, `contorno.webm`, `ocupacao_final.npz` |
| 4 · Mapeamento | o diretor escreve `04_plano.json` (batidas ligadas às palavras) | |
| 5 · Edição | `python timeline.py PASTA` | `timeline.json` (lugar livre + cor pelo fundo), `eventos_som.json`, `05_relatorio.json` |
| 6 · Som | `python som.py PASTA [--musica faixa.mp3]` | `mix.wav` (-14 LUFS), `06_som.json` |
| Prévia | `python render_local.py PASTA` | `previa.mp4` (mesma lógica do Remotion) |
| Revisão | `python revisar.py PASTA [--referencia folha_ref.jpg]` | `revisao_folha.jpg`, `revisao_checagens.json` |
| Final | copiar a pasta para o repositório privado de brutos e chamar `renderizar_video` (Remotion no VPS) | `render.mp4` |

Os modelos (recorte RVM e detector de rosto YuNet) são baixados do GitHub na primeira vez, para `~/.cache/otahstudio-video`. A transcrição vem do Whisper no VPS (`transcrever`).

## Formato do 04_plano.json

```json
{"marca": "otavio", "eixo": "uma frase", "destaques": ["palavra", "chave"],
 "batidas": [
  {"id": "titulo", "tipo": "texto", "estilo": "titulo|numero|rotulo|frase|etiqueta", "camada": "atras|frente",
   "texto": "RELATIVO", "gatilho": "relativo", "dur": 1.0, "lugar": ["topo"], "destaque": true, "entrada": "sobe", "saida": "fade"},
  {"tipo": "fundo", "de": "porque", "ate": "acerto"},
  {"tipo": "contorno", "de": "porque", "ate": "acerto"},
  {"tipo": "mira", "de": "eles", "ate": "necessariamente", "rotulo": "PERSPECTIVA"},
  {"tipo": "zoom", "de": "os", "ate": "opostos", "escala": 1.08, "impacto": true},
  {"tipo": "imagem", "src": "print.png", "gatilho": "...", "dur": 1.5, "w": 600, "h": 420, "lugar": ["topo"]}
 ]}
```
Entradas: sobe, escala, desliza-esq, desliza-dir, fade, nenhuma. Saídas: fade, afasta-esq, afasta-dir, desce, nenhuma.

## De onde vem o bruto

O Otávio manda o vídeo pelo painel (aba **Enviar vídeo**, direto da galeria do celular). O servidor guarda no repositório
privado `otavio6/otahstudio-brutos`, na pasta `brutos/AAAA-MM-DD-titulo/`, em partes de 20 MB, com um `manifesto.json`
(título, recado para o editor, sha256 e o comando para juntar). A ferramenta `painel_brutos` lista a fila: os que estão
`pronto` e sem `editado` são os próximos. Para juntar: `cat video.mov.parte01 video.mov.parte02 ... > video.mov` e confira
o sha256. Depois de entregar a edição, marque com `painel_bruto_editado`.

