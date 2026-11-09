from pyscript import document
from pyodide.ffi import create_proxy
from fazenda_logica import Jogador, Planta, LoteTerra, Receita
import asyncio
import json
from pyscript import window
import time

# --- Inicialização dos Objetos ---
jogador = Jogador()
trigo = Planta("Trigo", tempo_crescimento=10, custo=10, valor_venda=25, emoji="🌾")
tomate = Planta("Tomate", tempo_crescimento=25, custo=25, valor_venda=65, emoji="🍅")
feijao = Planta("Feijao", tempo_crescimento=50, custo=50, valor_venda=120, emoji="🫘")
semente_selecionada = trigo

PLANTAS_POR_NOME = {
    planta.nome: planta
    for planta in [trigo, tomate, feijao]
}

receita_salada = Receita(
    nome="Salada de Tomate", 
    ingredientes_requeridos={"Tomate": 2}, 
    valor_venda=160, 
    emoji="🥗"
)

receita_feijao = Receita(
    nome="Feijão Cozido", 
    ingredientes_requeridos={"Feijao": 4}, 
    valor_venda=300, 
    emoji="🍲"
)

receita_pao = Receita(
    nome="Pão de Trigo", 
    ingredientes_requeridos={"Trigo": 8}, 
    valor_venda=100, 
    emoji="🥖"
)

# Criados os 9 lotes conforme seu arquivo atualizado
lotes = [
    LoteTerra(1, comprado=True),
    LoteTerra(2), LoteTerra(3), LoteTerra(4), LoteTerra(5), LoteTerra(6),
    LoteTerra(7), LoteTerra(8), LoteTerra(9)
]

_proxies_eventos = []

def registrar_evento(elemento, evento, funcao_python):
    if elemento is not None:
        proxy = create_proxy(funcao_python)
        _proxies_eventos.append(proxy)
        elemento.addEventListener(evento, proxy)


def mostrar_mensagem(texto):
    document.querySelector("#mensagem").innerText = texto

def preco_lote(id_lote):
    return (id_lote * 100) * 2

# --- Sistema de Persistência (Save/Load) ---
def carregar_jogo():
    save_data = window.localStorage.getItem(
        "fazenda_paraiso_save"
    )

    if save_data is None:
        return

    try:
        dados = json.loads(save_data)

        # Restaura os dados básicos
        jogador.moedas = int(dados["moedas"])

        jogador.armazem = {
            nome: int(dados.get("armazem", {}).get(nome, 0))
            for nome in ["Trigo", "Tomate", "Feijao"]
        }

        # Compatibilidade com o formato antigo
        lotes_salvos = dados.get("lotes")

        if lotes_salvos is None:
            antigos = dados.get("lotes_comprados", [])

            for i, lote in enumerate(lotes):
                comprado = (
                    bool(antigos[i])
                    if i < len(antigos) else lote.id_lote == 1
                )

                lote.comprado = comprado
                lote.estado = "VAZIO" if comprado else "BLOQUEADO"
                lote.planta_atual = None
                lote.timestamp_plantio = None

        else:
            for i, lote in enumerate(lotes):

                if i >= len(lotes_salvos):
                    continue

                salvo = lotes_salvos[i]

                lote.comprado = salvo["comprado"]

                if not lote.comprado:
                    lote.estado = "BLOQUEADO"
                    lote.planta_atual = None
                    lote.timestamp_plantio = None
                    continue

                estado = salvo["estado"]

                if estado == "PLANTADO" or estado == "PRONTO":
                    nome_planta = salvo["planta"]

                    lote.planta_atual = PLANTAS_POR_NOME[nome_planta]
                    lote.timestamp_plantio = float(
                        salvo["timestamp_plantio"]
                    )

                    lote.estado = estado

                    # Verifica se amadureceu enquanto
                    # o navegador estava fechado
                    lote.checar_crescimento()

                else:
                    lote.estado = "VAZIO"
                    lote.planta_atual = None
                    lote.timestamp_plantio = None

        atualizar_tela()
        mostrar_mensagem("Progresso carregado com sucesso!")

    except Exception as e:
        print("Erro ao carregar jogo:", e)
        mostrar_mensagem("Erro ao carregar o salvamento.")
        
def salvar_jogo():
    dados_salvamento = {
        "versao": 2,
        "moedas": jogador.moedas,
        "armazem": jogador.armazem,
        "lotes": [
            {
                "id": lote.id_lote,
                "comprado": lote.comprado,
                "estado": lote.estado,
                "planta": (
                    lote.planta_atual.nome
                    if lote.planta_atual else None
                ),
                "timestamp_plantio": lote.timestamp_plantio
            }
            for lote in lotes
        ]
    }

    window.localStorage.setItem(
        "fazenda_paraiso_save",
        json.dumps(dados_salvamento)
    )
