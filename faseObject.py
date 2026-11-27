import os
import ctypes
import numpy as np
from PIL import Image
from OpenGL.GL import *
from texture import Texture
from shader import Shader
from blocoObject import BlocoObject
from particulasObject import ParticulasObject
from inimigoObject import InimigoObject, retangulosEncostam
from florObject import FlorObject
from lulatronObject import LulatronObject
from bolaDeFogoObject import BolaDeFogoObject

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_TEXTURAS = os.path.join(PASTA_BASE, 'textures')
PASTA_SHADERS = os.path.join(PASTA_BASE, 'shaders')

# cores do mapa de colisão que viram entidades / áreas especiais
COR_BLOCO_MURO = (0x00, 0x4a, 0xad)     # azul  -> blocos de muro
COR_BLOCO_INTERROGACAO = (97, 193, 41)  # verde -> blocos [?]
COR_CHEGADA = (255, 237, 0)             # amarelo -> fim da fase
COR_INIMIGO = (255, 0, 252)             # rosa -> onde nasce um inimigo
COR_BLOCO_LULATRON = (255, 69, 0)       # laranja -> bloco [_] que solta o power-up do Lulatron

# altura de toda fase em pixels do mundo (antes de multiplicar pela escala).
# a arte pode ter qualquer resolução: ela é esticada para esta altura, então trocar a imagem
# por uma versão maior/mais nítida não muda o tamanho do Lula e dos inimigos na tela
ALTURA_MUNDO = 482

def mascaraCor(r, g, b, cor, tolerancia=48):
    return (np.abs(r - cor[0]) < tolerancia) & (np.abs(g - cor[1]) < tolerancia) & (np.abs(b - cor[2]) < tolerancia)

def regioes(mascara, areaMinima=30):
    # separa a máscara em regiões conectadas e devolve o retângulo (x, y, largura, altura) de cada uma.
    # regiões muito pequenas são sobras do antialiasing da imagem e são ignoradas
    visitado = np.zeros(mascara.shape, dtype=bool)
    altura, largura = mascara.shape
    retangulos = []
    for y0, x0 in zip(*np.nonzero(mascara)):
        if visitado[y0, x0]:
            continue
        visitado[y0, x0] = True
        pilha = [(y0, x0)]
        xMin = xMax = x0
        yMin = yMax = y0
        area = 0
        while pilha:
            y, x = pilha.pop()
            area += 1
            xMin, xMax = min(xMin, x), max(xMax, x)
            yMin, yMax = min(yMin, y), max(yMax, y)
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < altura and 0 <= nx < largura and mascara[ny, nx] and not visitado[ny, nx]:
                    visitado[ny, nx] = True
                    pilha.append((ny, nx))
        if area >= areaMinima:
            retangulos.append((int(xMin), int(yMin), int(xMax - xMin + 1), int(yMax - yMin + 1)))
    return retangulos

def preencherComBlocos(tipo, retangulos):
    # cada região vira uma fileira de blocos: quantos blocos cabem é a largura / altura arredondada,
    # e eles são esticados um pouquinho para preencher a região inteira (bordas em pixels inteiros)
    blocos = []
    for x, y, larg, alt in retangulos:
        if larg >= alt:
            n = max(1, round(larg / alt))
            bordas = [round(x + i * larg / n) for i in range(n + 1)]
            for i in range(n):
                blocos.append(BlocoObject(tipo, bordas[i], y, bordas[i + 1] - bordas[i], alt))
        else:
            # região em pé: empilha os blocos na vertical
            n = max(1, round(alt / larg))
            bordas = [round(y + i * alt / n) for i in range(n + 1)]
            for i in range(n):
                blocos.append(BlocoObject(tipo, x, bordas[i], larg, bordas[i + 1] - bordas[i]))
    return blocos

