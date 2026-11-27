import os
import math
import ctypes
import numpy as np
from OpenGL.GL import *
import glfw
from PIL import Image, ImageOps
from texture import Texture
from shader import Shader

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
# visual do Lula conforme a vida: 1 = normal, 2 = vermelho (pegou a flor, joga bolas de fogo)
PASTAS_VISUAL = {
    'normal': os.path.join(PASTA_BASE, 'textures', 'Lula', 'lula_walk_sprites_png'),
    'vermelho': os.path.join(PASTA_BASE, 'textures', 'lula_red'),
}
# pose de arremesso (só do vermelho): 192x320, desenho só entre (4, 66) e (188, 254), virado para a direita
ARQUIVO_ARREMESSO = os.path.join(PASTA_BASE, 'textures', 'lula_red', 'powerup_cast_fire.png')
RECORTE_ARREMESSO = (4, 66, 188, 254)
PASTA_SHADERS = os.path.join(PASTA_BASE, 'shaders')

class LulaObject:
    def __init__(self, x=60.0, y=200.0):
        # tudo em pixels do mundo; (x, y) é o meio dos pés do boneco
        self.x = x
        self.y = y
        self.inicioX = x
        self.inicioY = y

        # vida: começa com 1. a flor sobe para 2 (Lula vermelho). inimigo tira 1.
        # encostar no vermelho do mapa zera a vida na hora
        self.vidaInicial = 1
        self.vidaMax = 2
        self.vida = self.vidaInicial
        self.tempoInvencivel = 90   # updates sem levar dano depois de apanhar (1,5 s)
        self.contadorInvencivel = 0
        self.forcaQuique = 8.0      # impulso para cima ao pisar num inimigo
        self.yAnterior = y          # altura no update anterior (para saber se pisou em cima)
        self.xAnterior = x          # posição no update anterior (para desenhar suave entre updates)

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

        # bola de fogo (tecla F, só com o Lula vermelho)
        self.tempoPoseArremesso = 12    # updates mostrando a pose de arremesso depois de jogar
        self.contadorArremesso = 0
        self.tiroPressionadoAntes = False

        # sprites de caminhada têm 192x320 px, então a largura é 0.6 da altura
        alt = 50.0

        # caixa de colisão menor que o desenho (o PNG tem bordas transparentes)
        self.hitMeiaLarg = 9.0
        self.hitAlt = 46.0

        # sprites de pulo têm 1496x2048 px (proporção 0.73) e não têm borda transparente em cima,
        # então ocupam só a altura do boneco (a caixa de colisão) para ficar do mesmo tamanho que andando
        altPulo = self.hitAlt
        self.resolucaoPulo = (70, 96)       # os PNGs de pulo são enormes: reduz antes de virar textura

        # cada vértice: [x, y, u, v] -> tudo intercalado num único VBO.
        # um quad por pose, porque andar e pular têm proporções diferentes
        # a pose de arremesso, recortada, tem 184x188: desenhada com a altura do boneco
        larguraArremesso = RECORTE_ARREMESSO[2] - RECORTE_ARREMESSO[0]
        alturaArremesso = RECORTE_ARREMESSO[3] - RECORTE_ARREMESSO[1]
        altArremesso = self.hitAlt
        self.resolucaoArremesso = (90, 92)
        self.quads = {
            'andar': self.criarQuad(alt * 0.6 / 2, alt),
            'pulo': self.criarQuad(altPulo * 1496 / 2048 / 2, altPulo),
            'arremesso': self.criarQuad(altArremesso * larguraArremesso / alturaArremesso / 2, altArremesso),
        }

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
        self.vaos = {}                  # pose -> VAO
        self.buffers = []               # todos os VBOs/EBOs, para apagar no final
        self.texturas = {}

    def criarQuad(self, meiaLarg, alt):
        # quad com os pés no (0, 0), centralizado em x
        return np.array([
            -meiaLarg, 0.0,  0.0, 0.0,
             meiaLarg, 0.0,  1.0, 0.0,
             meiaLarg, alt,  1.0, 1.0,
            -meiaLarg, alt,  0.0, 1.0,
        ], dtype=np.float32)

    def init(self):
        self.shader = Shader(os.path.join(PASTA_SHADERS, 'lula.vert'),
                             os.path.join(PASTA_SHADERS, 'lula.frag'))

        # texturas[visual][pose][direção] -> lista de frames
        self.texturas = {}
        for visual, pasta in PASTAS_VISUAL.items():
            self.texturas[visual] = {
                'andar': {
                    'direita': self.carregarSprites(pasta, 'walk_right'),
                    'esquerda': self.carregarSprites(pasta, 'walk_left'),
                },
                'pulo': {
                    'direita': self.carregarSprites(pasta, 'jump_right', self.resolucaoPulo),
                    'esquerda': self.carregarSprites(pasta, 'jump_left', self.resolucaoPulo),
                },
            }
        # arremesso: só existe virado para a direita, a esquerda é o espelho
        img = Image.open(ARQUIVO_ARREMESSO).convert('RGBA').crop(RECORTE_ARREMESSO)
        img = img.resize(self.resolucaoArremesso, Image.LANCZOS)
        self.texturas['vermelho']['arremesso'] = {
            'direita': [Texture(img).texId],
            'esquerda': [Texture(ImageOps.mirror(img)).texId],
        }

        for pose, vertices in self.quads.items():
            self.vaos[pose] = self.enviarQuad(vertices)

        self.shader.usar()
        self.shader.setInt('uTextura', 0)   # sampler lê da unidade de textura 0
        glUseProgram(0)

    def enviarQuad(self, vertices):
        vao = glGenVertexArrays(1)          # VAO guarda toda a configuração dos atributos
        vbo = glGenBuffers(1)               # VBO com posições + uvs
        ebo = glGenBuffers(1)               # EBO com os índices das faces
        self.buffers += [vbo, ebo]

        glBindVertexArray(vao)

        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.faces.nbytes, self.faces, GL_STATIC_DRAW)

        stride = 4 * vertices.itemsize      # 4 floats por vértice

        # location 0 -> aPosicao (x, y)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        # location 1 -> aUV (u, v), começa depois dos 2 floats da posição
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(2 * vertices.itemsize))
        glEnableVertexAttribArray(1)

        glBindVertexArray(0)                # o EBO fica gravado no VAO, então desativa o VAO primeiro
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        return vao

    def carregarSprites(self, pastaVisual, pasta, resolucao=None):
        caminho = os.path.join(pastaVisual, pasta)
        arquivos = sorted(f for f in os.listdir(caminho) if f.endswith('.png'))
        texIds = []
        for f in arquivos:
            img = Image.open(os.path.join(caminho, f)).convert('RGBA')
            if resolucao:
                img = img.resize(resolucao, Image.LANCZOS)
            texIds.append(Texture(img).texId)
        return texIds

    def mover(self, window, fase, velocidade=2.5):
        self.xAnterior = self.x
        self.yAnterior = self.y
        if self.contadorInvencivel > 0:
            self.contadorInvencivel -= 1

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
        if bateu and self.vy > 0:
            # bateu a cabeça subindo: se for um bloco, ele quebra
            fase.baterCabeca(*self.hitbox(self.x, self.y))
        if bateu:
            self.noChao = self.vy < 0
            self.vy = 0.0
        else:
            self.noChao = False

        # encostou no vermelho (caixa de colisão com 1 pixel de folga, para contar
        # também quando está só pisando ou encostado do lado) -> morre
        x0, y0, x1, y1 = self.hitbox(self.x, self.y)
        if fase.colideMortal(x0 - 1, y0 - 1, x1 + 1, y1 + 1):
            self.vida = 0

        # caiu para fora da fase -> também morre
        if self.y < -100:
            self.vida = 0

        # 4. bola de fogo: só no momento em que aperta F, e só com o Lula vermelho
        tiro = glfw.get_key(window, glfw.KEY_F) == glfw.PRESS
        if self.contadorArremesso > 0:
            self.contadorArremesso -= 1
        if tiro and not self.tiroPressionadoAntes and self.temPoder() and fase.podeLancarBolaDeFogo():
            lado = 1 if self.direcao == 'direita' else -1
            # sai da altura da mão, um pouco à frente do corpo
            fase.lancarBolaDeFogo(self.x + lado * (self.hitMeiaLarg + 4), self.y + self.hitAlt * 0.55, lado)
            self.contadorArremesso = self.tempoPoseArremesso
        self.tiroPressionadoAntes = tiro

        # só anima a caminhada com os pés no chão
        self.andando = dx != 0.0 and self.noChao
        self.animar()

    def morto(self):
        return self.vida <= 0

    def temPoder(self):
        # com 2 de vida o Lula está vermelho e pode jogar bolas de fogo
        return self.vida >= 2

    def visual(self):
        return 'vermelho' if self.temPoder() else 'normal'

    def pegarPoder(self):
        # pegou a flor: vida 2 (se já tinha, continua 2)
        self.vida = self.vidaMax

    def levarDano(self, dano):
        # depois de apanhar fica invencível um tempo (piscando), para não perder várias vidas de uma vez.
        # com 2 de vida, apanhar volta para 1: perde o poder e os sprites voltam ao normal
        if self.contadorInvencivel > 0 or self.morto():
            return
        self.vida = max(0, self.vida - dano)
        self.contadorInvencivel = self.tempoInvencivel
        self.contadorArremesso = 0

    def quicar(self):
        # pisou num inimigo: pula de novo (segurando o pulo vai mais alto, igual ao pulo normal)
        self.vy = self.forcaQuique
        self.noChao = False

    def reiniciar(self):
        # volta ao estado do começo da fase
        self.x, self.y = self.inicioX, self.inicioY
        self.vy = 0.0
        self.noChao = False
        self.contadorCoyote = 0
        self.puloPressionadoAntes = False
        self.direcao = 'direita'
        self.andando = False
        self.frameAtual = 0
        self.contadorFrames = 0
        self.vida = self.vidaInicial
        self.contadorInvencivel = 0
        self.contadorArremesso = 0
        self.tiroPressionadoAntes = False
        self.xAnterior = self.x
        self.yAnterior = self.y

    def posicaoDesenho(self, alfa):
        # a lógica roda a 60 updates/s, mas a tela pode desenhar mais quadros (ex.: monitor de 144 Hz).
        # entre dois updates, desenha o Lula no meio do caminho entre a posição anterior e a atual
        return (self.xAnterior + (self.x - self.xAnterior) * alfa,
                self.yAnterior + (self.y - self.yAnterior) * alfa)

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
            self.frameAtual = (self.frameAtual + 1) % len(self.texturas[self.visual()]['andar'][self.direcao])

    def poseAtual(self):
        # logo depois de jogar uma bola de fogo mostra a pose de arremesso.
        # no ar (pulando ou caindo) usa o sprite de pulo; a direção é sempre a última tecla apertada,
        # então virar no meio do pulo troca o sprite para o outro lado na hora
        if self.contadorArremesso > 0 and self.temPoder():
            return 'arremesso'
        return 'andar' if self.noChao else 'pulo'

    def draw(self, projecao, alfa, alinhar):
        # invencível depois de levar dano: pisca (some 4 updates a cada 8)
        if self.contadorInvencivel > 0 and (self.contadorInvencivel // 4) % 2 == 1:
            return
        self.shader.usar()
        self.shader.setMat4('uProjecao', projecao)
        # posição suavizada entre updates e alinhada na grade de pixels da tela
        x, y = self.posicaoDesenho(alfa)
        self.shader.setVec2('uDeslocamento', alinhar(x), alinhar(y))

        pose = self.poseAtual()
        frames = self.texturas[self.visual()][pose][self.direcao]
        frame = self.frameAtual if pose == 'andar' else 0

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, frames[frame % len(frames)])

        glBindVertexArray(self.vaos[pose])
        glDrawElements(GL_TRIANGLES, len(self.faces), GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)

    def delete(self):
        glDeleteVertexArrays(len(self.vaos), list(self.vaos.values()))
        glDeleteBuffers(len(self.buffers), self.buffers)
        for porPose in self.texturas.values():
            for porDirecao in porPose.values():
                for texIds in porDirecao.values():
                    glDeleteTextures(texIds)
        self.shader.delete()
