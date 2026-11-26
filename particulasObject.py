import random
from PIL import Image
from OpenGL.GL import *
from texture import Texture

# tons de marrom dos pedaços de tijolo
CORES_PARTICULAS = [
    (139, 69, 19),
    (160, 82, 45),
    (101, 52, 20),
    (205, 120, 60),
]

class Particula:
    def __init__(self, x, y, vx, vy, tamanho, cor, vida):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.tamanho = tamanho
        self.cor = cor                  # índice em CORES_PARTICULAS
        self.vida = vida                # quantos updates ainda fica na tela

class ParticulasObject:
    # pedaços que voam quando um bloco quebra: cada um é um quadradinho com velocidade e gravidade
    def __init__(self, gravidade=0.4):
        self.gravidade = gravidade
        self.particulas = []
        self.texturas = []              # uma textura 1x1 por cor

    def init(self):
        self.texturas = [Texture(Image.new('RGBA', (1, 1), (*cor, 255))).texId for cor in CORES_PARTICULAS]

    def explodir(self, x, y, largura, altura):
        # 4 pedaços grandes saindo dos cantos (para cima e para os lados) + farelos menores
        cx, cy = x + largura / 2, y + altura / 2
        for lado in (-1, 1):
            for alto in (0, 1):
                self.particulas.append(Particula(
                    cx + lado * largura / 4, cy + (alto - 0.5) * altura / 2,
                    vx=lado * random.uniform(1.0, 2.0),
                    vy=random.uniform(5.0, 7.0) if alto else random.uniform(3.0, 4.5),
                    tamanho=max(3, round(largura / 4)),
                    cor=random.randrange(len(CORES_PARTICULAS)),
                    vida=90))
        for _ in range(10):
            self.particulas.append(Particula(
                random.uniform(x, x + largura), random.uniform(y, y + altura),
                vx=random.uniform(-2.5, 2.5),
                vy=random.uniform(2.0, 6.0),
                tamanho=random.choice((2, 2, 3)),
                cor=random.randrange(len(CORES_PARTICULAS)),
                vida=random.randint(40, 70)))

    def atualizar(self):
        for p in self.particulas:
            p.vy -= self.gravidade
            p.x += p.vx
            p.y += p.vy
            p.vida -= 1
        # some quando o tempo acaba ou cai para baixo da fase
        self.particulas = [p for p in self.particulas if p.vida > 0 and p.y > -20]

    def limpar(self):
        self.particulas = []

    def draw(self, sprites, projecao):
        if not self.particulas:
            return
        sprites.comecar(projecao)
        for p in self.particulas:
            meio = p.tamanho / 2
            sprites.desenhar(self.texturas[p.cor], round(p.x - meio), round(p.y - meio), p.tamanho, p.tamanho)
        sprites.terminar()

    def delete(self):
        if self.texturas:
            glDeleteTextures(self.texturas)
