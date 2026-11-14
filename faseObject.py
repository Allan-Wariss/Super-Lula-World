import os
import ctypes
import numpy as np
from PIL import Image
from OpenGL.GL import *
from texture import Texture
from shader import Shader

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_FASE = os.path.join(PASTA_BASE, 'textures', 'fase')
PASTA_SHADERS = os.path.join(PASTA_BASE, 'shaders')

class FaseObject:
    def __init__(self, imagem='fase-teste.png', colisao='fase-colisao-teste.png',
                 colisaoEscalaX=1.06, colisaoDeslocY=9):
        self.caminhoImagem = os.path.join(PASTA_FASE, imagem)
        self.caminhoColisao = os.path.join(PASTA_FASE, colisao)

        # o mundo tem o tamanho da arte da fase, em pixels
        arte = Image.open(self.caminhoImagem)
        self.largura, self.altura = arte.size

        # ---- mapa de colisão ----
        # a imagem de colisão foi desenhada um pouco menor que a arte: ela é esticada em X
        # e descida em Y para os blocos pretos ficarem exatamente em cima do desenho.
        # se a imagem de colisão for refeita alinhada com a arte, basta usar escala 1 e deslocamento 0
        colisaoImg = Image.open(self.caminhoColisao).convert('RGB')
        colisaoImg = colisaoImg.resize((round(colisaoImg.width * colisaoEscalaX), colisaoImg.height), Image.NEAREST)
        alinhada = Image.new('RGB', (self.largura, self.altura), (255, 255, 255))
        alinhada.paste(colisaoImg, (0, colisaoDeslocY))

        mapa = np.array(alinhada).astype(np.int16)
        mapa = mapa[::-1]                   # imagem tem y para baixo, o mundo tem y para cima

        r, g, b = mapa[..., 0], mapa[..., 1], mapa[..., 2]
        preto = (r < 64) & (g < 64) & (b < 64)
        vermelho = (r > 192) & (g < 64) & (b < 64)

        self.mortal = vermelho
        # por enquanto o vermelho também é chão; a regra de morrer entra depois
        self.solido = preto | vermelho

        # imagem da colisão para o modo debug (tecla C): preto e vermelho semi-transparentes
        debug = np.zeros((self.altura, self.largura, 4), dtype=np.uint8)
        debug[preto] = (0, 0, 0, 255)
        debug[vermelho] = (255, 0, 0, 255)
        self.imagemDebug = Image.fromarray(debug[::-1], 'RGBA')
        self.mostrarColisao = False

        # ---- quad da fase, ocupando o mundo todo (0,0) até (largura, altura) ----
        self.vertices = np.array([
            0.0,           0.0,           0.0, 0.0,
            self.largura,  0.0,           1.0, 0.0,
            self.largura,  self.altura,   1.0, 1.0,
            0.0,           self.altura,   0.0, 1.0,
        ], dtype=np.float32)

        self.faces = np.array([
            0, 1, 2,
            0, 2, 3
        ], dtype=np.uint32)

        # estilo 16 bits
        self.tamanhoBloco = 2.0             # cada "pixel" retrô = 2x2 texels (3 deixava a arte borrada demais)
        self.niveisCor = (31.0, 63.0, 31.0) # RGB565

        self.shader = None
        self.vao = 0
        self.vbo = 0
        self.ebo = 0
        self.texId = 0
        self.texDebugId = 0

    def init(self):
        self.shader = Shader(os.path.join(PASTA_SHADERS, 'fase.vert'),
                             os.path.join(PASTA_SHADERS, 'fase.frag'))

        self.texId = Texture(self.caminhoImagem).texId
        self.texDebugId = Texture(self.imagemDebug).texId

        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.ebo = glGenBuffers(1)

        glBindVertexArray(self.vao)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.faces.nbytes, self.faces, GL_STATIC_DRAW)

        stride = 4 * self.vertices.itemsize

        # location 0 -> aPosicao
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        # location 1 -> aUV
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(2 * self.vertices.itemsize))
        glEnableVertexAttribArray(1)

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        self.shader.usar()
        self.shader.setInt('uTextura', 0)
        self.shader.setVec2('uTamanhoTextura', self.largura, self.altura)
        self.shader.setFloat('uTamanhoBloco', self.tamanhoBloco)
        self.shader.setVec3('uNiveisCor', *self.niveisCor)
        glUseProgram(0)

    def areaColide(self, mapa, x0, y0, x1, y1):
        # verifica se algum pixel do retângulo [x0, x1) x [y0, y1) está marcado no mapa
        x0 = max(int(np.floor(x0)), 0)
        y0 = max(int(np.floor(y0)), 0)
        x1 = min(int(np.ceil(x1)), self.largura)
        y1 = min(int(np.ceil(y1)), self.altura)
        if x0 >= x1 or y0 >= y1:
            return False
        return bool(mapa[y0:y1, x0:x1].any())

    def colideSolido(self, x0, y0, x1, y1):
        return self.areaColide(self.solido, x0, y0, x1, y1)

    def colideMortal(self, x0, y0, x1, y1):
        # ainda não é usado: fica pronto para a regra de morte
        return self.areaColide(self.mortal, x0, y0, x1, y1)

    def draw(self, projecao):
        self.shader.usar()
        self.shader.setMat4('uProjecao', projecao)

        glActiveTexture(GL_TEXTURE0)
        glBindVertexArray(self.vao)

        # 1. arte da fase com o estilo 16 bits
        self.shader.setInt('uEstilo16bits', 1)
        self.shader.setFloat('uOpacidade', 1.0)
        glBindTexture(GL_TEXTURE_2D, self.texId)
        glDrawElements(GL_TRIANGLES, len(self.faces), GL_UNSIGNED_INT, None)

        # 2. modo debug: colisão desenhada por cima, meio transparente
        if self.mostrarColisao:
            self.shader.setInt('uEstilo16bits', 0)
            self.shader.setFloat('uOpacidade', 0.5)
            glBindTexture(GL_TEXTURE_2D, self.texDebugId)
            glDrawElements(GL_TRIANGLES, len(self.faces), GL_UNSIGNED_INT, None)

        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)

    def delete(self):
        glDeleteVertexArrays(1, [self.vao])
        glDeleteBuffers(2, [self.vbo, self.ebo])
        glDeleteTextures([self.texId, self.texDebugId])
        self.shader.delete()
