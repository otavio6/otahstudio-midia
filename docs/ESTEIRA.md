# Esteira de conteúdo · @otaviohenriqve

Este é o manual que as tarefas automáticas seguem. A meta é **chegar a 1.000 seguidores** (eram 134 em 13/11/2026). Não existe cota fixa de posts: cada ideia forte vira peça. Alguns limites práticos seguram a qualidade e estão descritos abaixo.

Sobre o que a esteira lê e grava:
- **O que lê antes de começar:** este manual, `data/aprendizados.md`, `data/registro.json` e os últimos arquivos em `data/performance/`.
- **O que grava:** `data/execucoes.json` no começo e no fim (veja "Diário de execução"), e `data/registro.json` ao terminar, sempre com commit no repositório.

**Regra de ouro:** nada vai ao ar sem a aprovação explícita do Otávio: o botão **Aprovar** no painel (ig.otahstudio…/painel) ou um "ok" dele no chat. Quem posta é o agendador do servidor dele, no horário aprovado. A esteira nunca chama `publish_*` direto.

---

## Quem é a marca

| Item | Definição |
|---|---|
| Quem fala | Otávio Henrique, diretor de operações e marketing num grupo de saúde, dono da OTAHSTUDIO. |
| Posicionamento | "Construo marcas de saúde que faturam milhões." Método próprio: Método EDEN. |
| Pilares | Marketing, marca/branding e gestão, sempre vistos de dentro da operação. |
| Público | Donos de clínica, profissionais de saúde e donos de negócio que querem uma marca que vende. |
| Tom | Direto, provocativo, de quem está dentro da operação. Confronta crenças sem ofender pessoas ou grupos. |
| Nunca | Faturamento de cliente, dados ou fotos de paciente, conversas internas, estratégia não lançada, nome de hospital sem autorização (Dr. Felipe e Realizza são permitidos), política partidária, tragédias, promessa de resultado. |

---

## Diário de execução (vale para a Parte A e a Parte B)

O painel do Otávio mostra se cada tarefa rodou, quando e como terminou, lendo `data/execucoes.json`. Toda execução, agendada ou manual, escreve nele:

1. **Logo depois do clone**, antes de qualquer outra etapa: acrescente em `execucoes` uma entrada e faça commit e push na hora.
   ```json
   {"id":"criacao-2026-11-22T06:49","tarefa":"criacao","inicio":"2026-11-22T06:49:00-03:00","status":"rodando","fim":null,"resumo":"","etapas":{}}
   ```
   `tarefa` é `criacao` (Parte A) ou `analise` (Parte B). Use a hora real (`TZ=America/Sao_Paulo date -Iseconds`).
2. **Ao terminar**, atualize a mesma entrada e faça commit e push:
   - `fim`: a hora real;
   - `status`: `ok` (tudo feito), `parcial` (terminou, mas alguma etapa falhou ou foi pulada) ou `erro` (parou no meio);
   - `resumo`: uma frase do que aconteceu, por exemplo "2 peças aprovadas pelos revisores e 1 roteiro; esperando o ok do Otávio" ou "Metricool sem dados de hoje; aprendizados não atualizados";
   - `etapas`: os números da execução, como `{"ideias":6,"aprovadas_potencia":2,"pecas":2,"reels":1,"rascunhos":2}` na criação ou `{"posts_medidos":9,"seguidores":137,"publicados_conferidos":1}` na análise.
3. **Se der erro**, grave `status: "erro"` com o motivo em `resumo` antes de parar. Se nem isso for possível, o painel mostra "não rodou" sozinho quando passar do horário.
4. Na criação, quando o Otávio responder e você agendar (A8), acrescente ao `resumo` o que foi agendado.
5. Mantenha só as 60 entradas mais recentes. Não mexa na lista `tarefas` do arquivo, a não ser que o horário de uma tarefa agendada mude.

---

## PARTE A · Esteira de criação (todo dia, de manhã)

### A0 · Decisões do painel (antes de tudo)
Chame `painel_decisoes` no conector **Instagram OTAHSTUDIO**. Vale só a decisão cuja `versao` é igual à `versao` da peça no registro (sem campo = 1).
- **refazer:** é prioridade do dia. Refaça a peça com a `nota` do Otávio, passe de novo por A5 a A7, sobrescreva os arquivos na mesma pasta, some 1 na `versao` da peça no registro, mantenha `status: rascunho` e faça push. Com a versão nova, o pedido antigo deixa de valer e a peça volta a ficar amarela no painel. Mostre a peça refeita na mensagem do dia.
- **aprovar** com `estado: programado`: ponha `status: agendado` no registro. Com `estado: publicado`: `status: publicado`, `instagram_media_id` e `permalink`. Com `estado: erro`: conte o erro ao Otávio em 1 linha (o botão "Tentar de novo" fica no painel).

