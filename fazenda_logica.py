"""Regras do jogo Minha Fazendinha.""" 
from time import time


class Jogador:
    def __init__(
        self, moedas_iniciais=50, capacidade_maxima=20, produtos=None
    ):
        self.moedas = moedas_iniciais
        if produtos is None:
            produtos = ("Trigo", "Tomate", "Feijao")
        self.armazem = {produto: 0 for produto in produtos}
        self.capacidade_maxima = capacidade_maxima

    def total_itens_no_armazem(self):
        return sum(self.armazem.values())

    def tem_espaco_no_armazem(self):
        return self.total_itens_no_armazem() < self.capacidade_maxima

    def vender(self, nome_produto, valor, nome_exibicao=None):
        if nome_produto not in self.armazem:
            return False, "Produto desconhecido."
        if self.armazem[nome_produto] <= 0:
            nome_exibicao = nome_exibicao or nome_produto
            return False, f"Você não tem {nome_exibicao.lower()} no armazém."
        self.armazem[nome_produto] -= 1
        self.moedas += valor
        nome_exibicao = nome_exibicao or nome_produto
        return True, f"1 {nome_exibicao} vendido por {valor} moedas."

    def consumir_ingredientes(self, receita):
        for ingrediente, quantidade in receita.ingredientes_requeridos.items():
            if self.armazem.get(ingrediente, 0) < quantidade:
                return False, f"Ingredientes insuficientes para {receita.nome}."

        for ingrediente, quantidade in receita.ingredientes_requeridos.items():
            self.armazem[ingrediente] -= quantidade

        return True, ""

    def cozinhar(self, receita):
        sucesso, mensagem = self.consumir_ingredientes(receita)
        if not sucesso:
            return sucesso, mensagem
        self.moedas += receita.valor_venda
        return True, f"{receita.emoji} {receita.nome} preparado e vendido por {receita.valor_venda} moedas!"


class Planta:
    def __init__(
        self, nome, tempo_crescimento, custo, valor_venda, emoji="🌱",
        nome_exibicao=None
    ):
        self.nome = nome
        self.nome_exibicao = nome_exibicao or nome
        self.tempo_crescimento = tempo_crescimento
        self.custo = custo
        self.valor_venda = valor_venda
        self.emoji = emoji

class Receita:
    def __init__(
        self, nome, ingredientes_requeridos, valor_venda, emoji="🥗",
        tempo_cozimento=60
    ):
        self.nome = nome
        self.ingredientes_requeridos = ingredientes_requeridos
        self.valor_venda = valor_venda
        self.emoji = emoji
        self.tempo_cozimento = tempo_cozimento

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
        return True, f"{planta.nome_exibicao} plantado com sucesso!"

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
        nome_exibicao = self.planta_atual.nome_exibicao
        jogador.armazem[nome] += 1
        self.estado = "VAZIO"
        self.planta_atual = None
        self.timestamp_plantio = None
        return True, f"Você colheu 1 {nome_exibicao}!"


class Fogao:
    def __init__(self, id_fogao, comprado=False):
        self.id_fogao = id_fogao
        self.comprado = comprado
        self.timestamp_cozimento = None
        self.receita_atual = None
        self.estado = "VAZIO" if comprado else "BLOQUEADO"

    def cozinhar(self, receita, jogador):
        if not self.comprado:
            return False, "Este fogão ainda não foi comprado."
        if self.estado != "VAZIO":
            return False, "Este fogão não está vazio."
        sucesso, mensagem = jogador.consumir_ingredientes(receita)
        if not sucesso:
            return sucesso, mensagem
        self.receita_atual = receita
        self.timestamp_cozimento = time()
        self.estado = "COZINHANDO"
        return True, f"{receita.nome} cozinhada com sucesso!"

    def checar_cozinhar(self):
        if self.estado != "COZINHANDO" or self.receita_atual is None:
            return False
        decorrido = time() - self.timestamp_cozimento
        if decorrido >= self.receita_atual.tempo_cozimento:
            self.estado = "PRONTO"
            return True
        return False

    def tempo_restante(self):
        if self.estado != "COZINHANDO" or self.receita_atual is None:
            return 0
        restante = self.receita_atual.tempo_cozimento - (
            time() - self.timestamp_cozimento
        )
        return max(0, int(restante + 0.999))

    def colher(self, jogador):
        if self.estado != "PRONTO" or self.receita_atual is None:
            return False, "A receita ainda não está pronta."
        receita = self.receita_atual
        jogador.moedas += receita.valor_venda
        self.estado = "VAZIO"
        self.receita_atual = None
        self.timestamp_cozimento = None
        return True, (
            f"{receita.emoji} {receita.nome} preparado e vendido por "
            f"{receita.valor_venda} moedas!"
        )
