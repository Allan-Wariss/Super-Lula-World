import os
import math
from PIL import Image
from OpenGL.GL import *
from texture import Texture, pixelArt

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_MINION = os.path.join(PASTA_BASE, 'textures', 'minion')

# os PNGs têm 192x320, mas só a parte de baixo (192x224) tem desenho: recorta o espaço vazio de cima
RECORTE_SPRITE = (0, 96, 192, 320)

# tamanho do desenho no mundo: ~2/3 da altura do Lula (50 px).
# a textura é reduzida para EXATAMENTE este tamanho, então 1 pixel da arte = 1 pixel do mundo,
# a mesma densidade de pixels do sprite do Lula (senão o minion fica com pixels bem menores)
ALTURA_SPRITE = 32
LARGURA_SPRITE = round(ALTURA_SPRITE * 192 / 224)   # 27, mantém a proporção do desenho

# caixa de colisão um pouco menor que o desenho (os braços abertos não contam)
LARGURA_HITBOX = 22
ALTURA_HITBOX = 29

# o inimigo só passa a existir no mundo quando o ponto de spawn chega a esta distância
# da borda da tela: ainda fora do enquadramento, para não parecer que surgiu do nada
DISTANCIA_SPAWN = 64

TICKS_POR_FRAME = 10                # troca o passo a cada 10 updates (6 passos por segundo)

