from PIL import Image
from OpenGL.GL import *
from texture import Texture
from florObject import FlorObject

# tamanho no mundo (pixels). provisório: por enquanto o power-up é só um bloquinho cinza
TAMANHO_LULATRON = 14

class LulatronObject(FlorObject):
    # power-up único do Lulatron: sai do bloco [_] marcado de laranja no mapa de colisão.
    # sobe de dentro do bloco e fica parado em cima dele, igual à flor (só muda o desenho e o efeito)
    # TODO: trocar o bloquinho cinza pelo sprite do power-up quando ele existir
    LARGURA = TAMANHO_LULATRON
    ALTURA = TAMANHO_LULATRON
    textura = 0

    @classmethod
    def carregarTextura(cls):
        # bloquinho cinza com borda mais escura e um brilho no canto, para dar volume
        n = TAMANHO_LULATRON
        img = Image.new('RGBA', (n, n), (150, 150, 150, 255))
        for i in range(n):
            for borda in ((i, 0), (i, n - 1), (0, i), (n - 1, i)):
                img.putpixel(borda, (70, 70, 70, 255))
        for i in range(2, 5):
            img.putpixel((i, 2), (220, 220, 220, 255))
            img.putpixel((2, i), (220, 220, 220, 255))
        cls.textura = Texture(img).texId

    def pegar(self, lula):
        lula.pegarLulatron()
