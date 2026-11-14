from OpenGL.GL import *

class Shader:
    def __init__(self, vertPath, fragPath):
        vertSrc = open(vertPath, encoding='utf-8').read()   # lê o código GLSL dos arquivos
        fragSrc = open(fragPath, encoding='utf-8').read()

        vert = self.compilar(vertSrc, GL_VERTEX_SHADER)
        frag = self.compilar(fragSrc, GL_FRAGMENT_SHADER)

        self.programId = glCreateProgram()          # cria o programa e liga os dois shaders
        glAttachShader(self.programId, vert)
        glAttachShader(self.programId, frag)
        glLinkProgram(self.programId)

        if not glGetProgramiv(self.programId, GL_LINK_STATUS):
            erro = glGetProgramInfoLog(self.programId).decode()
            raise RuntimeError('Erro ao linkar o shader:\n' + erro)

        glDeleteShader(vert)                        # depois de linkados não são mais necessários
        glDeleteShader(frag)

    def compilar(self, src, tipo):
        shaderId = glCreateShader(tipo)
        glShaderSource(shaderId, src)
        glCompileShader(shaderId)

        if not glGetShaderiv(shaderId, GL_COMPILE_STATUS):
            erro = glGetShaderInfoLog(shaderId).decode()
            raise RuntimeError('Erro ao compilar o shader:\n' + erro)

        return shaderId

    def usar(self):
        glUseProgram(self.programId)

    def setInt(self, nome, valor):
        glUniform1i(glGetUniformLocation(self.programId, nome), valor)

    def setFloat(self, nome, valor):
        glUniform1f(glGetUniformLocation(self.programId, nome), valor)

    def setVec2(self, nome, x, y):
        glUniform2f(glGetUniformLocation(self.programId, nome), x, y)

    def setVec3(self, nome, x, y, z):
        glUniform3f(glGetUniformLocation(self.programId, nome), x, y, z)

    def setMat4(self, nome, matriz):
        # numpy guarda por linha, o OpenGL espera por coluna -> GL_TRUE transpõe
        glUniformMatrix4fv(glGetUniformLocation(self.programId, nome), 1, GL_TRUE, matriz)

    def delete(self):
        glDeleteProgram(self.programId)