# --- Lógica de Seleção de Cultivos ---
def selecionar_semente(planta):
    global semente_selecionada
    semente_selecionada = planta
    document.querySelector("#btn-trigo").className = "botao-semente ativa" if planta.nome == "Trigo" else "botao-semente"
    document.querySelector("#btn-tomate").className = "botao-semente ativa" if planta.nome == "Tomate" else "botao-semente"
    document.querySelector("#btn-feijao").className = "botao-semente ativa" if planta.nome == "Feijao" else "botao-semente"
    mostrar_mensagem(f"Semente selecionada: {planta.nome}.")

def clicar_selecionar_trigo(event): selecionar_semente(trigo)
def clicar_selecionar_tomate(event): selecionar_semente(tomate)
def clicar_selecionar_feijao(event): selecionar_semente(feijao)

# --- Mercado e Vendas ---
def vender(nome, valor):
    sucesso, mensagem = jogador.vender(nome, valor)
    mostrar_mensagem(mensagem)
    if sucesso:
        salvar_jogo()
    atualizar_tela()

def clicar_vender_trigo(event): vender("Trigo", trigo.valor_venda)
def clicar_vender_tomate(event): vender("Tomate", tomate.valor_venda)
def clicar_vender_feijao(event): vender("Feijao", feijao.valor_venda)

# --- Interface Gráfica ---
def atualizar_tela():
    total = jogador.total_itens_no_armazem()
    document.querySelector("#txt-moedas").innerText = str(jogador.moedas)
    document.querySelector("#txt-total-estoque").innerText = str(total)
    document.querySelector("#txt-max-estoque").innerText = str(jogador.capacidade_maxima)
    document.querySelector("#estoque-trigo").innerText = str(jogador.armazem.get("Trigo", 0))
    document.querySelector("#estoque-tomate").innerText = str(jogador.armazem.get("Tomate", 0))
    document.querySelector("#estoque-feijao").innerText = str(jogador.armazem.get("Feijao", 0))

    porcentagem = (total / jogador.capacidade_maxima) * 100
    document.querySelector("#barra-progresso").style.width = f"{porcentagem}%"
    
    document.querySelector("#vender-trigo").disabled = jogador.armazem.get("Trigo", 0) == 0
    document.querySelector("#vender-tomate").disabled = jogador.armazem.get("Tomate", 0) == 0
    document.querySelector("#vender-feijao").disabled = jogador.armazem.get("Feijao", 0) == 0

    botao_salada = document.querySelector("#btn-craft-salada")
    if botao_salada:
        botao_salada.disabled = jogador.armazem.get("Tomate", 0) < 2

    proximo_lote = next((l.id_lote for l in lotes if not l.comprado), None)

    for lote in lotes:
        elemento = document.querySelector(f"#lote-{lote.id_lote}")
        if elemento is None:
            continue
            
        elemento.disabled = False

        if lote.comprado:
            elemento.className = f"lote {lote.estado}"
            if lote.estado == "VAZIO":
                conteudo = '<span class="emoji-status">🟫</span><span>TERRA</span><span class="tempo-txt">Clique para plantar</span>'
            elif lote.estado == "PLANTADO":
                restante = lote.tempo_restante()
                conteudo = f'<span class="emoji-status">{lote.planta_atual.emoji}</span><span>{lote.planta_atual.nome}</span><span class="tempo-txt">Crescendo: {restante}s</span>'
            else:
                conteudo = f'<span class="emoji-status">{lote.planta_atual.emoji}</span><span>COLHER</span>'
        elif lote.id_lote == proximo_lote:
            elemento.className = "lote DISPONIVEL"
            conteudo = f'<span class="emoji-status">🪙</span><span>COMPRAR LOTE</span><span class="tempo-txt">{preco_lote(lote.id_lote)} moedas</span>'
        else:
            elemento.className = "lote BLOQUEADO"
            elemento.disabled = True
            conteudo = '<span class="emoji-status">🔒</span><span>BLOQUEADO</span>'

        elemento.innerHTML = conteudo
    

