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

---

# Pedido 2: botão "Atrasei" nos reels

Pedido do Otávio em 26/11/2026. No card de um reel que ainda não foi gravado (status `roteiro`), um botão **Atrasei** remaneja o reel.

- **Novo horário:** o próximo horário livre a partir de amanhã, com pelo menos 4 h de distância de qualquer outro post do dia. Pode haver 2 reels no mesmo dia, desde que respeitem as 4 h; não existe limite de 1 por dia.
- **Os outros reels:** os reels `roteiro` seguintes andam junto ("empurra a fila"), sem trocar a ordem entre eles. Peças já `agendado` ou `publicado` não mudam.
- **Data marcada:** reel com `"data_fixa": true` (tema preso a um dia, como Black Friday) não anda sozinho. O painel pergunta: "Mudar para <novo dia> e adaptar o texto" ou "Cancelar".
- **Registro:** grava a decisão em `painel_decisoes` como `{"acao": "atrasar", "de": "<data hora antiga>", "para": "<data hora nova>"}`. A esteira, no A0, atualiza `data` e `horario` no `registro.json` e adapta o roteiro se ele citar o dia ("sexta", "hoje", "amanhã").
- **Mesmo dia, temas que brigam:** se o novo dia já tiver uma peça com tema contrário (exemplo: oferta e crítica a desconto), o painel avisa antes de confirmar.

---

# Pedido 3: vídeo enviado tira o reel da lista "Gravar"

Pedido do Otávio em 27/11/2026: ele gravou os reels, mandou pela aba Enviar vídeo, e os cards "Gravar: …" continuaram em "Para você agora".

- **Status que já existe:** reel com `status: "gravado"` no `registro.json` sai de "Gravar" e da contagem "N reels na fila para gravar" e aparece cinza ("Gravado · em edição"). Hoje o painel só olha `roteiro`; ele precisa tratar `gravado` também.
- **Ligação com o bruto:** o reel gravado tem `"bruto": {"id": "<id do painel_brutos>", "titulo": "...", "gravado_em": "AAAA-MM-DD"}`. No card, mostrar "Bruto: <titulo>".
- **Na hora do envio:** a aba Enviar vídeo ganha um campo "Qual roteiro é este?" com a lista dos reels `roteiro` (título e dia), com "Nenhum / outro" no fim. Ao escolher, o servidor grava o `bruto` no reel e muda o status para `gravado` sozinho.
- **Pelo teleprompter:** o botão Teleprompter já sabe qual reel é; depois de gravar, o "Enviar vídeo" aberto a partir dali vem com o roteiro já escolhido.
- **Sem escolha:** se o bruto vier sem roteiro, a esteira associa pela fala (transcrição) e grava o `bruto` e o `gravado` no registro, como foi feito em 27/11.
- Quando o vídeo editado entra (`video` no registro e status `rascunho`), o card vira "Aprovar reel", como hoje.

---

# Pedido 4: trava de horário e de ordem (o que o texto promete tem que ser verdade)

Pedido do Otávio em 27/11/2026: "falou que o post sai 2 horas, tem que sair 2 horas; falou que já está no feed, tem que estar no feed".

O que aconteceu e mostra o furo:
- O story `2026-11-24-story-black-11h` diz "Hoje no feed · 11h". No registro ele era de 24/11 09:00, mas foi aprovado em 23/11 e publicado **em 23/11 às 14:35**, um dia antes do carrossel (que saiu 24/11 11:00). Para quem viu, "hoje às 11h" era mentira.
- O story `2026-11-26-story-achou-caro` era 18:00, foi aprovado às 18:42 e saiu às 19:00. Aqui não quebrou nada (o post era das 11h), mas o atraso foi silencioso.

O que o servidor precisa fazer:
1. **Nunca antes da data do registro.** Aprovar só programa. A peça sai em `data` + `horario` do `registro.json`, nunca no momento da aprovação. "Postar agora" só com confirmação explícita no painel ("Sair agora, fora do calendário?").
2. **Aprovação atrasada:** se o horário já passou, o painel pergunta "Sair agora (HH:MM) ou escolher outro horário?" e grava o horário real.
3. **Story que chama post** tem o campo `"chama": "<id do post>"` no registro (já preenchido nos stories). O agendador só solta o story se o post chamado já estiver `publicado` (com permalink). Se o post atrasar ou der erro, o story fica segurado e o painel avisa ("Story segurado: o post X ainda não saiu").
4. **Texto com tempo:** antes de publicar story, legenda ou arte, procure "hoje", "amanhã", "agora", "às HHh", "no feed", "post de hoje", "domingo", "sexta" etc. Se a data/hora de publicação não bater com o que o texto diz, segure e avise no painel. Exemplo: a legenda do estático da Nivea diz "até amanhã, domingo" e só pode sair em 28/11.
5. **Volta para o registro:** quando algo é publicado, o servidor grava `status: publicado`, `instagram_media_id` e `permalink` no `registro.json` (ou a esteira faz isso a cada execução, lendo `painel_decisoes`). Hoje o registro só é atualizado à noite e passa o dia dizendo "agendado" para o que já está no ar.