class InimigoObject:
    # minion que anda de um lado para o outro.
    # (x, y) é o canto inferior esquerdo da caixa de colisão, em pixels do mundo
    texturas = []                   # frames da caminhada, compartilhados por todos os inimigos

    def __init__(self, x, y, largura, altura, velocidade=1.0):
        # (x, y, largura, altura) é a marca rosa do mapa: o minion nasce centralizado nela, pelos pés
        self.largura = LARGURA_HITBOX
        self.altura = ALTURA_HITBOX
        self.x = float(x + (largura - self.largura) / 2)
        self.y = float(y)
        self.velocidade = velocidade
        self.direcao = -1           # começa andando para a esquerda
        self.vy = 0.0
        self.gravidade = 0.5
        self.velQuedaMax = 10.0
        self.noChao = False         # só evita beiradas quando está andando no chão
        self.vivo = True
        self.tempoEsmagado = 0      # depois de pisoteado fica achatado um tempinho e some
        self.xAnterior = self.x     # posição no update anterior (para desenhar suave entre updates)
        self.yAnterior = self.y
        self.frameAtual = 0         # animação de andar (2 sprites)
        self.contadorFrames = 0
        # antes de ativar o inimigo só "espera" no ponto de spawn: não anda, não cai,
        # não colide e não é desenhado
        self.ativo = False

    @classmethod
    def carregarTextura(cls):
        arquivos = sorted(f for f in os.listdir(PASTA_MINION) if f.endswith('.png'))
        cls.texturas = []
        for arquivo in arquivos:
            img = Image.open(os.path.join(PASTA_MINION, arquivo)).convert('RGBA')
            img = pixelArt(img.crop(RECORTE_SPRITE), (LARGURA_SPRITE, ALTURA_SPRITE))
            cls.texturas.append(Texture(img).texId)

    @classmethod
    def deletarTextura(cls):
        if cls.texturas:
            glDeleteTextures(cls.texturas)
            cls.texturas = []

    def retangulo(self, x=None, y=None):
        x = self.x if x is None else x
        y = self.y if y is None else y
        return (x, y, x + self.largura, y + self.altura)

    def topo(self):
        return self.y + self.altura

    def pertoDaTela(self, areaVisivel):
        esquerda, direita = areaVisivel
        return self.x + self.largura > esquerda - DISTANCIA_SPAWN and self.x < direita + DISTANCIA_SPAWN

    def ativar(self):
        # surge parado no ponto de spawn, com velocidade vertical zero:
        # se não tiver chão embaixo, a gravidade do próximo update já o faz cair
        self.ativo = True
        self.vy = 0.0
        self.xAnterior, self.yAnterior = self.x, self.y

    def atualizar(self, fase, lula, outros):
        if not self.ativo:
            return
        self.xAnterior, self.yAnterior = self.x, self.y
        if not self.vivo:
            self.tempoEsmagado -= 1
            return

        # 1. anda na horizontal, um pixel por vez; bateu em parede, bloco, jogador
        #    ou outro inimigo -> vira para o lado oposto.
        #    beirada: só cai se embaixo tiver chão normal; se for cair no vermelho ou num buraco, vira
        passos = math.ceil(self.velocidade)
        passo = self.velocidade / passos * self.direcao if passos else 0.0
        for _ in range(passos):
            proximo = self.retangulo(x=self.x + passo)
            if self.bloqueado(proximo, fase, lula, outros) or (self.noChao and self.beiradaPerigosa(proximo, fase)):
                self.direcao = -self.direcao
                break
            self.x += passo

        # 2. gravidade: cai até encostar no chão (só cai de beiradas que dão em chão normal)
        self.vy = max(self.vy - self.gravidade, -self.velQuedaMax)
        passos = max(1, math.ceil(abs(self.vy)))
        passo = self.vy / passos
        self.noChao = False
        for _ in range(passos):
            if fase.colideSolido(*self.retangulo(y=self.y + passo)):
                if passo < 0:
                    self.y = math.floor(self.y)     # cola no chão
                    self.noChao = True
                self.vy = 0.0
                break
            self.y += passo

        # caiu para fora da fase
        if self.y < -100:
            self.vivo = False
            self.tempoEsmagado = 0

        # animação: alterna os 2 sprites enquanto anda
        self.contadorFrames += 1
        if self.contadorFrames >= TICKS_POR_FRAME:
            self.contadorFrames = 0
            self.frameAtual = (self.frameAtual + 1) % len(self.texturas)

    def bloqueado(self, ret, fase, lula, outros):
        x0, y0, x1, y1 = ret
        if x0 < 0 or x1 > fase.largura:
            return True
        if fase.colideSolido(x0, y0, x1, y1):
            return True
        if retangulosEncostam(ret, lula.hitbox(lula.x, lula.y)):
            return True
        return any(o is not self and o.ativo and o.vivo and retangulosEncostam(ret, o.retangulo()) for o in outros)

    def beiradaPerigosa(self, ret, fase):
        # na próxima posição não sobra chão nenhum embaixo dos pés -> ia cair.
        # é perigosa se o que tem lá embaixo é o vermelho (morte) ou um buraco sem fundo
        x0, y0, x1, _ = ret
        if fase.colideSolido(x0, y0 - 1, x1, y0):
            return False
        return not fase.chaoSeguroAbaixo(x0, x1, y0)

    def queimado(self):
        # acertado por uma bola de fogo: some na hora (as partículas ficam por conta da fase)
        self.vivo = False
        self.tempoEsmagado = 0

    def pisoteado(self):
        self.vivo = False
        self.tempoEsmagado = 20

    def removivel(self):
        return not self.vivo and self.tempoEsmagado <= 0

    def draw(self, sprites, alfa, alinhar):
        if not self.ativo:
            return
        # suavizado entre updates e alinhado na grade de pixels da tela (igual ao Lula)
        x = alinhar(self.xAnterior + (self.x - self.xAnterior) * alfa)
        y = alinhar(self.yAnterior + (self.y - self.yAnterior) * alfa)
        # desenho centralizado na caixa de colisão, com os pés na base dela
        x = alinhar(x + (self.largura - LARGURA_SPRITE) / 2)
        textura = self.texturas[self.frameAtual]
        if self.vivo:
            sprites.desenhar(textura, x, y, LARGURA_SPRITE, ALTURA_SPRITE)
        elif self.tempoEsmagado > 0:
            # achatado: um terço da altura
            sprites.desenhar(textura, x, y, LARGURA_SPRITE, ALTURA_SPRITE // 3)

def retangulosEncostam(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]