Cada etapa tem um dono. **Os revisores são subagentes separados** (ferramenta Agent), que recebem só a peça e a rubrica, nunca o raciocínio de quem criou. Toda nota é registrada.

### A1 · Radar (pesquisador)
- Pesquise na web o que está em alta no Brasil nas últimas 24 a 72 h:
  - trends do Instagram/TikTok e memes;
  - notícias de marcas (rebrand, campanha, polêmica, lançamento, crise);
  - negócios e mercado;
  - mudanças nas plataformas.
- Abra as fontes. Snippet não conta como fonte.
- Inclua também 2 ou 3 ideias atemporais que ainda não estão no `registro.json`: erros de marca, posicionamento, preço, gestão de time, bastidores.
- Saída: uma lista de 6 a 12 ideias, cada uma com fonte, fato central e possível ponte com marca, marketing ou gestão.

### A2 · Revisor de potência (subagente)
Dá nota de 0 a 10 para cada ideia, como média destes critérios:

| Critério | A pergunta |
|---|---|
| Relevância | O dono de clínica ou negócio se importa com isso? |
| Timing | Está quente agora ou é atemporal de verdade? |
| Ponte | A lição de marca, marketing ou gestão é clara e não forçada? |
| Compartilhamento | Alguém mandaria isso para um sócio ou colega? |
| Ângulo novo | Foge do que já foi publicado (veja `registro.json`) e do que todo perfil está falando? |
| Risco | Política, tragédia ou exposição de alguém valem nota 0 e descartam a ideia. |

Seguem para a próxima etapa as ideias com **nota ≥ 7,5**, até **3 peças de feed** e **2 roteiros de reel** por dia. Acima disso a qualidade cai. Se nenhuma passar, faça a melhor e avise que foi um dia fraco.

### A3 · Escolha do formato
| Formato | Quando usar |
|---|---|
| **Reel** | Opinião, reação a algo em alta, bastidor, provocação que pede rosto e voz. É o formato que traz alcance novo, então é a prioridade quando a ideia é forte. Sai como roteiro para o Otávio gravar. |
| **Carrossel** | Explicação, lista, passo a passo, dado ou prova. Conteúdo que dá vontade de salvar. |
| **Estático** | Uma frase única muito forte, uma provocação ou uma comparação visual. |

Leia `aprendizados.md`: se um formato está performando muito melhor, puxe para ele.

### A4 · Copywriter
1. **Ângulo:** escolha o que faz a pessoa pensar "é a minha situação". Opções: dor, medo de perder, comparação com o concorrente, crença errada, fenômeno com nome, número que choca, bastidor, previsão, antes e depois.
2. **Método, pelo nível de consciência do público:**
   - **PAS** (problema, agitação, solução) para público frio com dor clara;
   - **BAB** (antes, depois, ponte) para transformação;
   - **AIDA** para novidade ou tendência;
   - **Mecanismo único** para quem já busca solução;
   - **Hook-Story-Lesson** para bastidor.
3. **Gancho:** escreva **5 ganchos**, uma frase cada, usando contraste, número concreto, pergunta incômoda ou afirmação contraintuitiva. Escolha o mais forte e guarde 2 de reserva.
4. **Estrutura:**
   - abra um loop logo depois do gancho;
   - cada frase dá motivo para a próxima;
   - desenvolva com o erro comum, depois a prova (fato verificável, com fonte) e depois a virada para o público;
   - feche com um princípio curto e salvável, que deixe a sensação de "aprendi algo de verdade";
   - termine com uma chamada simples (salvar, enviar, seguir ou comentar).
5. **Forma:** frases curtas, voz ativa, acentos corretos, nada de clichê de coach. Reel no jeito de falar do Otávio ("cara", "pô", "olha só"), com 30 a 45 s e o texto do gancho na tela.
6. **Legenda:** 4 a 8 linhas e 3 a 5 hashtags.

### A5 · Revisor de copy (subagente, com visão de mercado)
Dá nota de 0 a 10 em cada critério:
- força do gancho: para o dedo em 1 segundo?
- ângulo e identificação;
- retenção e loop;
- clareza;
- prova e credibilidade;
- fecho salvável;
- tom: provocativo sem ofender;
- impacto de mercado: isso se destaca no feed de quem segue perfis de marketing?
- conformidade: acentos certos, nada proibido, sem promessa.

