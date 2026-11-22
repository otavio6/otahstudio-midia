# Bíblia de edição · editor de vídeo sênior

Vale para todo vídeo que a esteira edita. O editor sabe fazer tudo, mas cada vídeo usa só o que o eixo pede. Nada é jogado: cada elemento tem um motivo, um lugar na grade e uma cor escolhida pelo fundo.

## 0. A esteira do vídeo (método)

Nada de "vou ver e editar". O vídeo passa por etapas na ordem abaixo, e **depois de cada etapa tem uma revisão com nota de 0 a 10**. A etapa só passa para a próxima com nota 8 ou mais. Abaixo disso, ela é refeita com o comentário do revisor. Cada etapa é um agente separado. O revisor de cada portão é outro agente, que não fez o trabalho. Tudo fica em `posts/<id>/edicao/`, com as notas em `revisoes.json`.

### Etapa 1 · Assistir e entender (Analista)
- Assiste o vídeo inteiro, quadro a quadro: movimentação, gestos, enquadramento, luz, cenário.
- Transcreve com o tempo de cada palavra (Whisper no VPS) e entende o assunto, a ideia central e onde estão as frases fortes.
- Marca respiros, vícios ("né", "tipo"), gaguejos, repetições e takes repetidos do gancho.
- Faz o mapa de ocupação (rosto, mãos e corpo em cada quadro) e mede volume e ruído.
- Entrega `01_analise.json`.
- **Revisão 1:** a transcrição bate com o áudio? Nenhuma palavra errada? O assunto e as frases fortes foram entendidos? O mapa de ocupação acompanha os gestos?

### Etapa 2 · Cor (Colorista)
- Diagnóstico: como o bruto está (branco, exposição, contraste, saturação, pele) e como vai ficar.
- Grading **natural e levemente cinematográfico**: mexer no básico, sem pesar.
  - Pretos mais pretos (ponto preto firme), contraste leve.
  - Saturação geral baixa: o resto da imagem fica mais esbranquiçado e neutro.
  - Pele com cor natural e o rosa da boca preservado.
  - Igualar os takes entre si.
- Entrega `02_cor.json` + quadros antes e depois.
- **Revisão 2:** está gostoso de assistir? Não está forte nem pesado? A pele está natural e a boca rosada? O preto está firme sem esmagar detalhe? Os takes estão iguais?

### Etapa 3 · Corte (Montador)
- Corta junto vídeo e respiros do áudio: silêncios, vícios, gaguejos, repetições. Escolhe o melhor take do gancho.
- Respiro certo: curto na explicação, um pouco mais longo antes de frase forte.
- O começo pega no primeiro segundo.
- Entrega `03_cortes.json` + prévia cortada.
- **Revisão 3:** todas as palavras estão certas e inteiras? Nenhuma sílaba cortada, nenhum pulo estranho na imagem? A frase continua fazendo sentido? O começo prende?

### Etapa 4 · Mapeamento de edição (Diretor de edição)
- Passa trecho por trecho e pergunta o que cabe em cada um:
  - dá para deixar **didático** (passo a passo, lista, número na tela)?
  - dá para deixar **explicativo** (esquema, comparação, tela dividida)?
  - dá para usar **imagem real** (print, foto, vídeo de apoio)?
  - qual **variação** de linguagem funciona melhor (texto atrás, recorte, zoom, rastreio, motion)?
- Para cada trecho, propõe de 2 a 3 opções e dá nota de **potencial de retenção** (prender e fazer assistir até o fim) a cada uma.
- Escolhe o caminho com a maior nota e escreve o plano: eixo, sistema visual (grade, tipografia, cor pelo fundo, um tipo de movimento) e o que acontece em cada frase.
- Entrega `04_mapa.md`.
- **Revisão 4:** o caminho escolhido é o de maior potencial? Tudo serve ao eixo? Tem algo novo a cada 1,5 a 2 s? Está coerente, sem efeito jogado?

