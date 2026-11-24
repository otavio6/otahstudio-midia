# Revisor de vídeo (agente separado)

**Quem edita não dá nota.** Toda nota de portão, inclusive a final, vem de um agente revisor aberto do zero: ele não viu a edição sendo feita, não leu o raciocínio do editor e não tem interesse em aprovar. Nota dada pelo próprio editor não vale e não libera etapa. Esta regra veio do Otávio (23/11/2026), depois de um reel que o editor avaliou com 9 e ele achou ruim.

## Como chamar

O editor abre um subagente novo, sem passar o histórico dele, e entrega só:
- o vídeo da etapa (ou a folha de quadros dela, para etapas sem vídeo);
- a transcrição e o objetivo do vídeo, em uma frase;
- a referência aprovada (`docs/EDICAO.md` §8) e este arquivo.

O revisor assiste por quadros: um a cada 0,5 s, mais os quadros de troca de cena, mais um recorte do áudio medido (volume, pico, espectro). Ele não recebe o `04_plano.json` antes de dar a primeira impressão, para julgar o que está na tela e não a intenção.

## O que ele avalia (0 a 10 cada, com o motivo)

1. **Áudio.** A voz soa natural, sem cara de processada (abafada, "debaixo d'água", chiado de redutor, volume bombando)? Sem estalo nos cortes? Volume perto de -14 LUFS, pico até -1 dB? **Toda palavra inteira e entendível**: nenhum pedaço de palavra cortada sobrando, nenhum começo ou fim de palavra comido, nenhum "s" repetido na emenda. O revisor lê `07_audio.json` (transcrição do áudio cortado comparada com a fala esperada, inclusive plural x singular) e confere de ouvido cada emenda que aparece lá. Problema sem explicação no `07_audio.json` = Áudio no máximo 5.
2. **Imagem.** Está tão nítida quanto o bruto? Sem trepidação, sem quadro repetido, sem serrilhado, sem cor estourada? Pele natural?
3. **Corte.** Palavras inteiras, respiros naturais, nenhum pulo estranho, começa prendendo no primeiro segundo?
4. **A edição explica o que está sendo dito.** Cada recurso na tela ajuda a entender aquela frase? Onde dava para ser didático (gráfico, esquema, comparação, print, tela cheia, tela dividida) e ficou só texto?
5. **Variedade.** Algum recurso se repete sem motivo? Mais de 2 vezes o mesmo truque, ou a mesma sequência (fundo preto, texto, volta ao normal) em loop, reprova este critério.
6. **Composição.** Textos centralizados no eixo do vídeo (ou num grid claro), nada cortado na borda, nada fora da zona segura, nada em cima do rosto ou da boca, hierarquia clara.
7. **Identidade.** Só preto e lima no texto, sem contorno nem sombra no texto, Inter, cara premium e minimalista. Nada parece efeito pronto jogado.
8. **Nível da referência.** Lado a lado com a referência aprovada, está no mesmo nível de acabamento?
9. **Propósito.** Uma pessoa que nunca viu o Otávio entende a ideia, fica até o fim e sabe o que fazer depois?

## Regras da nota

- A nota da etapa é a **menor** entre os critérios que valem para ela, não a média.
- Etapa passa com 8 ou mais. A final só libera com 9 ou mais em todos os critérios.
- O revisor lista os defeitos em ordem de gravidade, cada um com o tempo (ex.: "12,4 s: texto cortado na borda direita") e o que fazer.
- Se ele achar que o problema é de repertório (o editor não tem o recurso certo), diz qual recurso faltou.
- Na dúvida, nota menor. Melhor refazer do que chegar ruim no Otávio.

## O que fica registrado

`posts/<id>/edicao/revisoes.json`, uma entrada por portão: etapa, versão, notas por critério, defeitos, decisão (passa ou refaz) e `"revisor": "agente separado"`. A ficha `edicao` do registro só recebe as notas do revisor.
