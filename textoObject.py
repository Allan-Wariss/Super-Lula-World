import numpy as np
from PIL import Image, ImageDraw, ImageFont
from OpenGL.GL import *
from texture import Texture

def carregarFonte(tamanho):
    for nome in ('arialbd.ttf', 'arial.ttf', 'DejaVuSans-Bold.ttf'):
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            pass
    return ImageFont.load_default(size=tamanho)

class TextoObject:
    # texto desenhado com o PIL numa imagem, que vira textura e é mostrada no centro da tela
    def __init__(self, texto, tamanhoFonte=56):
        fonte = carregarFonte(tamanhoFonte)
        borda = max(2, tamanhoFonte // 12)

        esq, topo, dir, baixo = fonte.getbbox(texto, stroke_width=borda)
        margem = 4
        self.largura = dir - esq + 2 * margem
        self.altura = baixo - topo + 2 * margem

        img = Image.new('RGBA', (self.largura, self.altura), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((margem - esq, margem - topo), texto, font=fonte,
                                 fill=(255, 255, 255, 255),
                                 stroke_width=borda, stroke_fill=(0, 0, 0, 255))
        self.imagem = img
        self.texId = 0
        self.visivel = False

    def init(self):
        self.texId = Texture(self.imagem).texId

    def draw(self, sprites, larguraTela, alturaTela):
        if not self.visivel:
            return
        # projeção da tela: 1 unidade = 1 pixel da janela, não depende da câmera
        projecao = np.array([
            [2 / larguraTela, 0,               0, -1],
            [0,               2 / alturaTela,  0, -1],
            [0,               0,              -1,  0],
            [0,               0,               0,  1],
        ], dtype=np.float32)
        x = round((larguraTela - self.largura) / 2)
        y = round((alturaTela - self.altura) / 2)
        sprites.comecar(projecao)
        sprites.desenhar(self.texId, x, y, self.largura, self.altura)
        sprites.terminar()

    def delete(self):
        glDeleteTextures([self.texId])
