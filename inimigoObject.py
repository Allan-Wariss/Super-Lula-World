import math
from PIL import Image
from OpenGL.GL import *
from texture import Texture

COR_INIMIGO = (255, 0, 252)         # rosa: mesma cor que marca o spawn no mapa de colisão

class InimigoObject:
    # inimigo que anda de um lado para o outro. ainda sem sprite: é desenhado como um bloco rosa.
    # (x, y) é o canto inferior esquerdo, em pixels do mundo (y para cima)
    textura = 0                     # compartilhada por todos os inimigos

    def __init__(self, x, y, largura, altura, velocidade=1.0):
        self.x = float(x)
        self.y = float(y)
        self.largura = largura
        self.altura = altura
        self.velocidade = velocidade
        self.direcao = -1           # começa andando para a esquerda
        self.vy = 0.0
        self.gravidade = 0.5
        self.velQuedaMax = 10.0
        self.vivo = True
        self.tempoEsmagado = 0
        self.xAnterior = self.x     # posição no update anterior (para desenhar suave entre updates)
        self.yAnterior = self.y      # depois de pisoteado fica achatado um tempinho e some

    @classmethod
    def carregarTextura(cls):
        cls.textura = Texture(Image.new('RGBA', (1, 1), (*COR_INIMIGO, 255))).texId

    @classmethod
    def deletarTextura(cls):
        if cls.textura:
            glDeleteTextures([cls.textura])
            cls.textura = 0

    def retangulo(self, x=None, y=None):
        x = self.x if x is None else x
        y = self.y if y is None else y
        return (x, y, x + self.largura, y + self.altura)

    def topo(self):
        return self.y + self.altura

    def atualizar(self, fase, lula, outros):
        self.xAnterior, self.yAnterior = self.x, self.y
        if not self.vivo:
            self.tempoEsmagado -= 1
            return

        # 1. anda na horizontal, um pixel por vez; bateu em parede, bloco, jogador
        #    ou outro inimigo -> vira para o lado oposto
        passos = math.ceil(self.velocidade)
        passo = self.velocidade / passos * self.direcao
        for _ in range(passos):
            proximo = self.retangulo(x=self.x + passo)
            if self.bloqueado(proximo, fase, lula, outros):
                self.direcao = -self.direcao
                break
            self.x += passo

        # 2. gravidade: cai até encostar no chão (pode cair de beiradas)
        self.vy = max(self.vy - self.gravidade, -self.velQuedaMax)
        passos = max(1, math.ceil(abs(self.vy)))
        passo = self.vy / passos
        for _ in range(passos):
            if fase.colideSolido(*self.retangulo(y=self.y + passo)):
                if passo < 0:
                    self.y = math.floor(self.y)     # cola no chão
                self.vy = 0.0
                break
            self.y += passo

        # caiu para fora da fase
        if self.y < -100:
            self.vivo = False
            self.tempoEsmagado = 0

    def bloqueado(self, ret, fase, lula, outros):
        x0, y0, x1, y1 = ret
        if x0 < 0 or x1 > fase.largura:
            return True
        if fase.colideSolido(x0, y0, x1, y1):
            return True
        if retangulosEncostam(ret, lula.hitbox(lula.x, lula.y)):
            return True
        return any(o is not self and o.vivo and retangulosEncostam(ret, o.retangulo()) for o in outros)

    def pisoteado(self):
        self.vivo = False
        self.tempoEsmagado = 20

    def removivel(self):
        return not self.vivo and self.tempoEsmagado <= 0

    def draw(self, sprites, alfa, alinhar):
        # suavizado entre updates e alinhado na grade de pixels da tela (igual ao Lula)
        x = alinhar(self.xAnterior + (self.x - self.xAnterior) * alfa)
        y = alinhar(self.yAnterior + (self.y - self.yAnterior) * alfa)
        if self.vivo:
            sprites.desenhar(self.textura, x, y, self.largura, self.altura)
        elif self.tempoEsmagado > 0:
            # achatado: um terço da altura
            sprites.desenhar(self.textura, x, y, self.largura, max(2, self.altura // 3))

def retangulosEncostam(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]
