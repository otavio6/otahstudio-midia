# Bíblia de edição · editor de vídeo sênior

Vale para todo vídeo que a esteira edita. O editor sabe fazer tudo, mas cada vídeo usa só o que o eixo pede. Nada é jogado: cada elemento tem um motivo, um lugar na grade e uma cor escolhida pelo fundo.

## 0. A esteira do vídeo (um especialista por etapa)

Cada etapa é um agente separado (subagente), com uma função só. Ele recebe o arquivo da etapa anterior, faz o trabalho dele, confere a própria checklist e entrega um arquivo para a próxima. Tudo fica em `posts/<id>/edicao/`. O **diretor de edição** coordena, e o **revisor** no final não participa da edição.

| # | Agente | O que faz | Entrega |
|---|---|---|---|
| 1 | **Analista** | Transcreve com o tempo de cada palavra (Whisper no VPS). Marca frases, palavras-chave, respiros, vícios ("né", "tipo"), gaguejos e repetições. Encontra os takes do gancho. Mapeia quadro a quadro rosto, mãos e corpo (mapa de ocupação). Mede volume e ruído. | `01_analise.json` |
| 2 | **Diretor de edição** | Lê a análise e define o eixo (a ideia e a sensação), o sistema visual (grade, tipografia, cor, movimento, som) e o plano batida a batida: o que acontece em cada frase e por quê. Escolhe as técnicas, só as que servem. | `02_plano.md` |
| 3 | **Colorista: diagnóstico** | Mede o bruto: balanço de branco, exposição, contraste, saturação, tom de pele, diferença entre takes. | `03_cor_diagnostico.json` + quadros com histograma |
| 4 | **Colorista: grading** | Corrige primeiro (branco, exposição, igualar takes) e depois aplica o look da marca (Otávio: preto e branco com pele quente). Confere a pele e a consistência entre takes. | `04_grade.json` + antes e depois |
| 5 | **Montador (cortes e respiros)** | Corta silêncio, vício, gaguejo e repetição. Escolhe o melhor take do gancho. Deixa o respiro certo: curto na explicação, mais longo antes de uma frase forte. Define zoom de ênfase e troca de enquadramento. | `05_cortes.json` (lista de cortes) |
| 6 | **Designer de quadros-chave** | Desenha os momentos principais parados, na grade e nas áreas livres do mapa de ocupação, com a cor escolhida pelo contraste do fundo. Avalia com a régua de design. | `06_quadros/*.png` |
| 7 | **Motion** | Anima os quadros-chave com a curva única do vídeo, no tempo das palavras: texto, elementos, recorte, rastreio, tela dividida, transições. | camadas + prévia |
| 8 | **Legendista** | Legenda palavra por palavra, sincronizada, com destaque nas palavras-chave, cor pelo fundo e posição abaixo do queixo, dentro da zona segura. | `08_legenda.json` |
| 9 | **Sound designer** | Limpa a voz (ruído, chiado), nivela em -14 LUFS, coloca efeitos nas entradas que importam e música abaixando sozinha quando a voz entra. | `09_mix.wav` |
| 10 | **Finalizador** | Junta tudo e exporta (H.264, SDR bt709, 1080×1920, 30 fps). Gera a capa. Confere arquivo, duração, volume e legibilidade no celular. | `final.mp4` + `capa.jpg` |
| 11 | **Revisor** (independente) | Compara lado a lado com a referência e dá nota por critério (seção 6). Abaixo de 8 em qualquer critério, devolve para a etapa responsável com o motivo. | `11_revisao.json` |

Regras da esteira:
- Uma etapa não começa sem o arquivo da anterior. Se faltar dado (transcrição, por exemplo), ela para e avisa. Ela não inventa.
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
3. **O mínimo é 8 em todo critério, e a meta é 10.** Abaixo de 8, volte e corrija antes de mostrar.
4. Confira quadro a quadro os momentos de entrada e saída: nada cobrindo rosto, nada cortado, nada ilegível.

## 7. Referências

- **@fillrocha (anúncio "Possibilidades infinitas", nov/2026):** edição totalmente estilizada, com um sistema visual coerente. A decupagem do sistema dele (grade, tipografia, movimento, cor, som) entra aqui quando for feita.
