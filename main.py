import os
import glfw
from just_playback import Playback
from OpenGL.GL import *
from math import *
from lulaObject import *
from faseObject import *
from camera import *
from texture import *
from spriteRenderer import SpriteRenderer
from textoObject import TextoObject
from salvamento import carregarFase, salvarFase

# fases em ordem: pasta dentro de textures/, arte e mapa de colisão (a zona amarela marca o fim)
FASES = [
    {'pasta': 'fase', 'imagem': 'fase-teste.png', 'colisao': 'fase-colisao-teste.png'},
    {'pasta': 'fase2', 'imagem': 'fase2.png', 'colisao': 'fase2-colisao.png'},
]

# continua da fase salva (morrer sempre volta para o começo da fase atual)
faseAtual = carregarFase(len(FASES))
fase = FaseObject(**FASES[faseAtual], escala=1)  # tamanho original da arte (a colisão acompanha a escala)
# posição inicial do Lula acompanha a escala da fase; o tamanho dele não muda
lula = LulaObject(x=60.0 * fase.escala, y=200.0 * fase.escala)

ZOOM = 1.5                                   # câmera 1.5x mais perto que antes (antes mostrava 512 px de altura)
camera = Camera(alturaVisivel=fase.altura / ZOOM)

sprites = SpriteRenderer()                   # desenha blocos e texto
mensagemFase = TextoObject('Passou de fase!')

velocidade = 2.5    # pixels do mundo por update

# música de fundo (just_playback: biblioteca só de tocar áudio)
ARQUIVO_MUSICA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'songs', 'BackGroundSong.mp3')
VOLUME_MUSICA = 0.05    # bem baixo, só de fundo (0 a 1)
musica = None
# música do Lulatron: enquanto o power-up dura, a música normal pausa e esta toca
ARQUIVO_MUSICA_LULATRON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'songs', 'lulatron.mp3')
musicaLulatron = None
tocandoLulatron = False
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

def iniciarAudio():
    global musica, musicaLulatron
    try:
        musica = Playback()
        musica.load_file(ARQUIVO_MUSICA)
        musica.set_volume(VOLUME_MUSICA)
        musica.loop_at_end(True)        # ao chegar no fim, volta para o começo
    except Exception as erro:           # sem placa de som / arquivo faltando: o jogo roda mudo
        print('Sem áudio:', erro)
        musica = None
    try:
        musicaLulatron = Playback()
        musicaLulatron.load_file(ARQUIVO_MUSICA_LULATRON)
        musicaLulatron.set_volume(VOLUME_MUSICA)
        musicaLulatron.loop_at_end(True)
    except Exception as erro:
        print('Sem música do Lulatron:', erro)
        musicaLulatron = None
    tocarMusica()

def atualizarMusicaLulatron():
    # começou o Lulatron: pausa a música normal (guarda onde parou) e toca a dele do começo.
    # acabou: para a dele e a normal continua de onde estava
    global tocandoLulatron
    if lula.temLulatron() and not tocandoLulatron:
        tocandoLulatron = True
        if musica:
            musica.pause()
        if musicaLulatron:
            musicaLulatron.stop()
            musicaLulatron.play()
    elif not lula.temLulatron() and tocandoLulatron:
        tocandoLulatron = False
        if musicaLulatron:
            musicaLulatron.stop()
        if musica:
            musica.resume()

def tocarMusica():
    # do começo (stop volta a posição para 0)
    if musica:
        musica.stop()
        musica.play()

def pararMusica():
    # para tudo (inclusive a do Lulatron): usado na morte
    global tocandoLulatron
    tocandoLulatron = False
    if musica:
        musica.stop()
    if musicaLulatron:
        musicaLulatron.stop()

def areaVisivel():
    # saindo da fase a câmera fica parada: a área visível é onde ela parou
    if lula.saindoDaFase:
        return camera.x, camera.x + camera.larguraVisivel
    # o que a câmera mostra seguindo o Lula agora (calculado direto da posição dele,
    # então funciona igual mesmo logo depois de reiniciar, antes do próximo desenho)
    return camera.areaVisivelX(lula.x, fase.largura)

def reiniciarFase():
    fase.reiniciar()
    lula.reiniciar()
    mensagemFase.visivel = False
    fase.ativarInimigos(areaVisivel())  # os que já estão na tela do começo fazem parte da cena inicial
    tocarMusica()                       # a música recomeça junto com a fase