# --- Cliques nos Terrenos ---
def ao_clicar_no_lote(event):
    id_lote = int(event.currentTarget.id.split("-")[1])
    lote = lotes[id_lote - 1]

    if lote.comprado:
        if lote.estado == "VAZIO":
            sucesso, mensagem = lote.plantar(semente_selecionada, jogador)
            mostrar_mensagem(mensagem)

            if sucesso:
                salvar_jogo()
        elif lote.estado == "PLANTADO":
            mostrar_mensagem(f"{lote.planta_atual.nome} está crescendo. Faltam {lote.tempo_restante()} segundos.")
        elif lote.estado == "PRONTO":
            sucesso, mensagem = lote.colher(jogador)
            mostrar_mensagem(mensagem)
            if sucesso:
                salvar_jogo()
    else:
        proximo_lote_obj = next((l for l in lotes if not l.comprado), None)
        if proximo_lote_obj is lote:
            preco = preco_lote(lote.id_lote)
            if jogador.moedas >= preco:
                jogador.moedas -= preco
                lote.comprado = True
                lote.estado = "VAZIO"
                salvar_jogo()
                mostrar_mensagem(f"Lote {lote.id_lote} comprado por {preco} moedas!")
            else:
                mostrar_mensagem("Você não tem moedas suficientes para comprar este lote.")

    atualizar_tela()

# --- Lógica Alternância de Abas Corrigida e Expandida ---
def alternar_para_fazenda(event):
    document.querySelector("#painel-plantacao").classList.add("ativa")
    document.querySelector("#painel-cozinha").classList.remove("ativa")
    document.querySelector("#painel-curral").classList.remove("ativa")
    
    document.querySelector("#btn-aba-fazenda").classList.add("ativa")
    document.querySelector("#btn-aba-cozinha").classList.remove("ativa")
    document.querySelector("#btn-aba-curral").classList.remove("ativa")
    mostrar_mensagem("Visualizando o campo de plantação.")

def alternar_para_cozinha(event):
    document.querySelector("#painel-plantacao").classList.remove("ativa")
    document.querySelector("#painel-cozinha").classList.add("ativa")
    document.querySelector("#painel-curral").classList.remove("ativa")
    
    document.querySelector("#btn-aba-fazenda").classList.remove("ativa")
    document.querySelector("#btn-aba-cozinha").classList.add("ativa")
    document.querySelector("#btn-aba-curral").classList.remove("ativa")
    mostrar_mensagem("Entrou na Cozinha! O que vamos preparar hoje?")

def alternar_para_curral(event):
    document.querySelector("#painel-plantacao").classList.remove("ativa")
    document.querySelector("#painel-cozinha").classList.remove("ativa")
    document.querySelector("#painel-curral").classList.add("ativa")
    
    document.querySelector("#btn-aba-fazenda").classList.remove("ativa")
    document.querySelector("#btn-aba-cozinha").classList.remove("ativa")
    document.querySelector("#btn-aba-curral").classList.add("ativa")
    mostrar_mensagem("Olhando o Curral. Espaço pronto para futuros animais!")


# --- Atualização na Função inicializar_botoes() ---
# Certifique-se de incluir a nova aba no mapeamento de cliques automáticos:
def inicializar_botoes():
    mapeamento = {
        "#btn-trigo": clicar_selecionar_trigo,
        "#btn-tomate": clicar_selecionar_tomate,
        "#btn-feijao": clicar_selecionar_feijao,
        "#vender-trigo": clicar_vender_trigo,
        "#vender-tomate": clicar_vender_tomate,
        "#vender-feijao": clicar_vender_feijao,
        "#btn-aba-fazenda": alternar_para_fazenda,
        "#btn-aba-cozinha": alternar_para_cozinha,
        "#btn-aba-curral": alternar_para_curral, # Nova amarração
        "#btn-craft-salada": cozinhar_salada_tomate
    }

    for seletor, funcao in mapeamento.items():
        elemento = document.querySelector(seletor)
        if elemento is not None:
            registrar_evento(elemento, "click", funcao)

    for lote in lotes:
        elemento_lote = document.querySelector(f"#lote-{lote.id_lote}")
        if elemento_lote is not None:
            registrar_evento(elemento_lote, "click", ao_clicar_no_lote)

def cozinhar_salada_tomate(event):
    if jogador.armazem.get("Tomate", 0) >= 2:
        jogador.armazem["Tomate"] -= 2
        jogador.moedas += 160
        mostrar_mensagem("🥗 Você preparou uma deliciosa Salada de Tomate e vendeu por 160 moedas!")
        salvar_jogo()
        atualizar_tela()
    else:
        mostrar_mensagem("Ingredientes insuficientes! Você precisa de pelo menos 2 Tomates.")


async def ciclo_atualizacao():
    while True:
        for lote in lotes:
            if lote.comprado:
                lote.checar_crescimento()
        atualizar_tela()
        await asyncio.sleep(1)

# --- Fluxo de Entrada Executado uma única vez ---
atualizar_tela()
carregar_jogo()
inicializar_botoes()
asyncio.ensure_future(ciclo_atualizacao())
