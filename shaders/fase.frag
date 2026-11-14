#version 330 core

in vec2 vUV;

uniform sampler2D uTextura;
uniform vec2 uTamanhoTextura;   // largura e altura da textura em texels

// estilo 16 bits
uniform bool  uEstilo16bits;
uniform float uTamanhoBloco;    // quantos texels viram 1 "pixel" do estilo retrô
uniform vec3  uNiveisCor;       // níveis por canal: (31, 63, 31) = RGB565, cor de 16 bits

uniform float uOpacidade;       // usada no modo debug para ver a colisão por cima

out vec4 corFinal;

void main()
{
    vec2 uv = vUV;

    if (uEstilo16bits) {
        // 1. pixelização: todos os texels de um bloco leem a cor do centro do bloco,
        //    então a arte borrada vira blocos nítidos
        vec2 texel = uv * uTamanhoTextura;
        texel = (floor(texel / uTamanhoBloco) + 0.5) * uTamanhoBloco;
        uv = texel / uTamanhoTextura;
    }

    vec4 cor = texture(uTextura, uv);

    if (uEstilo16bits) {
        // 2. quantização: reduz a paleta para 5 bits R, 6 bits G, 5 bits B (16 bits por pixel)
        cor.rgb = floor(cor.rgb * uNiveisCor + 0.5) / uNiveisCor;
    }

    corFinal = vec4(cor.rgb, cor.a * uOpacidade);
}
