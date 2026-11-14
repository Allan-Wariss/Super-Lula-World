#version 330 core

// Atributos vindos do VBO (configurados no VAO do LulaObject)
layout (location = 0) in vec2 aPosicao;   // posição do vértice em pixels (relativa aos pés do boneco)
layout (location = 1) in vec2 aUV;        // coordenada de textura

// Posição do personagem no mundo (atualizada a cada frame)
uniform vec2 uDeslocamento;

// Projeção ortográfica da câmera (mundo em pixels -> tela)
uniform mat4 uProjecao;

out vec2 vUV;

void main()
{
    gl_Position = uProjecao * vec4(aPosicao + uDeslocamento, 0.0, 1.0);
    vUV = aUV;
}
