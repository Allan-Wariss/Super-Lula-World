import math
from PIL import Image
from OpenGL.GL import *
from texture import Texture

# bola de fogo em pixel art 8x8 (1 pixel da arte = 1 pixel do mundo).
# '.' transparente, r vermelho, o laranja, y amarelo, w brilho (fora do centro, para dar
# para ver a bola "girando" quando o desenho é rotacionado)
DESENHO_BOLA = [
    "..rrrr..",
    ".roooor.",
    "rooyyoor",
    "royywyor",
    "royyyyor",
    "rooyyoor",
    ".roooor.",
    "..rrrr..",
]
CORES_BOLA = {
    'r': (200, 30, 20, 255),
    'o': (250, 120, 20, 255),
    'y': (255, 220, 60, 255),
    'w': (255, 255, 220, 255),
}

TAMANHO = 8
VELOCIDADE_X = 4.0          # pixels por update na direção em que o Lula está virado
VELOCIDADE_Y_INICIAL = -1.5 # sai descendo um pouco, como se fosse arremessada
GRAVIDADE = 0.35
VEL_QUEDA_MAX = 8.0
FORCA_QUIQUE = 3.8          # ~20 px de altura em cada quique
QUIQUES_MAX = 3             # quica 3 vezes; ao tocar o chão de novo, some
TEMPO_VIDA_MAX = 300        # segurança: some depois de 5 s de qualquer jeito
TICKS_POR_FRAME = 4         # gira (troca o desenho) a cada 4 updates

class BolaDeFogoObject:
    # (x, y) é o canto inferior esquerdo, em pixels do mundo
    TAMANHO = TAMANHO
    texturas = []               # 4 rotações do desenho, compartilhadas por todas as bolas

    def __init__(self, x, y, direcao):
        self.x = float(x)
        self.y = float(y)
        self.xAnterior, self.yAnterior = self.x, self.y
        self.largura = TAMANHO
        self.altura = TAMANHO
        self.vx = VELOCIDADE_X * direcao
        self.vy = VELOCIDADE_Y_INICIAL
        self.quiques = 0
        self.tempoVida = 0
        self.viva = True

    @classmethod
    def carregarTexturas(cls):
        img = Image.new('RGBA', (TAMANHO, TAMANHO), (0, 0, 0, 0))
        for y, linha in enumerate(DESENHO_BOLA):
            for x, c in enumerate(linha):
                if c in CORES_BOLA:
                    img.putpixel((x, y), CORES_BOLA[c])
        rotacoes = [img, img.transpose(Image.ROTATE_90), img.transpose(Image.ROTATE_180), img.transpose(Image.ROTATE_270)]
        cls.texturas = [Texture(r).texId for r in rotacoes]

    @classmethod
    def deletarTexturas(cls):
        if cls.texturas:
            glDeleteTextures(cls.texturas)
            cls.texturas = []

    def retangulo(self, x=None, y=None):
        x = self.x if x is None else x
        y = self.y if y is None else y
        return (x, y, x + self.largura, y + self.altura)

    def atualizar(self, fase):
        self.xAnterior, self.yAnterior = self.x, self.y
        self.tempoVida += 1
        if self.tempoVida > TEMPO_VIDA_MAX:
            self.viva = False
            return

        # 1. horizontal, 1 pixel por vez: bateu numa parede ou bloco -> some
        passos = math.ceil(abs(self.vx))
        passo = self.vx / passos
        for _ in range(passos):
            if fase.colideSolido(*self.retangulo(x=self.x + passo)):
                self.viva = False
                return
            self.x += passo

        # 2. vertical com gravidade: no chão quica (até 3 vezes), no teto só para de subir
        self.vy = max(self.vy - GRAVIDADE, -VEL_QUEDA_MAX)
        passos = max(1, math.ceil(abs(self.vy)))
        passo = self.vy / passos
        for _ in range(passos):
            if fase.colideSolido(*self.retangulo(y=self.y + passo)):
                if passo < 0:
                    if self.quiques >= QUIQUES_MAX:
                        self.viva = False
                        return
                    self.quiques += 1
                    self.vy = FORCA_QUIQUE
                else:
                    self.vy = 0.0
                break
            self.y += passo

        # caiu num buraco
        if self.y < -50:
            self.viva = False

    def draw(self, sprites, alfa, alinhar):
        x = alinhar(self.xAnterior + (self.x - self.xAnterior) * alfa)
        y = alinhar(self.yAnterior + (self.y - self.yAnterior) * alfa)
        # gira no sentido em que está indo
        frame = (self.tempoVida // TICKS_POR_FRAME) % 4
        if self.vx < 0:
            frame = (4 - frame) % 4
        sprites.desenhar(self.texturas[frame], x, y, self.largura, self.altura)