### Etapa 5 · Edição (Designer + Motion + Legendista)
- Primeiro os quadros-chave parados, na grade e nas áreas livres, com a cor escolhida pelo fundo. Depois a animação, com uma curva só e no tempo das palavras. Por último a legenda palavra a palavra, embaixo do queixo, com as palavras-chave destacadas.
- Entrega a prévia editada + `05_edicao.json`.
- **Revisão 5:** nada cobre o rosto, nada cortado na borda, nada ilegível? O contraste está certo? O ritmo está bom? A legenda está sincronizada e sem erro? Lado a lado com a referência, o nível é comparável?

### Etapa 6 · Som (Sound designer)
- Assiste o vídeo editado e decide onde cabe efeito sonoro: só nas entradas que importam.
- Limpa a voz, nivela em -14 LUFS e coloca música (se houver) abaixando sozinha quando a voz entra.
- Entrega `06_mix.wav`.
- **Revisão 6:** o som ajuda ou distrai? A voz está sempre na frente? O volume está certo no celular?

### Etapa 7 · Finalização e revisão final (Finalizador + Revisor)
- Exporta (H.264, SDR bt709, 1080×1920, 30 fps), gera a capa e confere no tamanho do celular.
- **Revisão final:** assiste do começo ao fim e dá a nota geral. **Só passa com 9 ou 10**, junto com a frase: "este vídeo está pronto para cumprir o propósito dele". Só então ele vai para o Otávio aprovar. Abaixo de 9, volta para a etapa que puxou a nota para baixo.

Regras da esteira:
- Uma etapa não começa sem o arquivo e a nota aprovada da anterior. Se faltar dado (transcrição, por exemplo), ela para e avisa. Ela não inventa.
- Cada agente só mexe no que é dele. O montador não muda cor, o colorista não corta.
- O revisor devolve para a etapa certa, não para o começo.
- Tudo o que o Otávio corrigir vira regra na etapa responsável.

## 1. Antes de editar (pré-produção)

1. **Decupagem:** transcreva a fala com o tempo de cada palavra, marque as frases, as palavras-chave e os respiros.
2. **Eixo:** em uma frase, qual é a ideia do vídeo e qual sensação ele precisa deixar. Tudo o que entra serve ao eixo.
3. **Sistema visual do vídeo:** grade, tamanhos de tipografia (no máximo 3), cores (a paleta da marca), um tipo de movimento (mesma curva, mesma duração, mesma direção) e um tipo de som. Escreva antes de começar.
4. **Mapa de ocupação:** quadro a quadro, onde estão o rosto, as mãos e o corpo (detector de rosto + recorte da pessoa). Isso define as áreas livres.
5. **Quadros-chave:** desenhe os momentos principais como imagens paradas e avalie com a régua de design (grade, hierarquia, respiro, contraste) antes de animar. Se o quadro parado não fica bonito, o vídeo também não vai ficar.

## 2. Regras de posição

- Elemento só entra em área livre da grade. Se a mão vai passar por ali, ele muda de lugar ou espera a mão sair.
- Texto atrás da cabeça só de propósito, e a palavra importante precisa ficar inteira e legível.
- Nada encosta na borda nem sai cortado, a não ser numa saída animada de propósito.
- Respeite a zona segura do Reels: 250 px livres em cima e 340 px embaixo (1080×1920), e a lateral direita onde ficam os botões.
- A legenda fica abaixo do queixo e acima da zona de baixo. Nunca em cima da boca ou dos olhos.

## 3. Regras de cor (contraste antes de marca)

