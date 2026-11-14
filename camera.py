import numpy as np

class Camera:
    def __init__(self, alturaVisivel):
        self.x = 0.0                        # canto esquerdo da câmera no mundo (pixels)
        self.y = 0.0
        self.alturaVisivel = alturaVisivel  # quantos pixels do mundo cabem na altura da tela
        self.larguraVisivel = alturaVisivel

    def ajustarTela(self, larguraJanela, alturaJanela):
        # mantém a proporção da janela para não esticar os pixels
        self.larguraVisivel = self.alturaVisivel * larguraJanela / alturaJanela

    def seguir(self, alvoX, larguraFase):
        # regra clássica de jogo 2D: a fase fica parada e a câmera centraliza no personagem,
        # sem passar das bordas da fase
        x = alvoX - self.larguraVisivel / 2
        x = max(0.0, min(x, larguraFase - self.larguraVisivel))
        self.x = round(x)                   # posição inteira evita tremer os pixels

    def matrizProjecao(self):
        esq, dir = self.x, self.x + self.larguraVisivel
        baixo, cima = self.y, self.y + self.alturaVisivel
        return np.array([
            [2 / (dir - esq), 0,                 0,  -(dir + esq) / (dir - esq)],
            [0,               2 / (cima - baixo), 0, -(cima + baixo) / (cima - baixo)],
            [0,               0,                -1,  0],
            [0,               0,                 0,  1],
        ], dtype=np.float32)
