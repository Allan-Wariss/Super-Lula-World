#version 330 core

// Quad texturizado: pinta o retângulo com a textura, respeitando a transparência do PNG.
// Par do quadTexturizado.vert (blocos, inimigos, partículas e texto).

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
