from pyscript import document
from pyodide.ffi import create_proxy
from fazenda_logica import Jogador, Planta, LoteTerra, Receita, Fogao
import asyncio
from html import escape
import json
from pyscript import window

# --- Inicialização dos Objetos ---
with open("insumos.json", "r", encoding="utf-8") as arquivo_insumos:
    dados_insumos = json.load(arquivo_insumos)

plantas = [
    Planta(
        nome=registro["key"],
        nome_exibicao=registro["name"],
        tempo_crescimento=registro["time_to_harvest"],
        custo=registro["cost"],
        valor_venda=registro["sale_value"],
        emoji=registro["emoji"]
    )
    for registro in dados_insumos["plants"]
]
PLANTAS_POR_NOME = {planta.nome: planta for planta in plantas}
jogador = Jogador(produtos=[planta.nome for planta in plantas])

RECEITAS_POR_NOME = {
    registro["name"]: Receita(
        registro["name"],
        registro["ingredients"],
        registro["sale_value"],
        registro["emoji"],
        registro["cook_time"]
    )
    for registro in dados_insumos["recipes"]
}
selecao_atual = None

# Criados os 9 lotes conforme seu arquivo atualizado
lotes = [
    LoteTerra(1, comprado=True),
    LoteTerra(2), LoteTerra(3), LoteTerra(4), LoteTerra(5), LoteTerra(6),
    LoteTerra(7), LoteTerra(8), LoteTerra(9)
]
fogoes = [
    Fogao(1, comprado=True),
    Fogao(2), Fogao(3), Fogao(4), Fogao(5), Fogao(6),
    Fogao(7), Fogao(8), Fogao(9)
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

        armazem_salvo = dados.get("armazem", {})
        jogador.armazem = {
            nome: int(armazem_salvo.get(nome, 0))
            for nome in PLANTAS_POR_NOME
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

        fogoes_salvos = dados.get("fogoes", [])
        for i, fogao in enumerate(fogoes):
            if i >= len(fogoes_salvos):
                continue

            salvo = fogoes_salvos[i]
            fogao.comprado = bool(salvo["comprado"])
            if not fogao.comprado:
                fogao.estado = "BLOQUEADO"
                fogao.receita_atual = None
                fogao.timestamp_cozimento = None
                continue

            estado = salvo["estado"]
            nome_receita = salvo.get("receita")
            if estado in ("COZINHANDO", "PRONTO") and nome_receita:
                fogao.receita_atual = RECEITAS_POR_NOME[nome_receita]
                fogao.timestamp_cozimento = float(
                    salvo["timestamp_cozimento"]
                )
                fogao.estado = estado
                fogao.checar_cozinhar()
            else:
                fogao.estado = "VAZIO"
                fogao.receita_atual = None
                fogao.timestamp_cozimento = None

        atualizar_tela()
        mostrar_mensagem("Progresso carregado com sucesso!")

    except Exception as e:
        print("Erro ao carregar jogo:", e)
        mostrar_mensagem("Erro ao carregar o salvamento.")
        
def salvar_jogo():
    dados_salvamento = {
        "versao": 3,
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
        ],
        "fogoes": [
            {
                "id": fogao.id_fogao,
                "comprado": fogao.comprado,
                "estado": fogao.estado,
                "receita": (
                    fogao.receita_atual.nome
                    if fogao.receita_atual else None
                ),
                "timestamp_cozimento": fogao.timestamp_cozimento
            }
            for fogao in fogoes
        ]
    }

    window.localStorage.setItem(
        "fazenda_paraiso_save",
        json.dumps(dados_salvamento)
    )
# --- Mercado e Vendas ---
def vender(nome, valor, nome_exibicao=None):
    sucesso, mensagem = jogador.vender(nome, valor, nome_exibicao)
    mostrar_mensagem(mensagem)
    if sucesso:
        salvar_jogo()
    atualizar_tela()


def ao_vender_planta(event):
    chave = event.currentTarget.id.removeprefix("vender-").capitalize()
    planta = PLANTAS_POR_NOME[chave]
    vender(planta.nome, planta.valor_venda, planta.nome_exibicao)


def inicializar_controles_dinamicos():
    document.querySelector("#lista-estoque").innerHTML = "".join(
        (
            '<div class="item-estoque">'
            f'{escape(planta.emoji)} {escape(planta.nome_exibicao)}: '
            f'<span id="estoque-{escape(planta.nome.lower(), quote=True)}">'
            '0</span></div>'
        )
        for planta in plantas
    )
    document.querySelector("#lista-mercado").innerHTML = "".join(
        (
            f'<button id="vender-{escape(planta.nome.lower(), quote=True)}" '
            'class="botao-venda">'
            f'Vender {escape(planta.nome_exibicao)} '
            f'(+${planta.valor_venda})</button>'
        )
        for planta in plantas
    )


def fechar_seletor():
    global selecao_atual
    for seletor in ("#seletor-sementes", "#seletor-receitas"):
        painel = document.querySelector(seletor)
        painel.classList.remove("aberto")
        painel.innerHTML = ""
    selecao_atual = None


def abrir_seletor(tipo, objeto):
    global selecao_atual
    fechar_seletor()
    selecao_atual = (tipo, objeto)

    if tipo == "semente":
        painel = document.querySelector("#seletor-sementes")
        opcoes = []
        for planta in plantas:
            pode_comprar = jogador.moedas >= planta.custo
            status = (
                f"Cresce em {planta.tempo_crescimento}s"
                if pode_comprar else "Moedas insuficientes"
            )
            atributo_disabled = "" if pode_comprar else "disabled"
            opcoes.append(
                f'<button class="opcao-selecao" data-chave="'
                f'{escape(planta.nome, quote=True)}" {atributo_disabled}>'
                f'<span class="opcao-emoji">{escape(planta.emoji)}</span>'
                f'<span class="opcao-nome">'
                f'{escape(planta.nome_exibicao)}</span>'
                f'<span class="opcao-detalhe">Semente: {planta.custo} '
                f'moedas · {status}</span></button>'
            )
        titulo = f"Escolha uma semente para o lote {objeto.id_lote}"
    else:
        painel = document.querySelector("#seletor-receitas")
        opcoes = []
        for receita in RECEITAS_POR_NOME.values():
            tem_ingredientes = all(
                jogador.armazem.get(nome, 0) >= quantidade
                for nome, quantidade
                in receita.ingredientes_requeridos.items()
            )
            ingredientes = ", ".join(
                f"{quantidade} "
                f"{PLANTAS_POR_NOME[nome].nome_exibicao}"
                for nome, quantidade
                in receita.ingredientes_requeridos.items()
            )
            status = (
                "Pronta para preparar"
                if tem_ingredientes else "Faltam ingredientes"
            )
            atributo_disabled = "" if tem_ingredientes else "disabled"
            opcoes.append(
                f'<button class="opcao-selecao" data-chave="'
                f'{escape(receita.nome, quote=True)}" {atributo_disabled}>'
                f'<span class="opcao-emoji">{escape(receita.emoji)}</span>'
                f'<span class="opcao-nome">'
                f'{escape(receita.nome)}</span>'
                f'<span class="opcao-detalhe">{ingredientes} · '
                f'{receita.tempo_cozimento}s · '
                f'+{receita.valor_venda} moedas</span>'
                f'<span class="opcao-status">{status}</span></button>'
            )
        titulo = f"Escolha o que preparar no fogão {objeto.id_fogao}"

    painel.innerHTML = (
        '<div class="seletor-cabecalho">'
        f'<h3>{escape(titulo)}</h3>'
        '<button class="fechar-seletor" data-cancelar '
        'aria-label="Fechar">×</button></div>'
        f'<div class="opcoes-selecao">{"".join(opcoes)}</div>'
    )
    painel.classList.add("aberto")


def escolher_opcao(event):
    global selecao_atual
    alvo = event.target.closest("[data-chave], [data-cancelar]")
    if alvo is None:
        return
    if alvo.hasAttribute("data-cancelar"):
        fechar_seletor()
        return
    if selecao_atual is None:
        return

    tipo, objeto = selecao_atual
    chave = alvo.getAttribute("data-chave")
    if tipo == "semente":
        planta = PLANTAS_POR_NOME[chave]
        sucesso, mensagem = objeto.plantar(planta, jogador)
    else:
        receita = RECEITAS_POR_NOME[chave]
        sucesso, mensagem = objeto.cozinhar(receita, jogador)

    mostrar_mensagem(mensagem)
    if sucesso:
        salvar_jogo()
    fechar_seletor()
    atualizar_tela()


# --- Interface Gráfica ---
def atualizar_tela():
    total = jogador.total_itens_no_armazem()
    document.querySelector("#txt-moedas").innerText = str(jogador.moedas)
    document.querySelector("#txt-total-estoque").innerText = str(total)
    document.querySelector("#txt-max-estoque").innerText = str(jogador.capacidade_maxima)

    porcentagem = (total / jogador.capacidade_maxima) * 100
    document.querySelector("#barra-progresso").style.width = f"{porcentagem}%"
    for planta in plantas:
        quantidade = jogador.armazem.get(planta.nome, 0)
        document.querySelector(
            f"#estoque-{planta.nome.lower()}"
        ).innerText = str(quantidade)
        document.querySelector(
            f"#vender-{planta.nome.lower()}"
        ).disabled = quantidade == 0

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
                conteudo = f'<span class="emoji-status">{lote.planta_atual.emoji}</span><span>{lote.planta_atual.nome_exibicao}</span><span class="tempo-txt">Crescendo: {restante}s</span>'
            else:
                conteudo = f'<span class="emoji-status">{lote.planta_atual.emoji}</span><span>COLHER {lote.planta_atual.nome_exibicao}</span>'
        elif lote.id_lote == proximo_lote:
            elemento.className = "lote DISPONIVEL"
            conteudo = f'<span class="emoji-status">🪙</span><span>COMPRAR LOTE</span><span class="tempo-txt">{preco_lote(lote.id_lote)} moedas</span>'
        else:
            elemento.className = "lote BLOQUEADO"
            elemento.disabled = True
            conteudo = '<span class="emoji-status">🔒</span><span>BLOQUEADO</span>'

        elemento.innerHTML = conteudo

    proximo_fogao = next((f.id_fogao for f in fogoes if not f.comprado), None)

    for fogao in fogoes:
        elemento = document.querySelector(f"#fogao-{fogao.id_fogao}")
        if elemento is None:
            continue

        elemento.disabled = False
        if fogao.comprado:
            elemento.className = f"fogao {fogao.estado}"
            if fogao.estado == "VAZIO":
                conteudo = (
                    '<span class="emoji-status">🍳</span>'
                    '<span>FOGÃO VAZIO</span>'
                    '<span class="tempo-txt">Clique para escolher uma receita</span>'
                )
            elif fogao.estado == "COZINHANDO":
                restante = fogao.tempo_restante()
                conteudo = (
                    f'<span class="emoji-status">'
                    f'{fogao.receita_atual.emoji}</span>'
                    f'<span>{fogao.receita_atual.nome}</span>'
                    f'<span class="tempo-txt">Cozinhando: {restante}s</span>'
                )
            else:
                conteudo = (
                    f'<span class="emoji-status">'
                    f'{fogao.receita_atual.emoji}</span>'
                    f'<span>{fogao.receita_atual.nome}</span>'
                    '<span class="tempo-txt">Pronto! Clique para vender</span>'
                )
        elif fogao.id_fogao == proximo_fogao:
            preco = preco_lote(fogao.id_fogao)
            elemento.className = "fogao DISPONIVEL"
            conteudo = (
                '<span class="emoji-status">🪙</span>'
                '<span>COMPRAR FOGÃO</span>'
                f'<span class="tempo-txt">{preco} moedas</span>'
            )
        else:
            elemento.className = "fogao BLOQUEADO"
            elemento.disabled = True
            conteudo = (
                '<span class="emoji-status">🔒</span>'
                '<span>BLOQUEADO</span>'
            )

        elemento.innerHTML = conteudo

# --- Cliques nos Terrenos ---
def ao_clicar_no_lote(event):
    id_lote = int(event.currentTarget.id.split("-")[1])
    lote = lotes[id_lote - 1]

    if lote.comprado:
        if lote.estado == "VAZIO":
            abrir_seletor("semente", lote)
            mostrar_mensagem("Escolha uma semente para plantar.")
        elif lote.estado == "PLANTADO":
            mostrar_mensagem(f"{lote.planta_atual.nome_exibicao} está crescendo. Faltam {lote.tempo_restante()} segundos.")
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


def ao_clicar_no_fogao(event):
    id_fogao = int(event.currentTarget.id.split("-")[1])
    fogao = fogoes[id_fogao - 1]

    if fogao.comprado:
        if fogao.estado == "VAZIO":
            abrir_seletor("receita", fogao)
            mostrar_mensagem("Escolha uma receita para preparar.")
        elif fogao.estado == "COZINHANDO":
            mostrar_mensagem(
                f"{fogao.receita_atual.nome} está cozinhando. "
                f"Faltam {fogao.tempo_restante()} segundos."
            )
        else:
            sucesso, mensagem = fogao.colher(jogador)
            mostrar_mensagem(mensagem)
            if sucesso:
                salvar_jogo()
    else:
        proximo_fogao_obj = next(
            (f for f in fogoes if not f.comprado), None
        )
        if proximo_fogao_obj is fogao:
            preco = preco_lote(fogao.id_fogao)
            if jogador.moedas >= preco:
                jogador.moedas -= preco
                fogao.comprado = True
                fogao.estado = "VAZIO"
                salvar_jogo()
                mostrar_mensagem(
                    f"Fogão {fogao.id_fogao} comprado por {preco} moedas!"
                )
            else:
                mostrar_mensagem(
                    "Você não tem moedas suficientes para comprar este fogão."
                )

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
        "#btn-aba-fazenda": alternar_para_fazenda,
        "#btn-aba-cozinha": alternar_para_cozinha,
        "#btn-aba-curral": alternar_para_curral,
    }

    for seletor, funcao in mapeamento.items():
        elemento = document.querySelector(seletor)
        if elemento is not None:
            registrar_evento(elemento, "click", funcao)

    for seletor in ("#seletor-sementes", "#seletor-receitas"):
        registrar_evento(
            document.querySelector(seletor),
            "click",
            escolher_opcao
        )

    for planta in plantas:
        registrar_evento(
            document.querySelector(f"#vender-{planta.nome.lower()}"),
            "click",
            ao_vender_planta
        )

    for lote in lotes:
        elemento_lote = document.querySelector(f"#lote-{lote.id_lote}")
        if elemento_lote is not None:
            registrar_evento(elemento_lote, "click", ao_clicar_no_lote)

    for fogao in fogoes:
        elemento_fogao = document.querySelector(f"#fogao-{fogao.id_fogao}")
        if elemento_fogao is not None:
            registrar_evento(elemento_fogao, "click", ao_clicar_no_fogao)


async def ciclo_atualizacao():
    while True:
        for lote in lotes:
            if lote.comprado:
                lote.checar_crescimento()
        for fogao in fogoes:
            if fogao.comprado:
                fogao.checar_cozinhar()
        atualizar_tela()
        await asyncio.sleep(1)

# --- Fluxo de Entrada Executado uma única vez ---
inicializar_controles_dinamicos()
atualizar_tela()
carregar_jogo()
inicializar_botoes()
asyncio.ensure_future(ciclo_atualizacao())
