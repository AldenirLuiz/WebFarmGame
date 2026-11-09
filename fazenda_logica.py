"""Regras do jogo Minha Fazendinha.""" 
from time import time


class Jogador:
    def __init__(
        self, moedas_iniciais=50, capacidade_maxima=20, produtos=None,
        aumento_capacidade_armazem=10
    ):
        self.moedas = moedas_iniciais
        if produtos is None:
            produtos = ("Trigo", "Tomate", "Feijao")
        self.armazem = {produto: 0 for produto in produtos}
        self.capacidade_base_armazem = capacidade_maxima
        self.aumento_capacidade_armazem = aumento_capacidade_armazem
        self.nivel_melhoria_armazem = 0

    @property
    def capacidade_maxima(self):
        return (
            self.capacidade_base_armazem
            + self.nivel_melhoria_armazem
            * self.aumento_capacidade_armazem
        )

    def melhorar_armazem(self, custos):
        if self.nivel_melhoria_armazem >= len(custos):
            return False, "O armazém já atingiu o nível máximo."

        custo = custos[self.nivel_melhoria_armazem]
        if self.moedas < custo:
            return False, "Moedas insuficientes para melhorar o armazém."

        self.moedas -= custo
        self.nivel_melhoria_armazem += 1
        return True, (
            f"Armazém melhorado para o nível "
            f"{self.nivel_melhoria_armazem}! Capacidade aumentada em "
            f"{self.aumento_capacidade_armazem} itens."
        )

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
    def __init__(
        self, id_lote, comprado=False, reducao_tempo_por_nivel=0.1
    ):
        self.id_lote = id_lote
        self.comprado = comprado
        self.estado = "VAZIO" if comprado else "BLOQUEADO"
        self.planta_atual = None
        self.timestamp_plantio = None
        self.nivel_melhoria = 0
        self.reducao_tempo_por_nivel = reducao_tempo_por_nivel

    def tempo_crescimento_planta(self, planta):
        reducao = self.reducao_tempo_por_nivel * self.nivel_melhoria
        return planta.tempo_crescimento * (1 - reducao)

    def melhorar(self, jogador, custos):
        if not self.comprado:
            return False, "Este lote ainda não foi comprado."
        if self.estado != "VAZIO":
            return False, "Colha a plantação antes de melhorar este lote."
        if self.nivel_melhoria >= len(custos):
            return False, "Este lote já atingiu o nível máximo."

        custo = custos[self.nivel_melhoria]
        if jogador.moedas < custo:
            return False, "Moedas insuficientes para melhorar este lote."

        jogador.moedas -= custo
        self.nivel_melhoria += 1
        return True, (
            f"Lote {self.id_lote} melhorado para o nível "
            f"{self.nivel_melhoria}! As plantas crescem "
            f"{self.reducao_tempo_por_nivel:.0%} mais rápido por nível."
        )

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
        if decorrido >= self.tempo_crescimento_planta(self.planta_atual):
            self.estado = "PRONTO"
            return True
        return False

    def tempo_restante(self):
        if self.estado != "PLANTADO" or self.planta_atual is None:
            return 0
        restante = self.tempo_crescimento_planta(self.planta_atual) - (
            time() - self.timestamp_plantio
        )
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


class Animal:
    def __init__(
        self, chave, nome, emoji, custo, alimento, intervalo_alimentacao,
        tempo_crescimento, tempo_reproducao, capacidade, valor_venda
    ):
        self.chave = chave
        self.nome = nome
        self.emoji = emoji
        self.custo = custo
        self.alimento = alimento
        self.intervalo_alimentacao = intervalo_alimentacao
        self.tempo_crescimento = tempo_crescimento
        self.tempo_reproducao = tempo_reproducao
        self.capacidade = capacidade
        self.valor_venda = valor_venda


