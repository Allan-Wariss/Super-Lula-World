#version 330 core

// quad unitário: posição de (0,0) até (1,1)
layout (location = 0) in vec2 aPosicao;
layout (location = 1) in vec2 aUV;

uniform vec2 uDeslocamento;   // canto inferior esquerdo do sprite (pixels)
uniform vec2 uTamanho;        // largura e altura do sprite (pixels)
uniform mat4 uProjecao;       // projeção ortográfica (mundo ou tela)

out vec2 vUV;

void main()
{
    gl_Position = uProjecao * vec4(aPosicao * uTamanho + uDeslocamento, 0.0, 1.0);
    vUV = aUV;
}
