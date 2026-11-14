import glfw
from OpenGL.GL import *
from math import *
from lulaObject import *
from faseObject import *
from camera import *
from texture import *

fase = FaseObject()
lula = LulaObject()
camera = Camera(alturaVisivel=fase.altura)   # a tela mostra a fase inteira na vertical

velocidade = 2.5    # pixels do mundo por update
tecla_c_anterior = False

def init():
    glClearColor(0.0, 0.0, 0.0, 1.0)

    # transparência do PNG
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    fase.init()                         # shader, VAO/VBO e textura da fase
    lula.init()                         # cria shader, VAO, VBO e carrega os sprites

def update(window):
    global tecla_c_anterior

    # tecla C liga/desliga a visualização da colisão por cima da arte
    tecla_c = glfw.get_key(window, glfw.KEY_C) == glfw.PRESS
    if tecla_c and not tecla_c_anterior:
        fase.mostrarColisao = not fase.mostrarColisao
    tecla_c_anterior = tecla_c

    # a fase fica parada, quem se move é a câmera atrás do Lula
    camera.seguir(lula.x, fase.largura)

def render(window):
    larg, alt = glfw.get_framebuffer_size(window)
    if larg == 0 or alt == 0:           # janela minimizada
        return
    glViewport(0, 0, larg, alt)
    camera.ajustarTela(larg, alt)

    glClear(GL_COLOR_BUFFER_BIT)

    projecao = camera.matrizProjecao()
    fase.draw(projecao)
    lula.draw(projecao)

def main():
    glfw.init()

    # pede um contexto OpenGL 3.3 core (necessário para VAO/VBO + GLSL 330)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)

    # altura = altura da fase -> 1 pixel da fase = 1 pixel da tela (sem borrar)
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

        render(window)
        glfw.swap_buffers(window)

    lula.delete()
    fase.delete()
    glfw.terminate()

if __name__ == '__main__':
    main()
