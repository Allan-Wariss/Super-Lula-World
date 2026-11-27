from PIL import Image
from OpenGL.GL import *

class Texture:
    def __init__(self, fileName):
        # aceita o caminho de um arquivo ou uma imagem PIL já carregada
        img = Image.open(fileName) if isinstance(fileName, str) else fileName
        img = img.transpose(Image.FLIP_TOP_BOTTOM)  # inverte a imagem verticalmente
        imgData = img.convert("RGBA").tobytes()      # converte a imagem para um vetor de bytes

        self.texId = glGenTextures(1)  # criar textura
        glBindTexture(GL_TEXTURE_2D, self.texId)    # torna ela ativa
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST) 

        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        # glTexEnvf foi removido: não existe no OpenGL core, quem decide a cor agora é o fragment shader

        glTexImage2D(
            GL_TEXTURE_2D,                          # tipo alvo de textura
            0,                                      # nível de mipmap
            GL_RGBA,                                 # formato interno de armazenamento
            img.width,                              # largura da imagem em pixels
            img.height,                             # altura da imagem em pixels
            0,                                      # borda
            GL_RGBA,                                 # formato dos dados da imagem
            GL_UNSIGNED_BYTE,
            imgData
        )

        glBindTexture(GL_TEXTURE_2D, 0)             # desativa. Ativa apenas quando for usar

def pixelArt(img, tamanho):
    # reduz uma imagem grande para a resolução final (1 pixel da textura = 1 pixel do mundo)
    # e deixa a transparência "dura" (cada pixel é opaco ou vazio), para as bordas ficarem
    # nítidas como pixel art e não borradas
    img = img.resize(tamanho, Image.BOX)
    alfa = img.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
    img.putalpha(alfa)
    return img
