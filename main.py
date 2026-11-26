import glfw
from OpenGL.GL import *
from math import *
from lulaObject import *
from faseObject import *
from camera import *
from texture import *
from spriteRenderer import SpriteRenderer
from textoObject import TextoObject

fase = FaseObject(escala=1)                  # tamanho original da arte (a colisão acompanha a escala)
# posição inicial do Lula acompanha a escala da fase; o tamanho dele não muda
lula = LulaObject(x=60.0 * fase.escala, y=200.0 * fase.escala)

ZOOM = 1.5                                   # câmera 1.5x mais perto que antes (antes mostrava 512 px de altura)
camera = Camera(alturaVisivel=fase.alturaArte / ZOOM)

sprites = SpriteRenderer()                   # desenha blocos e texto
mensagemFase = TextoObject('Passou de fase!')

velocidade = 2.5    # pixels do mundo por update
tecla_c_anterior = False

def init():
    glClearColor(0.0, 0.0, 0.0, 1.0)

    # transparência do PNG
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    sprites.init()
    mensagemFase.init()
    fase.init()                         # shader, VAO/VBO e textura da fase
    lula.init()                         # cria shader, VAO, VBO e carrega os sprites

def reiniciarFase():
    fase.reiniciar()
    lula.reiniciar()
    mensagemFase.visivel = False

def update(window):
    global tecla_c_anterior

    # tecla C liga/desliga a visualização da colisão por cima da arte
    tecla_c = glfw.get_key(window, glfw.KEY_C) == glfw.PRESS
    if tecla_c and not tecla_c_anterior:
        fase.mostrarColisao = not fase.mostrarColisao
    tecla_c_anterior = tecla_c

    # inimigos andando, contato com o Lula e partículas dos blocos quebrados
    fase.atualizar(lula)

    # vida chegou a 0 -> a fase inteira reinicia do começo
    if lula.morto():
        reiniciarFase()

    # encostou na parte amarela -> passou de fase (a transição para a próxima fase entra depois)
    if not mensagemFase.visivel and fase.colideChegada(*lula.hitbox(lula.x, lula.y)):
        mensagemFase.visivel = True


def render(window, alfa):
    # alfa: quanto já passou do próximo update (0 a 1), para desenhar entre o estado anterior e o atual
    larg, alt = glfw.get_framebuffer_size(window)
    if larg == 0 or alt == 0:           # janela minimizada
        return
    glViewport(0, 0, larg, alt)
    camera.ajustarTela(larg, alt)

    # a fase fica parada, quem se move é a câmera atrás do Lula
    # (segue a posição suavizada e alinhada, a mesma usada para desenhar o Lula -> ele não treme)
    lx, ly = lula.posicaoDesenho(alfa)
    camera.seguir(camera.alinhar(lx), camera.alinhar(ly), fase.largura, fase.altura)

    glClear(GL_COLOR_BUFFER_BIT)

    projecao = camera.matrizProjecao()
    fase.draw(projecao, sprites, alfa, camera.alinhar)  # arte + blocos + inimigos (+ colisão no debug)
    lula.draw(projecao, alfa, camera.alinhar)
    mensagemFase.draw(sprites, larg, alt)   # por cima de tudo, em coordenadas da tela

def main():
    glfw.init()

    # pede um contexto OpenGL 3.3 core (necessário para VAO/VBO + GLSL 330)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)

    window = glfw.create_window(1024, 512, 'Super Lula', None, None)
    glfw.make_context_current(window)
    glfw.swap_interval(1)

    init()

    FPS_ALVO = 60.0
    TEMPO_POR_ATUALIZACAO = 1.0 / FPS_ALVO

    last_time = glfw.get_time()
    acumulador = 0.0

    while not glfw.window_should_close(window):
        current_time = glfw.get_time()
        delta_tempo = current_time - last_time
        last_time = current_time

        acumulador += delta_tempo
        glfw.poll_events()

        while acumulador >= TEMPO_POR_ATUALIZACAO:

            # Movimento do Lula (A/D ou setas), pulo (W/↑/espaço), gravidade, colisão e animação
            lula.mover(window=window, fase=fase, velocidade=velocidade)

            update(window)

            acumulador -= TEMPO_POR_ATUALIZACAO

        render(window, acumulador / TEMPO_POR_ATUALIZACAO)
        glfw.swap_buffers(window)

    lula.delete()
    fase.delete()
    mensagemFase.delete()
    sprites.delete()
    glfw.terminate()

if __name__ == '__main__':
    main()