class FaseObject:
    def __init__(self, pasta='fase', imagem='fase-teste.png', colisao='fase-colisao-teste.png', escala=1):
        # pasta dentro de textures/ com a arte e o mapa de colisão desta fase
        self.caminhoImagem = os.path.join(PASTA_TEXTURAS, pasta, imagem)
        self.caminhoColisao = os.path.join(PASTA_TEXTURAS, pasta, colisao)

        # o mundo tem sempre ALTURA_MUNDO de altura (vezes a escala); a largura segue a proporção da arte
        arte = Image.open(self.caminhoImagem)
        self.larguraArte, self.alturaArte = arte.size
        self.escala = escala
        self.altura = ALTURA_MUNDO * escala
        self.largura = round(self.larguraArte * self.altura / self.alturaArte)
        self.artePorMundo = self.alturaArte / self.altura   # pixels da arte por pixel do mundo

        # ---- mapa de colisão ----
        # a imagem de colisão tem o mesmo tamanho da arte; ela é esticada (sem suavizar)
        # para o tamanho do mundo, então continua encaixada na arte em qualquer escala
        alinhada = Image.open(self.caminhoColisao).convert('RGB')
        alinhada = alinhada.resize((self.largura, self.altura), Image.NEAREST)

        mapa = np.array(alinhada).astype(np.int16)
        mapa = mapa[::-1]                   # imagem tem y para baixo, o mundo tem y para cima

        r, g, b = mapa[..., 0], mapa[..., 1], mapa[..., 2]
        preto = (r < 64) & (g < 64) & (b < 64)
        vermelho = (r > 192) & (g < 64) & (b < 64)

        azul = mascaraCor(r, g, b, COR_BLOCO_MURO)
        verde = mascaraCor(r, g, b, COR_BLOCO_INTERROGACAO)
        rosa = mascaraCor(r, g, b, COR_INIMIGO)
        amarelo = mascaraCor(r, g, b, COR_CHEGADA)
        # laranja é parecido com o vermelho (255, 40, 28): tolerância pequena para não confundir
        laranja = mascaraCor(r, g, b, COR_BLOCO_LULATRON, tolerancia=16)

        self.mortal = vermelho
        # o vermelho é sólido (o Lula não atravessa), mas encostar nele mata
        self.solido = preto | vermelho
        # encostar no amarelo termina a fase (não é sólido, o Lula entra nele)
        self.chegada = amarelo

        # ---- entidades: blocos ----
        # o mapa já está com y para cima, então a linha da máscara é o y do mundo
        # as regiões ficam guardadas para recriar os blocos quando a fase reinicia
        self.regioesBlocos = {'muro': regioes(azul), 'interrogacao': regioes(verde),
                              'lulatron': regioes(laranja, areaMinima=10)}
        self.criarBlocos()

        # ---- entidades: inimigos ----
        # cada marca rosa é o lugar (e o tamanho) onde um inimigo nasce
        self.regioesInimigos = regioes(rosa)
        self.criarInimigos()

        # ---- entidades: power-ups e bolas de fogo (surgem durante o jogo) ----
        self.flores = []                # power-ups saindo dos blocos (flores e o Lulatron)
        self.bolasDeFogo = []
        self.maxBolasDeFogo = 2         # no máximo 2 bolas de fogo na tela ao mesmo tempo

        # imagem da colisão para o modo debug (tecla C): semi-transparente por cima da arte
        debug = np.zeros((self.altura, self.largura, 4), dtype=np.uint8)
        debug[preto] = (0, 0, 0, 255)
        debug[vermelho] = (255, 0, 0, 255)
        debug[amarelo] = (255, 237, 0, 255)
        # os blocos não entram nesta imagem fixa: como podem quebrar, são desenhados um a um no debug
        self.imagemDebug = Image.fromarray(debug[::-1], 'RGBA')
        self.mostrarColisao = False

        # ---- arte sem os blocos ----
        # a arte já tem os tijolos pintados; eles são apagados dela (cada linha é preenchida
        # misturando as cores à esquerda e à direita) para que, quando a entidade quebrar,
        # apareça o fundo atrás e não o desenho do bloco
        self.imagemArte = self.apagarBlocosDaArte(arte.convert('RGBA'))

        # pedaços voando quando um bloco quebra
        self.particulas = ParticulasObject()

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
        # cada "pixel" retrô = 2x2 pixels do mundo (3 deixava a arte borrada demais).
        # o shader trabalha em texels: numa arte de resolução maior o bloco tem mais texels
        self.tamanhoBloco = 2.0 * self.artePorMundo
        self.niveisCor = (31.0, 63.0, 31.0) # RGB565

        self.shader = None
        self.vao = 0
        self.vbo = 0
        self.ebo = 0
        self.texId = 0
        self.texDebugId = 0
        self.texDebugBlocos = {}

    def apagarBlocosDaArte(self, arte, margem=2):
        margem = max(1, round(margem * self.artePorMundo))   # margem em pixels da arte
        pixels = np.array(arte).astype(np.float32)
        alturaImg, larguraImg = pixels.shape[:2]
        for retangulos in self.regioesBlocos.values():
            for x, y, larg, alt in retangulos:
                # mundo (y para cima) -> imagem da arte (y para baixo, na resolução dela)
                k = self.artePorMundo
                x0 = max(int(x * k) - margem, 1)
                x1 = min(int((x + larg) * k) + margem, larguraImg - 1)
                topo = max(alturaImg - int((y + alt) * k) - margem, 0)
                baixo = min(alturaImg - int(y * k) + margem, alturaImg)
                esquerda = pixels[topo:baixo, x0 - 1]       # coluna logo antes do bloco
                direita = pixels[topo:baixo, x1]            # coluna logo depois
                t = np.linspace(0.0, 1.0, x1 - x0)[None, :, None]
                pixels[topo:baixo, x0:x1] = esquerda[:, None] * (1 - t) + direita[:, None] * t
        return Image.fromarray(pixels.round().astype(np.uint8), 'RGBA')

    def init(self):
        self.shader = Shader(os.path.join(PASTA_SHADERS, 'fase.vert'),
                             os.path.join(PASTA_SHADERS, 'fase.frag'))

        self.texId = Texture(self.imagemArte).texId
        self.texDebugId = Texture(self.imagemDebug).texId
        BlocoObject.carregarTexturas()
        self.particulas.init()
        InimigoObject.carregarTextura()
        FlorObject.carregarTextura()
        LulatronObject.carregarTextura()
        BolaDeFogoObject.carregarTexturas()
        # quadradinhos semi-transparentes para mostrar a colisão dos blocos no modo debug
        self.texDebugBlocos = {
            'muro': Texture(Image.new('RGBA', (1, 1), (*COR_BLOCO_MURO, 160))).texId,
            'interrogacao': Texture(Image.new('RGBA', (1, 1), (*COR_BLOCO_INTERROGACAO, 160))).texId,
            'lulatron': Texture(Image.new('RGBA', (1, 1), (*COR_BLOCO_LULATRON, 160))).texId,
        }

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
        self.shader.setVec2('uTamanhoTextura', self.larguraArte, self.alturaArte)
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
        if self.areaColide(self.solido, x0, y0, x1, y1):
            return True
        return any(bloco.colide(x0, y0, x1, y1) for bloco in self.blocos)

    def chaoSeguroAbaixo(self, x0, x1, y):
        # descendo a partir da altura y na faixa [x0, x1): a primeira coisa sólida que aparece
        # é chão normal? (vermelho = morte e nada embaixo = buraco sem fundo não contam)
        xa = max(int(np.floor(x0)), 0)
        xb = min(int(np.ceil(x1)), self.largura)
        ya = min(int(np.floor(y)), self.altura)
        if xa >= xb or ya <= 0:
            return False
        linhas = np.nonzero(self.solido[:ya, xa:xb].any(axis=1))[0]
        topoMapa = int(linhas[-1]) if len(linhas) else -1
        topoBlocos = max((b.y + b.altura for b in self.blocos
                          if b.solido and b.x < x1 and b.x + b.largura > x0 and b.y + b.altura <= y),
                         default=-1)
        if topoMapa < 0 and topoBlocos < 0:
            return False
        if topoBlocos > topoMapa:           # um bloco fica acima do chão do mapa: cai em cima dele
            return True
        return not self.mortal[topoMapa, xa:xb].any()

    def colideChegada(self, x0, y0, x1, y1):
        return self.areaColide(self.chegada, x0, y0, x1, y1)

    def drawBlocos(self, sprites, projecao):
        sprites.comecar(projecao)
        for bloco in self.blocos:
            bloco.draw(sprites)
        sprites.terminar()

    def colideMortal(self, x0, y0, x1, y1):
        return self.areaColide(self.mortal, x0, y0, x1, y1)

    def criarBlocos(self):
        self.blocos = []
        for tipo, retangulos in self.regioesBlocos.items():
            self.blocos += preencherComBlocos(tipo, retangulos)

    def criarInimigos(self):
        self.inimigos = [InimigoObject(x, y, larg, alt) for x, y, larg, alt in self.regioesInimigos]

    def reiniciar(self):
        # recria as entidades no estado inicial: os blocos quebrados e os inimigos mortos voltam
        self.criarBlocos()
        self.criarInimigos()
        self.flores = []
        self.bolasDeFogo = []
        self.particulas.limpar()

    def baterCabeca(self, x0, y0, x1, y1):
        # o Lula subiu e bateu a cabeça (topo da caixa = y1): acerta o bloco logo acima dele.
        # se encostar em dois blocos ao mesmo tempo, acerta o que está mais em cima da cabeça.
        # bloco quebrável some; o bloco [?] não quebra, só passa de fechado para aberto
        acima = [b for b in self.blocos
                 if b.x < x1 and b.x + b.largura > x0 and -0.5 <= b.y - y1 <= 1.5]
        if not acima:
            return None
        bloco = max(acima, key=lambda b: min(x1, b.x + b.largura) - max(x0, b.x))
        if bloco.quebravel():
            self.quebrarBloco(bloco)
        elif bloco.abrir():
            # bloco [?] abriu agora: solta o power-up, que sobe de dentro dele
            # (o laranja solta o Lulatron, que é único: o bloco só abre uma vez)
            if bloco.tipo == 'lulatron':
                self.flores.append(LulatronObject(bloco))
            else:
                self.flores.append(FlorObject(bloco))
        return bloco

    def podeLancarBolaDeFogo(self):
        return len(self.bolasDeFogo) < self.maxBolasDeFogo

    def lancarBolaDeFogo(self, x, y, direcao):
        # (x, y) é o centro de onde a bola sai; direcao = 1 (direita) ou -1 (esquerda)
        tamanho = BolaDeFogoObject.TAMANHO
        self.bolasDeFogo.append(BolaDeFogoObject(x - tamanho / 2, y - tamanho / 2, direcao))

    def quebrarBloco(self, bloco):
        self.blocos.remove(bloco)
        self.particulas.explodir(bloco.x, bloco.y, bloco.largura, bloco.altura)

    def ativarInimigos(self, areaVisivel):
        # inimigos que ainda esperam no ponto de spawn surgem quando a câmera chega perto deles
        for inimigo in self.inimigos:
            if not inimigo.ativo and inimigo.pertoDaTela(areaVisivel):
                inimigo.ativar()

    def atualizar(self, lula, areaVisivel):
        self.particulas.atualizar()
        self.ativarInimigos(areaVisivel)
        for inimigo in self.inimigos:
            inimigo.atualizar(self, lula, self.inimigos)
        self.verificarInimigos(lula)
        self.atualizarFlores(lula)
        self.atualizarBolasDeFogo(areaVisivel)
        self.inimigos = [i for i in self.inimigos if not i.removivel()]

    def atualizarFlores(self, lula):
        # Lula encostou no power-up -> pega (flor: vida 2 e bolas de fogo; Lulatron: invencível)
        caixa = lula.hitbox(lula.x, lula.y)
        for flor in list(self.flores):
            flor.atualizar()
            if flor.saiu() and retangulosEncostam(caixa, flor.retangulo()):
                flor.pegar(lula)
                self.flores.remove(flor)

    def atualizarBolasDeFogo(self, areaVisivel):
        esquerda, direita = areaVisivel
        for bola in self.bolasDeFogo:
            bola.atualizar(self)
            if not bola.viva:
                # bateu na parede ou acabaram os quiques: apaga com umas faíscas
                self.particulas.faiscas(bola.x + bola.largura / 2, bola.y + bola.altura / 2, quantidade=5)
                continue
            # saiu da tela: some sem efeito
            if bola.x + bola.largura < esquerda - 16 or bola.x > direita + 16:
                bola.viva = False
                continue
            # encostou num inimigo -> o inimigo morre e a bola some
            for inimigo in self.inimigos:
                if inimigo.ativo and inimigo.vivo and retangulosEncostam(bola.retangulo(), inimigo.retangulo()):
                    inimigo.queimado()
                    self.particulas.explodir(inimigo.x, inimigo.y, inimigo.largura, inimigo.altura, paleta='fogo')
                    bola.viva = False
                    break
        self.bolasDeFogo = [b for b in self.bolasDeFogo if b.viva]

    def verificarInimigos(self, lula):
        # contato do Lula com os inimigos:
        # - caindo e com os pés acima do topo do inimigo no update anterior -> pisoteou, inimigo morre
        # - qualquer outro contato (pelos lados ou por baixo) -> Lula leva 1 de dano
        # - com o Lulatron ativo: qualquer contato mata o inimigo
        x0, y0, x1, y1 = lula.hitbox(lula.x, lula.y)
        # 1 pixel de folga dos lados, para contar também quando só estão encostados
        caixa = (x0 - 1, y0 - 1, x1 + 1, y1)
        pisou = False
        for inimigo in self.inimigos:
            if not inimigo.ativo or not inimigo.vivo or not retangulosEncostam(caixa, inimigo.retangulo()):
                continue
            if lula.temLulatron():
                inimigo.queimado()      # some na hora, explodindo em faíscas
                self.particulas.explodir(inimigo.x, inimigo.y, inimigo.largura, inimigo.altura, paleta='fogo')
                continue
            if lula.vy <= 0 and lula.yAnterior >= inimigo.topo() - 1:
                inimigo.pisoteado()
                pisou = True
            elif not pisou:
                lula.levarDano(1)
        if pisou:
            lula.quicar()

    def draw(self, projecao, sprites, alfa=1.0, alinhar=round):
        self.shader.usar()
        self.shader.setMat4('uProjecao', projecao)

        glActiveTexture(GL_TEXTURE0)
        glBindVertexArray(self.vao)

        # 1. arte da fase com o estilo 16 bits
        self.shader.setInt('uEstilo16bits', 1)
        self.shader.setFloat('uOpacidade', 1.0)
        glBindTexture(GL_TEXTURE_2D, self.texId)
        glDrawElements(GL_TRIANGLES, len(self.faces), GL_UNSIGNED_INT, None)

        # 2. flores (antes dos blocos: enquanto sobem, a parte dentro do bloco fica escondida),
        #    entidades bloco por cima da arte, e os pedaços dos que quebraram
        if self.flores:
            sprites.comecar(projecao)
            for flor in self.flores:
                flor.draw(sprites, alfa, alinhar)
            sprites.terminar()
        self.drawBlocos(sprites, projecao)
        self.particulas.draw(sprites, projecao)

        # inimigos (os que ainda não surgiram não são desenhados)
        sprites.comecar(projecao)
        for inimigo in self.inimigos:
            inimigo.draw(sprites, alfa, alinhar)
        for bola in self.bolasDeFogo:
            bola.draw(sprites, alfa, alinhar)
        sprites.terminar()

        # 3. modo debug: colisão desenhada por cima de tudo, meio transparente
        if self.mostrarColisao:
            self.shader.usar()
            glActiveTexture(GL_TEXTURE0)
            glBindVertexArray(self.vao)
            self.shader.setInt('uEstilo16bits', 0)
            self.shader.setFloat('uOpacidade', 0.5)
            glBindTexture(GL_TEXTURE_2D, self.texDebugId)
            glDrawElements(GL_TRIANGLES, len(self.faces), GL_UNSIGNED_INT, None)

            # blocos que ainda existem
            sprites.comecar(projecao)
            for bloco in self.blocos:
                sprites.desenhar(self.texDebugBlocos[bloco.tipo], bloco.x, bloco.y, bloco.largura, bloco.altura)
            sprites.terminar()

        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)

    def delete(self):
        glDeleteVertexArrays(1, [self.vao])
        glDeleteBuffers(2, [self.vbo, self.ebo])
        glDeleteTextures([self.texId, self.texDebugId, *self.texDebugBlocos.values()])
        BlocoObject.deletarTexturas()
        self.particulas.delete()
        InimigoObject.deletarTextura()
        FlorObject.deletarTextura()
        LulatronObject.deletarTextura()
        BolaDeFogoObject.deletarTexturas()
        self.shader.delete()