Para passar, a **média precisa ser ≥ 8,5 e nenhum critério pode ficar abaixo de 7**. Se não passar, o copywriter reescreve com os comentários do revisor, no máximo 2 vezes. Se ainda assim não passar, descarte a ideia ou faça a melhor versão e registre a nota.

### A6 · Construção
**Carrossel e estático (designer):**
- Siga a skill `carrossel-otaviohenriqve`. **O motor atualizado fica em `engine/` deste repositório** (template.html, render.js, brand.json, avatar.jpg): renderize com `node engine/render.js posts/<pasta>`, onde a pasta tem o `spec.json`. Os specs de exemplo dos templates T01–T20 estão no artifact https://claude.ai/artifact/677Q3YrBAmPzCAKSZ5dQsz, mas o motor de lá é antigo. A saída é 1080×1350.
- Recursos novos do motor (21/11):
  - `"grid": false` em U, D2, T, V e F;
  - `dots` no U: grade de 100 pontos com `on`, `hot` e `cap`;
  - `step` no D2;
  - no D: `title`, `pills: true` (Sim e Não, sem checkbox) e `label`;
  - no M2: `ctaLight: true` e `icon: "plus"`;
  - `visual: "notifs"` em M2 e A;
  - no TW: `bold` (quantos parágrafos em negrito), `boldSize`, `gap`, `foot` (rodapé da série) e quebra de linha com `\n` dentro do parágrafo.
- Exemplos aprovados (média ≥ 8,5): `posts/2026-11-24-black-friday-clinica/spec.json` (carrossel, 8,56) e `posts/2026-11-26-preco-explicacao/spec.json` (estático, 8,63).
- Fundamentos obrigatórios:
  - hierarquia clara;
  - margens e zona segura respeitadas;
  - nada solto ou longe demais do elemento a que pertence;
  - espaçamento consistente;
  - contraste legível;
  - nada sobreposto ou cortado;
  - acentos certos.
- **Imagem nos vazios:** quando um slide de miolo tiver espaço vazio grande, coloque uma imagem que reforce a ideia do slide. O motor aceita o campo `photo` (data URI), com bordas arredondadas.
  - A capa não leva imagem, salvo se a ideia pedir.
  - Fontes da imagem, nesta ordem: fotos do Otávio em `assets/fotos/`, se houver; depois uma imagem gerada com a ferramenta de imagem do ElevenLabs (gasta créditos do Otávio: no máximo 2 imagens por peça), em estilo editorial, sem logos, marcas ou pessoas reais identificáveis.
  - Se usar imagem gerada por IA com aparência realista, diga isso na legenda.
- **Sem repetir layout:** compare com as `assinatura` das 10 últimas peças no `registro.json`. A capa e a sequência de módulos não podem repetir. Varie a composição dentro da identidade:
  - fundo claro ou escuro;
  - grid;
  - tipo de capa;
  - blocos de número, lista, comparação, citação ou foto.
- Paleta: preto, branco e off-white, com acento lime #D4FF3A ou azul #1F4FFF. Vermelho #E5484D só para marcar erro.


**Estático estilo tweet (TW), padrão definido pelo Otávio em 21/11:** igual a um print real de tweet. Texto em peso normal, num tamanho só (`size` 54), em parágrafos corridos. Sem negrito, sem lista com setas, sem rodapé da série e sem acento colorido: é a simplicidade que gera conexão. Referência: `posts/2026-11-26-preco-explicacao/`. O revisor de qualidade não deve descontar pontos por vazio, falta de acento ou falta de rodapé nesse formato.

**Reel:**
- Mande o roteiro para o Otávio gravar.
- Quando o vídeo bruto chegar, a edição segue a skill `edicao-video-otaviohenriqve`:
  - cor: preto e branco com contraste; só a pele e os lábios ficam quentes e saturados;
  - legenda: Inter SemiBold, uma palavra por vez, lime no fundo escuro e azul no fundo claro;
  - zona segura e exportação SDR na resolução original.
- Se o Otávio usar o clone de IA (HeyGen), faça a pós-produção: cortes, tela dividida se fizer sentido, legenda e cor no mesmo padrão.

### A7 · Revisor de qualidade (subagente que olha as imagens ou assiste o vídeo)
**Arte**, nota de 0 a 10 em cada critério:
- composição e hierarquia;
- alinhamento, margens e zona segura;
- espaçamento (nada solto);
- legibilidade e contraste;
- fidelidade à marca;
- novidade do layout em relação ao registro;
- uso de imagem;
- acabamento: nada sobreposto, cortado ou com erro de texto.

