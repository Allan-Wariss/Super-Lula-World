#version 330 core

layout (location = 0) in vec2 aPosicao;   // posição em pixels do mundo
layout (location = 1) in vec2 aUV;

// Projeção ortográfica da câmera (mundo em pixels -> tela)
uniform mat4 uProjecao;

out vec2 vUV;

void main()
{
    gl_Position = uProjecao * vec4(aPosicao, 0.0, 1.0);
    vUV = aUV;
}
