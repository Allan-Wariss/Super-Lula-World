import os
from PIL import Image
from OpenGL.GL import *
from texture import Texture

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_BLOCOS = os.path.join(PASTA_BASE, 'textures', 'blocks')

# tipo do bloco -> arquivo do sprite
SPRITES_BLOCOS = {
    'muro': 'Bloco-Muro.png',       # azul (#004aad) no mapa de colisão
    'interrogacao': 'Bloco [_].png', # verde no mapa de colisão
}

# os PNGs originais são enormes (~1600 px); reduzidos para este tamanho antes de virar textura,
# senão o GL_NEAREST pula pixels e o bloco fica todo serrilhado
RESOLUCAO_SPRITE = 32

class BlocoObject:
    # um bloco é uma entidade: tem tipo, posição e tamanho no mundo e é sólido para o Lula.
    # (x, y) é o canto inferior esquerdo, em pixels do mundo (y para cima)
    texturas = {}                   # compartilhadas por todos os blocos do mesmo tipo

    def __init__(self, tipo, x, y, largura, altura):
        self.tipo = tipo
        self.x = x
        self.y = y
        self.largura = largura
        self.altura = altura
        self.solido = True

    @classmethod
    def carregarTexturas(cls):
        for tipo, arquivo in SPRITES_BLOCOS.items():
            img = Image.open(os.path.join(PASTA_BLOCOS, arquivo)).convert('RGBA')
            img = img.resize((RESOLUCAO_SPRITE, RESOLUCAO_SPRITE), Image.LANCZOS)
            cls.texturas[tipo] = Texture(img).texId

    @classmethod
    def deletarTexturas(cls):
        if cls.texturas:
            glDeleteTextures(list(cls.texturas.values()))
            cls.texturas = {}

    def colide(self, x0, y0, x1, y1):
        # o retângulo [x0, x1) x [y0, y1) encosta dentro deste bloco?
        return (self.solido and x0 < self.x + self.largura and x1 > self.x
                and y0 < self.y + self.altura and y1 > self.y)

    def draw(self, sprites):
        sprites.desenhar(self.texturas[self.tipo], self.x, self.y, self.largura, self.altura)
