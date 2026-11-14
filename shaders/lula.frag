#version 330 core

in vec2 vUV;

// Sprite atual da animação (unidade de textura 0)
uniform sampler2D uTextura;

out vec4 corFinal;

void main()
{
    vec4 cor = texture(uTextura, vUV);

    // descarta os pixels transparentes do PNG
    if (cor.a < 0.1)
        discard;

    corFinal = cor;
}
