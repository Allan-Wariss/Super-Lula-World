#version 330 core

in vec2 vUV;

uniform sampler2D uTextura;

out vec4 corFinal;

void main()
{
    vec4 cor = texture(uTextura, vUV);

    // pixels totalmente transparentes não são desenhados; o resto usa o blend (bordas suaves do texto)
    if (cor.a < 0.01)
        discard;

    corFinal = cor;
}
