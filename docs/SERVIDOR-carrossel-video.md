# Pedido de mudança no servidor: carrossel com slides em vídeo

Para quem mexe no servidor do Instagram (MCP `Instagram OTAHSTUDIO`, painel ig.otahstudio.com.br e agendador) na VPS do Otávio. Pedido do Otávio em 26/11/2026: poder postar carrossel em que cada slide é um vídeo.

## O que muda no registro (já vale a partir de agora)

Um carrossel com motion tem no `data/registro.json`:

```json
{"id": "2026-11-27-qual-o-valor", "formato": "carrossel", "slides": 7, "motion": true}
```

Com `"motion": true`, os slides são os vídeos `posts/<id>/motion/01.mp4` … `NN.mp4` (1080×1350, H.264, 30 fps, 5 s cada, sem áudio), no lugar de `posts/<id>/01.png` … `NN.png`. As imagens continuam na pasta e servem de reserva. Sem o campo (ou `false`), nada muda.

Para carregar pelo GitHub, use a mesma URL pública que o servidor já usa para os PNGs, trocando `NN.png` por `motion/NN.mp4`.

## 1. Agendador (publicação)

Fluxo da Graph API para carrossel com vídeo:

1. Para cada slide, crie um container filho:
   `POST /{ig-user-id}/media` com `media_type=VIDEO`, `video_url=<url do mp4>`, `is_carousel_item=true`.
   Imagem continua como hoje (`image_url`, `is_carousel_item=true`). Pode misturar imagem e vídeo.
2. **Espere cada filho de vídeo ficar pronto:** consulte `GET /{container-id}?fields=status_code` até `FINISHED` (a cada 5 s, até 5 min). Se vier `ERROR` ou estourar o tempo, a postagem vai para `estado: erro` com o motivo.
3. Crie o container do carrossel: `POST /{ig-user-id}/media` com `media_type=CAROUSEL`, `children=<ids em ordem>`, `caption=<legenda>`.
4. Espere o container do carrossel ficar `FINISHED` e publique com `POST /{ig-user-id}/media_publish`.
5. Grave `media_id` e `permalink` em `painel_decisoes`, como hoje.

Limites: 2 a 10 slides; vídeo de slide entre 3 s e 60 s. Cada carrossel conta 1 na cota de 100 por 24 h.

Comece a criar os filhos de vídeo uns 10 min antes do horário, porque o processamento leva tempo, e publique no horário aprovado.

## 2. Ferramenta MCP `publish_carousel`

Aceitar, além de `image_urls`, uma lista `items: [{"type": "image" | "video", "url": "..."}]`, com o mesmo fluxo de espera. Atualize a descrição da ferramenta.

## 3. Painel

- No card do carrossel com `motion: true`, mostrar os vídeos (tag `<video muted loop playsinline autoplay>`) no lugar das imagens, com as setas para passar.
- Escrever "Carrossel animado · N vídeos" no card.
- Os botões Aprovar e Refazer continuam iguais.

## Como testar antes de valer

1. Publicar numa conta de teste, ou criar os containers sem chamar o `media_publish`, com o post `2026-11-27-qual-o-valor` (os 7 vídeos já estão em `posts/2026-11-27-qual-o-valor/motion/`).
2. Conferir que os 7 filhos chegam a `FINISHED` e o carrossel também.
3. Só depois disso marcar o carrossel do dia 27 com `motion: true` (decisão do Otávio).

## Quem gera os vídeos

`node engine/motion_carrossel.js posts/<id>` gera `posts/<id>/motion/NN.mp4` e uma `previa.mp4` (todos os slides em sequência, só para ver; não vai para o Instagram).