**Vídeo**, nota de 0 a 10 em cada critério:
- qualidade técnica: resolução, nitidez, SDR;
- correção de cor (look Otávio);
- pele e lábios;
- legenda: sincronia, posição, zona segura, fonte;
- cortes e ritmo;
- áudio: nível e ruído;
- gancho na tela no primeiro segundo;
- cartela final.

Para passar, a **média precisa ser ≥ 8,5 e nenhum critério pode ficar abaixo de 7**. Se não passar, volte para a construção com os comentários, no máximo 2 vezes.

### A8 · Aprovação do Otávio
1. Suba a mídia em `posts/AAAA-MM-DD-<tema>/` no repositório (01.png…, legenda.txt e notas.json com todas as notas) e faça o push. As URLs públicas são `https://raw.githubusercontent.com/otavio6/otahstudio-midia/main/posts/<pasta>/<arquivo>`. O agendador posta exatamente esses arquivos: carrossel = `01.png` até o número de `slides`; estático = `01.png`; reel = o arquivo do campo `video` (e `capa`, se houver). A legenda é o `legenda.txt`.
2. Registre a peça (A9) com `status: rascunho`, `versao: 1`, `data` e `horario`. Escolha o horário pela `getBestTimeToPostByNetwork` do Metricool e por `aprendizados.md`, a pelo menos 4 h de outro post do dia. **Não crie post no Metricool**: o Metricool fica só para os dados. A peça já aparece amarela no painel, com os botões Aprovar e Refazer.
3. Mande **uma mensagem só** com todas as peças do dia, numeradas. Cada peça leva:
   - a prévia (imagem com os slides lado a lado, via SendUserFile);
   - o tema e a fonte;
   - a nota de potência, a de copy e a de qualidade;
   - a legenda;
   - o horário proposto.
4. Os roteiros de reel vão na mesma mensagem, prontos para gravar.
5. Termine com: **"Aprove no painel (botão Aprovar) ou responda 'ok' para tudo, 'ok 1,3' para algumas, ou diga o que mudar."**

Depois da resposta no chat:
- **ok:** para cada peça aprovada, chame `painel_aprovar` com o `id` (e `quando`, se ele pediu outro horário). O servidor posta sozinho no horário. Atualize o registro para `status: agendado`.
- **Ajuste:** refaça, suba de novo, some 1 na `versao` e mande uma nova prévia.
- **Sem resposta:** nada vai ao ar. A peça continua amarela no painel até ele decidir.
- Para desfazer uma aprovação, use `painel_cancelar` (ele também pode cancelar pelo painel).

### A8b · Reels (o Otávio grava, Claude edita)
Quando o Otávio mandar o vídeo bruto no chat, ponha o reel como `status: gravado` (cinza no painel), edite com a skill `edicao-video-otaviohenriqve` e exporte MP4 H.264 vertical 1080×1920. Depois:
1. suba `posts/<id>/video.mp4`, `capa.jpg` (opcional) e `legenda.txt`;
2. no registro, ponha `status: rascunho`, `video: "video.mp4"`, `capa: "capa.jpg"` se houver, `trial: true` se for Trial Reel, `data` e `horario`;
3. faça push e avise o Otávio: o reel aparece no painel com o player, e ele aprova ou pede para refazer por lá.

### A9 · Registro
Para cada peça, acrescente ao `data/registro.json`:

```json
{"id":"2026-11-23-post-de-clinica","data":"2026-11-23","formato":"carrossel","tema":"...","fonte":"https://...","angulo":"crença errada","metodo":"PAS","gancho":"...","ganchos_reserva":["...","..."],"assinatura":"capa:frase-grande-escura | numero | lista | foto-direita | cta-claro","notas":{"potencia":8.2,"copy":8.9,"qualidade":9.0},"metricool":{"id":0,"uuid":"","horario":"2026-11-23T18:00:00"},"status":"rascunho|agendado|publicado|recusado|reprovado|roteiro|gravado","instagram_media_id":null,"permalink":null,"horario":"HH:MM","titulo":"nome curto para o calendário","slides":6}
```

Para reels, inclua também `"roteiro": {"tela": "texto do gancho na tela", "fala": ["frase 1", "frase 2"], "tipo": "seguidor/cliente"}`. O **painel do Otávio** (ig.otahstudio/painel) lê este arquivo para montar o calendário. Sem `data`, `horario`, `titulo` e `status` certos, a peça não aparece no calendário.

Faça commit e push.

---

## PARTE B · Esteira de análise (todo dia, à noite)

