import os
from PIL import Image
from OpenGL.GL import *
from texture import Texture, pixelArt

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_FLOR = os.path.join(PASTA_BASE, 'textures', 'flower', 'flower_powerup.png')

# o PNG tem 2048x2048, mas a flor ocupa só o meio: recorta a área com desenho
RECORTE_FLOR = (683, 512, 1365, 1536)

# tamanho no mundo: a altura de um bloco. a textura é reduzida para exatamente esse tamanho
# (1 pixel da arte = 1 pixel do mundo, igual ao Lula e ao minion)
ALTURA_FLOR = 21
LARGURA_FLOR = round(ALTURA_FLOR * (1365 - 683) / (1536 - 512))   # 14

VELOCIDADE_SUBIDA = 0.7             # pixels por update saindo de dentro do bloco (~30 updates)

class FlorObject:
    # power-up: sai de dentro de um bloco [?] quando ele é aberto e fica parada em cima dele.
    # (x, y) é o canto inferior esquerdo, em pixels do mundo
    textura = 0

    def __init__(self, bloco):
        self.largura = LARGURA_FLOR
        self.altura = ALTURA_FLOR
        self.x = bloco.x + (bloco.largura - self.largura) / 2
        # começa escondida dentro do bloco e sobe até ficar apoiada no topo dele.
        # o bloco é desenhado depois da flor, então a parte ainda dentro dele fica escondida
        self.yFinal = bloco.y + bloco.altura
        self.y = self.yFinal - self.altura
        self.yAnterior = self.y

    @classmethod
    def carregarTextura(cls):
        img = Image.open(ARQUIVO_FLOR).convert('RGBA').crop(RECORTE_FLOR)
        cls.textura = Texture(pixelArt(img, (LARGURA_FLOR, ALTURA_FLOR))).texId

    @classmethod
    def deletarTextura(cls):
        if cls.textura:
            glDeleteTextures([cls.textura])
            cls.textura = 0

    def atualizar(self):
        self.yAnterior = self.y
        self.y = min(self.y + VELOCIDADE_SUBIDA, self.yFinal)

    def retangulo(self):
        return (self.x, self.y, self.x + self.largura, self.y + self.altura)

    def draw(self, sprites, alfa, alinhar):
        y = self.yAnterior + (self.y - self.yAnterior) * alfa
        sprites.desenhar(self.textura, alinhar(self.x), alinhar(y), self.largura, self.altura)