class Curral:
    def __init__(self, id_curral, comprado=False):
        self.id_curral = id_curral
        self.comprado = comprado
        self.animal = None
        self.animais = []
        self.alimentado = False
        self.ultima_atualizacao = time()
        self.proxima_alimentacao = None
        self.proxima_reproducao = None
        self.nivel_melhoria = 0

    @property
    def capacidade_maxima(self):
        if self.animal is None:
            return 0
        return self.animal.capacidade + self.nivel_melhoria

    def melhorar(self, jogador, custos):
        if not self.comprado:
            return False, "Esta baia ainda não foi comprada."
        if self.nivel_melhoria >= len(custos):
            return False, "Esta baia já atingiu o nível máximo."

        custo = custos[self.nivel_melhoria]
        if jogador.moedas < custo:
            return False, "Moedas insuficientes para melhorar esta baia."

        jogador.moedas -= custo
        self.nivel_melhoria += 1
        return True, (
            f"Baia {self.id_curral} melhorada para o nível "
            f"{self.nivel_melhoria}! Capacidade aumentada em 1 animal."
        )

    def comprar_animal(self, animal, jogador):
        if not self.comprado:
            return False, "Esta baia ainda não foi comprada."
        if self.animais:
            return False, "Esta baia já tem animais."
        if jogador.moedas < animal.custo:
            return False, "Moedas insuficientes para comprar este animal."

        jogador.moedas -= animal.custo
        self.animal = animal
        self.animais = [0.0]
        self.alimentado = False
        self.ultima_atualizacao = time()
        self.proxima_alimentacao = self.ultima_atualizacao
        self.proxima_reproducao = None
        return True, f"{animal.emoji} {animal.nome} chegou ao curral!"

    def adicionar_animal(self, jogador):
        if self.animal is None:
            return False, "Escolha um animal para esta baia primeiro."
        if len(self.animais) >= self.capacidade_maxima:
            return False, "Esta baia já atingiu sua capacidade."
        if jogador.moedas < self.animal.custo:
            return False, "Moedas insuficientes para comprar este animal."

        jogador.moedas -= self.animal.custo
        self.animais.append(0.0)
        self.alimentado = False
        self.ultima_atualizacao = time()
        self.proxima_alimentacao = self.ultima_atualizacao
        return True, f"Mais um(a) {self.animal.nome} chegou ao curral!"

    def adultos(self):
        if self.animal is None:
            return 0
        return sum(
            idade >= self.animal.tempo_crescimento
            for idade in self.animais
        )

    def processar_ciclo(self, jogador, agora=None):
        if not self.comprado or self.animal is None:
            return []

        agora = time() if agora is None else agora
        if self.proxima_alimentacao is None:
            self.proxima_alimentacao = agora
            self.alimentado = False
        eventos = []
        while self.ultima_atualizacao < agora:
            if self.alimentado:
                limite = min(agora, self.proxima_alimentacao)
                decorrido = limite - self.ultima_atualizacao
                if decorrido > 0:
                    self.animais = [
                        idade + decorrido for idade in self.animais
                    ]
                    self.ultima_atualizacao = limite

                if limite < self.proxima_alimentacao:
                    break

            else:
                if self.proxima_alimentacao > agora:
                    self.ultima_atualizacao = agora
                    break
                self.ultima_atualizacao = self.proxima_alimentacao

            alimentacao = {
                item: quantidade * len(self.animais)
                for item, quantidade in self.animal.alimento.items()
            }
            tem_alimento = all(
                jogador.armazem.get(item, 0) >= quantidade
                for item, quantidade in alimentacao.items()
            )
            estava_alimentado = self.alimentado
            if tem_alimento:
                for item, quantidade in alimentacao.items():
                    jogador.armazem[item] -= quantidade
                self.alimentado = True
                self.proxima_alimentacao += (
                    self.animal.intervalo_alimentacao
                )
            else:
                self.alimentado = False
                self.proxima_alimentacao = (
                    self.ultima_atualizacao
                    + self.animal.intervalo_alimentacao
                )
                if estava_alimentado or not eventos:
                    itens = ", ".join(
                        f"{quantidade} {item}"
                        for item, quantidade in alimentacao.items()
                    )
                    eventos.append(
                        f"{self.animal.nome}: alimento insuficiente "
                        f"({itens}); crescimento pausado."
                    )

        adultos = self.adultos()
        if adultos < 2:
            self.proxima_reproducao = None
        elif self.proxima_reproducao is None:
            self.proxima_reproducao = agora + self.animal.tempo_reproducao
        elif (
            self.alimentado
            and len(self.animais) < self.capacidade_maxima
            and agora >= self.proxima_reproducao
        ):
            self.animais.append(0.0)
            self.proxima_reproducao = agora + self.animal.tempo_reproducao
            eventos.append(
                f"Nasceu um filhote de {self.animal.nome} no curral "
                f"{self.id_curral}!"
            )

        return eventos

    def tempo_para_crescer(self, agora=None):
        if self.animal is None or not self.animais:
            return 0
        agora = time() if agora is None else agora
        idade = min(self.animais)
        if idade >= self.animal.tempo_crescimento:
            return 0
        restante = self.animal.tempo_crescimento - idade
        if self.alimentado and self.proxima_alimentacao is not None:
            restante += max(0, self.proxima_alimentacao - agora)
        return max(0, int(restante + 0.999))

    def vender_adulto(self, jogador):
        if self.animal is None or self.adultos() == 0:
            return False, "Ainda não há animais adultos para vender."
        nome_animal = self.animal.nome
        valor_venda = self.animal.valor_venda
        self.animais.remove(
            next(
                idade for idade in self.animais
                if idade >= self.animal.tempo_crescimento
            )
        )
        jogador.moedas += valor_venda
        if not self.animais:
            self.animal = None
            self.alimentado = False
            self.proxima_alimentacao = None
            self.proxima_reproducao = None
        return True, (
            f"{nome_animal} vendido por {valor_venda} moedas."
        )
