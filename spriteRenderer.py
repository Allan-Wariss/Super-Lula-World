import os
import ctypes
import numpy as np
from OpenGL.GL import *
from shader import Shader

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_SHADERS = os.path.join(PASTA_BASE, 'shaders')

class SpriteRenderer:
    # desenha qualquer textura num retângulo (x, y, largura, altura) usando um único quad unitário.
    # serve para os blocos (no mundo) e para o texto (na tela): só muda a matriz de projeção
    def __init__(self):
        self.vertices = np.array([
            0.0, 0.0,  0.0, 0.0,
            1.0, 0.0,  1.0, 0.0,
            1.0, 1.0,  1.0, 1.0,
            0.0, 1.0,  0.0, 1.0,
        ], dtype=np.float32)

        self.faces = np.array([
            0, 1, 2,
            0, 2, 3
        ], dtype=np.uint32)

        self.shader = None
        self.vao = 0
        self.vbo = 0
        self.ebo = 0

    def init(self):
        # shader de "quad texturizado": um retângulo com uma textura, posição e tamanho via uniforms
        self.shader = Shader(os.path.join(PASTA_SHADERS, 'quadTexturizado.vert'),
                             os.path.join(PASTA_SHADERS, 'quadTexturizado.frag'))

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
        glUseProgram(0)

    def comecar(self, projecao):
        # liga shader e VAO uma vez antes de desenhar vários sprites seguidos
        self.shader.usar()
        self.shader.setMat4('uProjecao', projecao)
        glActiveTexture(GL_TEXTURE0)
        glBindVertexArray(self.vao)

    def desenhar(self, texId, x, y, largura, altura):
        self.shader.setVec2('uDeslocamento', x, y)
        self.shader.setVec2('uTamanho', largura, altura)
        glBindTexture(GL_TEXTURE_2D, texId)
        glDrawElements(GL_TRIANGLES, len(self.faces), GL_UNSIGNED_INT, None)

    def terminar(self):
        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)

    def delete(self):
        glDeleteVertexArrays(1, [self.vao])
        glDeleteBuffers(2, [self.vbo, self.ebo])
        self.shader.delete()
