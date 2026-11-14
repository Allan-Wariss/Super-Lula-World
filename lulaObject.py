import os
import math
import ctypes
import numpy as np
from OpenGL.GL import *
import glfw
from texture import Texture
from shader import Shader

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_SPRITES = os.path.join(PASTA_BASE, 'textures', 'Lula', 'lula_walk_sprites_png')
PASTA_SHADERS = os.path.join(PASTA_BASE, 'shaders')

class LulaObject:
    def __init__(self, x=60.0, y=200.0):
        # tudo em pixels do mundo; (x, y) é o meio dos pés do boneco
        self.x = x
        self.y = y
        self.inicioX = x
        self.inicioY = y

        # física
        self.vy = 0.0
        self.gravidade = 0.5        # pixels por update²
        self.velQuedaMax = 10.0     # velocidade terminal
        self.noChao = False

        # pulo
        self.forcaPulo = 11.0       # velocidade inicial pra cima (~120 px de altura máxima)
        self.cortePulo = 0.5        # soltar o botão no meio da subida corta a velocidade -> pulo mais baixo
        self.tempoCoyote = 6        # updates em que ainda dá para pular logo depois de sair de uma beirada
        self.contadorCoyote = 0
        self.puloPressionadoAntes = False

        # sprites têm 192x320 px, então a largura é 0.6 da altura
        alt = 50.0
        meiaLarg = alt * 0.6 / 2

        # caixa de colisão menor que o desenho (o PNG tem bordas transparentes)
        self.hitMeiaLarg = 9.0
        self.hitAlt = 46.0

        # cada vértice: [x, y, u, v] -> tudo intercalado num único VBO
        self.vertices = np.array([
            -meiaLarg, 0.0,  0.0, 0.0,
             meiaLarg, 0.0,  1.0, 0.0,
             meiaLarg, alt,  1.0, 1.0,
            -meiaLarg, alt,  0.0, 1.0,
        ], dtype=np.float32)

        self.faces = np.array([
            0, 1, 2,
            0, 2, 3
        ], dtype=np.uint32)

        # animação
        self.direcao = 'direita'
        self.andando = False
        self.frameAtual = 0
        self.contadorFrames = 0
        self.ticksPorFrame = 6      # troca de sprite a cada 6 updates (60/6 = 10 sprites por segundo)

        # só podem ser criados depois do contexto OpenGL existir -> init()
        self.shader = None
        self.vao = 0
        self.vbo = 0
        self.ebo = 0
        self.texturas = {}

    def init(self):
        self.shader = Shader(os.path.join(PASTA_SHADERS, 'lula.vert'),
                             os.path.join(PASTA_SHADERS, 'lula.frag'))

        self.texturas = {
            'direita': self.carregarSprites('walk_right'),
            'esquerda': self.carregarSprites('walk_left'),
        }

        self.vao = glGenVertexArrays(1)     # VAO guarda toda a configuração dos atributos
        self.vbo = glGenBuffers(1)          # VBO com posições + uvs
        self.ebo = glGenBuffers(1)          # EBO com os índices das faces

        glBindVertexArray(self.vao)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.faces.nbytes, self.faces, GL_STATIC_DRAW)

        stride = 4 * self.vertices.itemsize  # 4 floats por vértice

        # location 0 -> aPosicao (x, y)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        # location 1 -> aUV (u, v), começa depois dos 2 floats da posição
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(2 * self.vertices.itemsize))
        glEnableVertexAttribArray(1)

        glBindVertexArray(0)                # o EBO fica gravado no VAO, então desativa o VAO primeiro
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        self.shader.usar()
        self.shader.setInt('uTextura', 0)   # sampler lê da unidade de textura 0
        glUseProgram(0)

    def carregarSprites(self, pasta):
        caminho = os.path.join(PASTA_SPRITES, pasta)
        arquivos = sorted(f for f in os.listdir(caminho) if f.endswith('.png'))
        return [Texture(os.path.join(caminho, f)).texId for f in arquivos]

    def mover(self, window, fase, velocidade=2.5):
        esquerda = glfw.get_key(window, glfw.KEY_A) == glfw.PRESS or glfw.get_key(window, glfw.KEY_LEFT) == glfw.PRESS
        direita = glfw.get_key(window, glfw.KEY_D) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT) == glfw.PRESS

        dx = 0.0
        if esquerda and not direita:
            self.direcao = 'esquerda'
            dx = -velocidade
        elif direita and not esquerda:
            self.direcao = 'direita'
            dx = velocidade

        # 1. eixo X: anda até encostar numa parede
        self.moverEixo(fase, dx, 0.0)
        self.x = max(self.hitMeiaLarg, min(self.x, fase.largura - self.hitMeiaLarg))

        # 2. pulo (W, seta para cima ou espaço)
        pulo = (glfw.get_key(window, glfw.KEY_W) == glfw.PRESS or
                glfw.get_key(window, glfw.KEY_UP) == glfw.PRESS or
                glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS)

        if self.noChao:
            self.contadorCoyote = self.tempoCoyote
        elif self.contadorCoyote > 0:
            self.contadorCoyote -= 1

        # só pula no momento em que aperta (segurar o botão não fica pulando sozinho)
        if pulo and not self.puloPressionadoAntes and self.contadorCoyote > 0:
            self.vy = self.forcaPulo
            self.contadorCoyote = 0
        # soltou o botão ainda subindo -> pulo curto
        if not pulo and self.vy > 0:
            self.vy *= self.cortePulo
        self.puloPressionadoAntes = pulo

        # 3. eixo Y: gravidade puxa para baixo até encostar no chão (ou bater a cabeça)
        self.vy = max(self.vy - self.gravidade, -self.velQuedaMax)
        bateu = self.moverEixo(fase, 0.0, self.vy)
        if bateu:
            self.noChao = self.vy < 0
            self.vy = 0.0
        else:
            self.noChao = False

        # caiu para fora da fase -> volta para o início
        if self.y < -100:
            self.x, self.y, self.vy = self.inicioX, self.inicioY, 0.0

        # só anima a caminhada com os pés no chão (sem sprite de pulo por enquanto)
        self.andando = dx != 0.0 and self.noChao
        self.animar()

    def hitbox(self, x, y):
        return (x - self.hitMeiaLarg, y, x + self.hitMeiaLarg, y + self.hitAlt)

    def moverEixo(self, fase, dx, dy):
        # anda em passos de no máximo 1 pixel para não atravessar plataformas finas
        distancia = abs(dx) + abs(dy)
        if distancia == 0:
            return False
        passos = math.ceil(distancia)
        px, py = dx / passos, dy / passos

        for _ in range(passos):
            if fase.colideSolido(*self.hitbox(self.x + px, self.y + py)):
                self.encostar(fase, px, py)
                return True
            self.x += px
            self.y += py
        return False

    def encostar(self, fase, px, py):
        # completa o pedaço de pixel que falta para ficar colado no obstáculo
        if px > 0:
            x = math.ceil(self.x + self.hitMeiaLarg) - self.hitMeiaLarg
        elif px < 0:
            x = math.floor(self.x - self.hitMeiaLarg) + self.hitMeiaLarg
        else:
            x = self.x
        if py < 0:
            y = math.floor(self.y)
        elif py > 0:
            y = math.ceil(self.y + self.hitAlt) - self.hitAlt
        else:
            y = self.y
        if not fase.colideSolido(*self.hitbox(x, y)):
            self.x, self.y = x, y

    def animar(self):
        if not self.andando:
            # parado: volta para o primeiro sprite da direção atual
            self.frameAtual = 0
            self.contadorFrames = 0
            return

        self.contadorFrames += 1
        if self.contadorFrames >= self.ticksPorFrame:
            self.contadorFrames = 0
            self.frameAtual = (self.frameAtual + 1) % len(self.texturas[self.direcao])

    def draw(self, projecao):
        self.shader.usar()
        self.shader.setMat4('uProjecao', projecao)
        # posição arredondada para o sprite cair certinho na grade de pixels
        self.shader.setVec2('uDeslocamento', round(self.x), round(self.y))

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texturas[self.direcao][self.frameAtual])

        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, len(self.faces), GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)

    def delete(self):
        glDeleteVertexArrays(1, [self.vao])
        glDeleteBuffers(2, [self.vbo, self.ebo])
        for texIds in self.texturas.values():
            glDeleteTextures(texIds)
        self.shader.delete()