def irParaProximaFase(window):
    # troca a fase inteira (arte, colisão, blocos, inimigos) pela próxima e salva o progresso.
    # depois da última fase o jogo volta para a primeira
    global fase, faseAtual
    faseAtual = (faseAtual + 1) % len(FASES)
    salvarFase(faseAtual)

    fase.delete()                       # libera as texturas/buffers da fase que acabou
    fase = FaseObject(**FASES[faseAtual], escala=1)
    fase.init()

    # a câmera mostra a altura do mundo da nova fase (com o mesmo zoom)
    camera.alturaVisivel = fase.altura / ZOOM
    larg, alt = glfw.get_framebuffer_size(window)
    if larg > 0 and alt > 0:
        camera.ajustarTela(larg, alt)

    lula.reiniciar(manterVida=True)     # passou de fase: continua com o poder que tinha
    mensagemFase.visivel = False
    fase.ativarInimigos(areaVisivel())

def update(window):
    # devolve True quando carregou uma fase nova (o loop principal descarta o tempo gasto carregando)
    global tecla_c_anterior

    # tecla C liga/desliga a visualização da colisão por cima da arte
    tecla_c = glfw.get_key(window, glfw.KEY_C) == glfw.PRESS
    if tecla_c and not tecla_c_anterior:
        fase.mostrarColisao = not fase.mostrarColisao
    tecla_c_anterior = tecla_c

    # vida chegou a 0 -> o mundo congela enquanto roda a animação de morte do Lula,
    # e só depois de 2 s a fase inteira reinicia do começo
    if lula.morto():
        if lula.contadorMorte == 1:     # primeiro update da animação de morte: a música para
            pararMusica()
        if lula.terminouMorte():
            reiniciarFase()
        return False

    # inimigos andando, contato com o Lula e partículas dos blocos quebrados
    # (continua rodando durante a saída; o Lula não leva dano nesse tempo)
    fase.atualizar(lula, areaVisivel())
    atualizarMusicaLulatron()

    if lula.saindoDaFase:
        # andando sozinho para a direita: quando sumir da tela, começa a próxima fase
        if lula.saiuDaTela(camera.x + camera.larguraVisivel):
            irParaProximaFase(window)
            return True
        return False

    # encostou na parte amarela -> passou de fase: perde o controle e sai andando pela direita
    if fase.colideChegada(*lula.hitbox(lula.x, lula.y)):
        mensagemFase.visivel = True
        lula.comecarSaida()
    return False


def render(window, alfa):
    # alfa: quanto já passou do próximo update (0 a 1), para desenhar entre o estado anterior e o atual
    larg, alt = glfw.get_framebuffer_size(window)
    if larg == 0 or alt == 0:           # janela minimizada
        return
    glViewport(0, 0, larg, alt)
    camera.ajustarTela(larg, alt)

    # a fase fica parada, quem se move é a câmera atrás do Lula
    # (segue a posição suavizada e alinhada, a mesma usada para desenhar o Lula -> ele não treme)
    # morrendo ou saindo da fase: a câmera fica parada onde estava, para o Lula sair da tela
    if not lula.morto() and not lula.saindoDaFase:
        lx, ly = lula.posicaoDesenho(alfa)
        camera.seguir(camera.alinhar(lx), camera.alinhar(ly), fase.largura, fase.altura)

    glClear(GL_COLOR_BUFFER_BIT)

    projecao = camera.matrizProjecao()
    # mundo congelado durante a morte: desenha no estado atual (sem interpolar, senão treme)
    alfaMundo = 1.0 if lula.morto() else alfa
    fase.draw(projecao, sprites, alfaMundo, camera.alinhar)  # arte + blocos + inimigos (+ colisão no debug)
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

    # a câmera precisa saber o tamanho da janela antes do primeiro update (spawn dos inimigos)
    camera.ajustarTela(*glfw.get_framebuffer_size(window))
    init()
    fase.ativarInimigos(areaVisivel())
    iniciarAudio()

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

            trocouFase = update(window)

            acumulador -= TEMPO_POR_ATUALIZACAO

            if trocouFase:
                # carregar a fase nova demora um pouco: esse tempo não vira uma enxurrada de updates
                acumulador = 0.0
                last_time = glfw.get_time()
                break

        render(window, acumulador / TEMPO_POR_ATUALIZACAO)
        glfw.swap_buffers(window)

    lula.delete()
    fase.delete()
    mensagemFase.delete()
    sprites.delete()
    pararMusica()
    glfw.terminate()

if __name__ == '__main__':
    main()
