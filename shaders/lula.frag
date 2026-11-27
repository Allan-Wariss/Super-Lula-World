#version 330 core

in vec2 vUV;

// Sprite atual da animação (unidade de textura 0)
uniform sampler2D uTextura;

// Lulatron: cor do pisca-pisca e quanto ela cobre o sprite (0 = desenho normal)
uniform vec3  uCorTinta;
uniform float uMisturaTinta;

out vec4 corFinal;

void main()
{
    vec4 cor = texture(uTextura, vUV);

    // descarta os pixels transparentes do PNG
    if (cor.a < 0.1)
        discard;

    // tinge mantendo o sombreado do desenho: partes escuras continuam escuras
    float luz = dot(cor.rgb, vec3(0.299, 0.587, 0.114));
    vec3 tingido = uCorTinta * (0.35 + 0.9 * luz);
    corFinal = vec4(mix(cor.rgb, tingido, uMisturaTinta), cor.a);
}
