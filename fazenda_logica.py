"""Regras do jogo Minha Fazendinha.""" 
from time import time


class Jogador:
    def __init__(self, moedas_iniciais=50, capacidade_maxima=20):
        self.moedas = moedas_iniciais
        self.armazem = {"Trigo": 0, "Tomate": 0, "Feijao": 0}
        self.capacidade_maxima = capacidade_maxima

    def total_itens_no_armazem(self):
        return sum(self.armazem.values())

    def tem_espaco_no_armazem(self):
        return self.total_itens_no_armazem() < self.capacidade_maxima

    def vender(self, nome_produto, valor):
        if nome_produto not in self.armazem:
            return False, "Produto desconhecido."
        if self.armazem[nome_produto] <= 0:
            return False, f"Você não tem {nome_produto.lower()} no armazém."
        self.armazem[nome_produto] -= 1
        self.moedas += valor
        return True, f"1 {nome_produto} vendido por {valor} moedas."

    def cozinhar(self, receita):
        # 1. Verifica se tem todos os ingredientes nas quantidades certas
        for ingrediente, quantidade in receita.ingredientes_requeridos.items():
            if self.armazem.get(ingrediente, 0) < quantidade:
                return False, f"Ingredientes insuficientes para {receita.nome}."

        # 2. Consome os ingredientes do armazém
        for ingrediente, quantidade in receita.ingredientes_requeridos.items():
            self.armazem[ingrediente] -= quantity if 'quantity' in locals() else quantidade

        # 3. Adiciona o dinheiro da venda imediata do prato
        self.moedas += receita.valor_venda
        return True, f"{receita.emoji} {receita.nome} preparado e vendido por {receita.valor_venda} moedas!"


class Planta:
    def __init__(self, nome, tempo_crescimento, custo, valor_venda, emoji="🌱"):
        self.nome = nome
        self.tempo_crescimento = tempo_crescimento
        self.custo = custo
        self.valor_venda = valor_venda
        self.emoji = emoji


class LoteTerra:
    def __init__(self, id_lote, comprado=False):
        self.id_lote = id_lote
        self.comprado = comprado
        self.estado = "VAZIO" if comprado else "BLOQUEADO"
        self.planta_atual = None
        self.timestamp_plantio = None

    def plantar(self, planta, jogador):
        if not self.comprado:
            return False, "Este lote ainda não foi comprado."
        if self.estado != "VAZIO":
            return False, "Este lote não está vazio."
        if jogador.moedas < planta.custo:
            return False, "Moedas insuficientes para comprar esta semente."
        jogador.moedas -= planta.custo
        self.planta_atual = planta
        self.timestamp_plantio = time()
        self.estado = "PLANTADO"
        return True, f"{planta.nome} plantado com sucesso!"

    def checar_crescimento(self):
        if self.estado != "PLANTADO" or self.planta_atual is None:
            return False
        decorrido = time() - self.timestamp_plantio
        if decorrido >= self.planta_atual.tempo_crescimento:
            self.estado = "PRONTO"
            return True
        return False

    def tempo_restante(self):
        if self.estado != "PLANTADO" or self.planta_atual is None:
            return 0
        restante = self.planta_atual.tempo_crescimento - (time() - self.timestamp_plantio)
        return max(0, int(restante + 0.999))

    def colher(self, jogador):
        if self.estado != "PRONTO" or self.planta_atual is None:
            return False, "A planta ainda não está pronta para colher."
        if not jogador.tem_espaco_no_armazem():
            return False, "Armazém cheio! Venda algum produto antes de colher."
        nome = self.planta_atual.nome
        jogador.armazem[nome] += 1
        self.estado = "VAZIO"
        self.planta_atual = None
        self.timestamp_plantio = None
        return True, f"Você colheu 1 {nome}!"


class Receita:
    def __init__(self, nome, ingredientes_requeridos, valor_venda, emoji="🥗"):
        self.nome = nome
        self.ingredientes_requeridos = ingredientes_requeridos  # Dicionário, ex: {"Tomate": 2}
        self.valor_venda = valor_venda
        self.emoji = emoji


