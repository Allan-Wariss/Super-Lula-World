import os
from PIL import Image, ImageOps, ImageEnhance
from OpenGL.GL import *
from texture import Texture

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_BLOCOS = os.path.join(PASTA_BASE, 'textures', 'blocks')

# tipo do bloco -> arquivo do sprite
SPRITES_BLOCOS = {
    'muro': 'Bloco-Muro.png',       # azul (#004aad) no mapa de colisão
    'interrogacao': 'Bloco [_].png', # verde no mapa de colisão
    'lulatron': 'Bloco [_].png',     # laranja no mapa de colisão: mesmo bloco, mas solta o Lulatron
}

# os PNGs originais são enormes (~1600 px); reduzidos para este tamanho antes de virar textura,
# senão o GL_NEAREST pula pixels e o bloco fica todo serrilhado
RESOLUCAO_SPRITE = 32

# blocos que não quebram: ao serem acertados por baixo passam de 'fechado' para 'aberto'
TIPOS_INQUEBRAVEIS = {'interrogacao', 'lulatron'}

def acinzentar(img):
    # versão "aberta" do bloco: sem cor e um pouco mais escura, mantendo a transparência
    alfa = img.getchannel('A')
    cinza = ImageOps.grayscale(img.convert('RGB'))
    cinza = ImageEnhance.Brightness(cinza).enhance(0.75)
    resultado = cinza.convert('RGBA')
    resultado.putalpha(alfa)
    return resultado

class BlocoObject:
    # um bloco é uma entidade: tem tipo, posição e tamanho no mundo e é sólido para o Lula.
    # (x, y) é o canto inferior esquerdo, em pixels do mundo (y para cima)
    texturas = {}                   # (tipo, estado) -> textura, compartilhada por todos os blocos

    def __init__(self, tipo, x, y, largura, altura):
        self.tipo = tipo
        self.x = x
        self.y = y
        self.largura = largura
        self.altura = altura
        self.solido = True
        self.estado = 'fechado'     # só muda nos blocos inquebráveis

    def quebravel(self):
        return self.tipo not in TIPOS_INQUEBRAVEIS

    def abrir(self):
        # devolve True se mudou de estado agora (já aberto não faz nada)
        if self.estado == 'fechado':
            self.estado = 'aberto'
            return True
        return False

    @classmethod
    def carregarTexturas(cls):
        for tipo, arquivo in SPRITES_BLOCOS.items():
            img = Image.open(os.path.join(PASTA_BLOCOS, arquivo)).convert('RGBA')
            img = img.resize((RESOLUCAO_SPRITE, RESOLUCAO_SPRITE), Image.LANCZOS)
            cls.texturas[(tipo, 'fechado')] = Texture(img).texId
            if tipo in TIPOS_INQUEBRAVEIS:
                cls.texturas[(tipo, 'aberto')] = Texture(acinzentar(img)).texId

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
        sprites.desenhar(self.texturas[(self.tipo, self.estado)], self.x, self.y, self.largura, self.altura)
