from OpenGL.GL import *
import glfw
from bulletObject import BulletObject

class ShipObject:
    def __init__(self, x=0.0, y=-0.5):
        self.x = x
        self.y = y

        tamV0 = [-0.07, -0.07]
        tamV1 = [0.07, -0.07]
        tamV2 = [0.07, 0.07]
        tamV3 = [-0.07, 0.07]

        self.vertices = [tamV0, tamV1, tamV2, tamV3]
        
        self.uvs = [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1]
        ]

        self.faces = [
            [0, 1, 2],
            [0, 2, 3]
        ]
        
        self.texId = 0
        self.color = [1, 1, 0]
        
    def mover(self, window, velocidade=0.02, x_min=-0.8, x_max=0.8, y_min=-0.9, y_max=0.6):
        if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS and self.y <= y_max:
            self.y += velocidade  
        if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS and self.y >= y_min:
            self.y -= velocidade  
        if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS and self.x >= x_min:
            self.x -= velocidade  
        if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS and self.x <= x_max:
            self.x += velocidade

    def atirar(self):
        # Cria e retorna um objeto de tiro na posição atual da nave
        return BulletObject(x=self.x, y=self.y + 0.1, velocidade_y=0.04, color=[0, 1, 0])

    def draw(self):
        glColor3fv(self.color)
        glBindTexture(GL_TEXTURE_2D, self.texId)
        
        glBegin(GL_TRIANGLES)
        for f in self.faces:
            for vid in f:
                glTexCoord2fv(self.uvs[vid])
                vx = self.vertices[vid][0] + self.x
                vy = self.vertices[vid][1] + self.y
                glVertex2f(vx, vy)
        glEnd()
        
        glBindTexture(GL_TEXTURE_2D, 0)