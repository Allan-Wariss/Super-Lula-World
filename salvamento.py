import os
import json

# arquivo com o progresso do jogador (qual fase ele está). fica ao lado do jogo
ARQUIVO_SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'save.json')

def carregarFase(totalFases):
    # devolve o índice da fase salva (0 = primeira). sem save ou com save estragado, começa do início
    try:
        with open(ARQUIVO_SAVE, 'r', encoding='utf-8') as arquivo:
            indice = int(json.load(arquivo)['fase'])
    except (OSError, ValueError, KeyError, TypeError):
        return 0
    return indice if 0 <= indice < totalFases else 0

def salvarFase(indice):
    try:
        with open(ARQUIVO_SAVE, 'w', encoding='utf-8') as arquivo:
            json.dump({'fase': indice}, arquivo)
    except OSError as erro:             # sem permissão de escrita: o jogo continua, só não salva
        print('Não foi possível salvar:', erro)