1. **Conferir postagem.** Chame `painel_decisoes` e `list_recent_media` (conector Instagram OTAHSTUDIO). Para cada peça com aprovação publicada, ponha no registro `status: publicado`, `instagram_media_id` e `permalink`. Aprovação programada vira `status: agendado`. Se uma postagem deu erro, ou se passou do horário e não saiu, avise o Otávio em 1 linha.
2. **Foto do dia.** Puxe no Metricool (`getAnalyticsDataByMetrics`) os dados de todos os posts e reels dos últimos 30 dias:
   - posts: IGPO02 data, IGPO03 legenda, IGPO28 views, IGPO14 alcance, IGPO29 seguidores;
   - reels: IGRE02, IGRE03, IGRE23 views, IGRE11 alcance, IGRE21 compartilhamentos, IGRE12 salvamentos, IGRE24 tempo médio assistido, IGRE30 taxa de pulo;
   - conta: IGEV01 seguidores, IGEV43 ganhos, IGEV44 perdidos, IGEV06 alcance.

   Salve tudo em `data/performance/AAAA-MM-DD.json`, com `"analisado_em": "AAAA-MM-DDTHH:MM-03:00"`. O arquivo **sempre** traz `"conta": {"seguidores": N}` no nível de cima, com o número do dia (o painel monta o gráfico de crescimento com esse campo). Ao atualizar o `status` de um item no registro (agendado, publicado), o painel muda de cor sozinho. Cada post é acompanhado por 30 dias, dia a dia.
3. **Aprendizados.** Reescreva `data/aprendizados.md` (topo: data e hora da análise) com:
   - o placar: seguidores, ganho do dia, da semana e do mês, e quanto falta para 1.000;
   - o top 5 e o bottom 5 por alcance, compartilhamento, salvamento e seguidores, cruzando com ângulo, método, formato, gancho, assinatura e horário do registro;
   - o que funciona e o que não funciona, como regras curtas baseadas em dados ("gancho com número: alcance 2,1× a média em 6 posts");
   - o que testar a seguir: até 3 hipóteses.
4. Faça as contas rodando código, nunca de cabeça. Nada de número inventado: se faltar dado, diga que falta.
5. Faça commit e push.
6. **Mensagem para o Otávio:** só se houver algo relevante (post que estourou, falha de publicação, queda forte). Às **sextas**, mande sempre o placar da semana: seguidores, quanto falta, campeão, pior e até 3 ajustes.

---

## Conector Instagram OTAHSTUDIO (API oficial da Meta)

O Otávio conectou um servidor MCP próprio, que aparece como as ferramentas `Instagram_OTAHSTUDIO`. A cota é de 100 publicações a cada 24 h. Esse conector **publica na hora**: ele não agenda.

- **Leitura (use à vontade):**
  - `account_overview`: seguidores e cota;
  - `list_recent_media`: posts com id, link, curtidas e comentários;
  - `media_insights`: reach, views, saved, shares e total_interactions por post;
  - `account_insights`: métricas da conta no período;
  - `list_comments`: comentários de cada post.

  A esteira de análise (Parte B) usa essas ferramentas como fonte principal, com o Metricool como reserva. `list_comments` também serve para achar leads: quem comentou palavra-chave ou pediu diagnóstico. Liste essas pessoas para o Otávio responder.
- **Painel e agendador:** `painel_decisoes` (o que ele aprovou, o que foi postado e o que pediu para refazer), `painel_aprovar` (só depois do "ok" dele no chat) e `painel_cancelar`. O agendamento é sempre por aqui, nunca pelo Metricool.
- **Publicação direta** (`publish_carousel`, `publish_image`, `publish_reel`, `publish_story`): a esteira **não usa**. Só em pedido explícito do Otávio no chat para postar algo na hora, como um story.
- **Responder comentários** (`reply_comment`): só com o texto aprovado pelo Otávio.
- **Segurança:** nunca repita tokens ou links com `access_token` em mensagens, arquivos ou commits.

---

## Limites técnicos

- **Metricool:** só para dados (análise e melhor horário). O plano grátis não limita mais a quantidade de posts, porque quem posta é o agendador do servidor. A cota da Meta é de 100 posts por 24 h.
- **Daqui não dá para enviar arquivo direto para outro servidor.** A mídia sempre passa pelo GitHub, neste repositório público.
- **Repositório:** clone com `--depth 1` e faça push com `git -c push.negotiate=true push`.
- **Erros:** se algo der errado no push ou no Metricool, não fique tentando em loop. Entregue os arquivos e diga o erro em 1 linha.
