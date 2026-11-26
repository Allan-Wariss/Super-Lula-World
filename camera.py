import numpy as np

class Camera:
    def __init__(self, alturaVisivel):
        self.x = 0.0                        # canto esquerdo da câmera no mundo (pixels)
        self.y = 0.0
        self.alturaVisivel = alturaVisivel  # quantos pixels do mundo cabem na altura da tela
        self.larguraVisivel = alturaVisivel
        self.escalaTela = 1.0               # quantos pixels da tela tem 1 pixel do mundo

    def ajustarTela(self, larguraJanela, alturaJanela):
        # mantém a proporção da janela para não esticar os pixels
        self.larguraVisivel = self.alturaVisivel * larguraJanela / alturaJanela
        self.escalaTela = alturaJanela / self.alturaVisivel

    def alinhar(self, valor):
        # arredonda uma posição do mundo para cair exatamente num pixel da TELA.
        # com zoom 1.5, 1 pixel do mundo = 1.5 pixel da tela: arredondar só no mundo
        # faz o personagem e a câmera "pularem" meio pixel um em relação ao outro
        return round(valor * self.escalaTela) / self.escalaTela

    def seguir(self, alvoX, alvoY, larguraFase, alturaFase):
        # regra clássica de jogo 2D: a fase fica parada e a câmera centraliza no personagem,
        # sem passar das bordas da fase
        x = alvoX - self.larguraVisivel / 2
        x = max(0.0, min(x, larguraFase - self.larguraVisivel))
        self.x = self.alinhar(x)            # alinhado na grade da tela evita tremer os pixels

        # na vertical o personagem fica um pouco abaixo do centro (mostra mais o que está acima)
        y = alvoY - self.alturaVisivel * 0.4
        y = max(0.0, min(y, alturaFase - self.alturaVisivel))
        self.y = self.alinhar(y)

    def matrizProjecao(self):
        esq, dir = self.x, self.x + self.larguraVisivel
        baixo, cima = self.y, self.y + self.alturaVisivel
        return np.array([
            [2 / (dir - esq), 0,                 0,  -(dir + esq) / (dir - esq)],
            [0,               2 / (cima - baixo), 0, -(cima + baixo) / (cima - baixo)],
            [0,               0,                -1,  0],
            [0,               0,                 0,  1],
        ], dtype=np.float32)