- **A cor sai do fundo, não do gosto.** Antes de colocar um texto ou elemento, meça a luminância do que está atrás dele.
- **Fundo claro:** texto preto (#0B0B0C). **Fundo escuro:** branco ou lime.
- **O lime (#D4FF3A) só entra em fundo escuro.** Em fundo claro, ele some.
- O contraste mínimo é 4,5:1 para texto pequeno e 3:1 para texto grande. Se o fundo varia (parede, rosto, mão), use sombra suave ou uma faixa por trás, ou escolha outro lugar.
- No máximo uma cor de destaque por tela.

## 4. Movimento e ritmo

- Algo novo na tela a cada 1,5 a 2 s, sempre ligado ao que está sendo dito naquele momento.
- Os elementos entram no tempo da palavra (com tolerância de 2 quadros).
- Uma curva de movimento para o vídeo inteiro, com entrada rápida e saída suave. Nada de cada elemento se mexer de um jeito.
- Zoom e corte servem à fala: ênfase, troca de ideia, respiro. Nunca por enfeite.

## 5. Som

- Voz em primeiro lugar, a -14 LUFS.
- Efeito sonoro só em entrada que importa (troca de cena, palavra-chave, impacto) e baixo.
- A música, quando houver, abaixa sozinha quando a voz entra.

## 6. Revisão (antes de chegar no Otávio)

1. Compare lado a lado com a referência da vez, no mesmo tempo.
2. Dê nota de 0 a 10 por critério: eixo e coerência, grade e posição, contraste e cor, tipografia, ritmo, legenda, som, acabamento, fidelidade à marca.
3. **Nos portões das etapas, o mínimo é 8. Na revisão final, o mínimo é 9 e a meta é 10.** Abaixo disso, volte e corrija antes de mostrar.
4. Confira quadro a quadro os momentos de entrada e saída: nada cobrindo rosto, nada cortado, nada ilegível.

## 7. Aprender com as métricas (a edição evolui)

Cada reel é um experimento. A esteira guarda **como** ele foi editado e, depois, **como** ele performou. Com o tempo, ela descobre o formato que mais segura e espalha, e o mapeamento de edição (etapa 4) passa a partir dele.

**Ficha de edição.** Toda edição grava no `registro.json`, dentro da peça, o campo `edicao`:
```json
"edicao": {
  "gancho": {"tipo": "pergunta | número | afirmação contraintuitiva | cena | provocação", "texto_tela": "...", "primeira_frase": "...", "visual": "zoom | texto atrás | recorte | corte seco | b-roll", "duracao_s": 1.8},
  "duracao_s": 38, "cortes_por_min": 24, "novidades_por_10s": 5,
  "tecnicas": ["texto atrás", "recorte", "rastreio", "tela dividida"],
  "legenda": "palavra a palavra, destaque lime",
  "cor": "natural cinematográfico", "som": {"efeitos": true, "musica": false},
  "cta": "comentário palavra-chave | seguir | salvar | enviar", "trial_reel": false,
  "variavel_testada": "gancho visual"
}
```

**Métricas que importam para a edição** (Parte B, todo dia, nos 30 dias de vida do reel):
- **Gancho:** taxa de pulo (quem passou direto nos primeiros segundos) e views. É a métrica do gancho.
- **Meio:** tempo médio assistido e porcentagem do vídeo assistida (tempo médio ÷ duração).
- **Fim:** replays, comentários e cliques no perfil.
- **Espalhar:** compartilhamentos, salvamentos, alcance de quem não segue e seguidores ganhos.

**Como testar sem se enganar:**
- **Mude uma coisa por vez.** Cada reel declara a `variavel_testada` (gancho visual, primeira frase, ritmo de corte, música, duração, CTA). O resto segue o melhor formato até ali.
- **Trial Reels para testar gancho:** o mesmo conteúdo com dois ganchos diferentes, mostrado só para quem não segue. É o teste mais limpo que existe.
- **Nada de conclusão com 1 vídeo.** Um padrão só vira regra com pelo menos 3 reels a favor e a diferença aparecendo nas métricas certas (por exemplo, gancho → taxa de pulo).
- **80/20:** 80% dos reels seguem o formato vencedor e 20% testam algo novo, para não estacionar.

**Onde o aprendizado fica:** na seção "Vídeo" de `data/aprendizados.md`, com o que funciona, o que não funciona, o teste em andamento e o placar de cada variável. A etapa 4 (mapeamento) lê essa seção antes de propor as opções, e a nota de potencial de retenção leva em conta o histórico.

## 8. Referências

- **@fillrocha (anúncio "Possibilidades infinitas", nov/2026):** edição totalmente estilizada, com um sistema visual coerente. A decupagem do sistema dele (grade, tipografia, movimento, cor, som) entra aqui quando for feita.
