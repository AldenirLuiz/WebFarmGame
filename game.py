from pyscript import document
from pyodide.ffi import create_proxy
from fazenda_logica import (
    Animal, Curral, Fogao, Jogador, LoteTerra, Planta, Receita
)
import asyncio
from html import escape
import json
from pyscript import window
from time import time

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
ANIMAIS_POR_CHAVE = {
    registro["key"]: Animal(
        chave=registro["key"],
        nome=registro["name"],
        emoji=registro["emoji"],
        custo=registro["cost"],
        alimento=registro["feed"],
        intervalo_alimentacao=registro["feed_interval"],
        tempo_crescimento=registro["growth_time"],
        tempo_reproducao=registro["reproduction_time"],
        capacidade=registro["max_per_corral"],
        valor_venda=registro["sale_value"]
    )
    for registro in dados_insumos["animals"]
}
PRECO_BASE_LOTE = dados_insumos["progression"]["plot_base_cost"]
PRECO_BASE_CURRAL = dados_insumos["progression"]["corral_base_cost"]
selecao_atual = None
ultimo_salvamento_progresso = 0
notificacoes_ativas = {
    "campo": {},
    "cozinha": {},
    "curral": {}
}
notificacoes_lidas = {
    "campo": set(),
    "cozinha": set(),
    "curral": set()
}
avisos_aba_token = {"campo": 0, "cozinha": 0, "curral": 0}
ABA_ATIVA = "campo"
TEMPO_AVISO_ABA = 4

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
currais = [
    Curral(1, comprado=True),
    *(Curral(id_curral) for id_curral in range(2, 10))
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
    return id_lote * PRECO_BASE_LOTE


def preco_curral(id_curral):
    return id_curral * PRECO_BASE_CURRAL


async def ocultar_aviso_aba_apos_tempo(chave_aba, token):
    await asyncio.sleep(TEMPO_AVISO_ABA)
    if avisos_aba_token[chave_aba] == token:
        seletor = {
            "campo": "#btn-aba-fazenda",
            "cozinha": "#btn-aba-cozinha",
            "curral": "#btn-aba-curral"
        }[chave_aba]
        document.querySelector(seletor).querySelector(
            ".tab-aviso"
        ).hidden = True


def mostrar_aviso_aba(chave_aba, texto):
    seletor = {
        "campo": "#btn-aba-fazenda",
        "cozinha": "#btn-aba-cozinha",
        "curral": "#btn-aba-curral"
    }[chave_aba]
    aviso = document.querySelector(seletor).querySelector(".tab-aviso")
    aviso.innerText = texto
    aviso.hidden = False
    avisos_aba_token[chave_aba] += 1
    asyncio.ensure_future(
        ocultar_aviso_aba_apos_tempo(
            chave_aba, avisos_aba_token[chave_aba]
        )
    )


def reconhecer_notificacoes_aba(chave_aba):
    notificacoes_lidas[chave_aba].update(
        notificacoes_ativas[chave_aba]
    )
    seletor = {
        "campo": "#btn-aba-fazenda",
        "cozinha": "#btn-aba-cozinha",
        "curral": "#btn-aba-curral"
    }[chave_aba]
    aba = document.querySelector(seletor)
    aba.querySelector(".tab-notificacao").hidden = True
    aba.querySelector(".tab-aviso").hidden = True
    avisos_aba_token[chave_aba] += 1


def atualizar_notificacoes_abas():
    novas_notificacoes = {
        "campo": {
            f"lote:{lote.id_lote}": (
                f"{lote.planta_atual.nome_exibicao} pronta para colher"
            )
            for lote in lotes
            if lote.comprado and lote.estado == "PRONTO"
        },
        "cozinha": {
            f"fogao:{fogao.id_fogao}": (
                f"{fogao.receita_atual.nome} pronto para vender"
            )
            for fogao in fogoes
            if fogao.comprado and fogao.estado == "PRONTO"
        },
        "curral": {}
    }
    for curral in currais:
        if not curral.comprado or curral.animal is None:
            continue
        if not curral.alimentado:
            novas_notificacoes["curral"][
                f"curral:{curral.id_curral}:alimento"
            ] = f"Baia {curral.id_curral} precisa de alimento"
        adultos = curral.adultos()
        if adultos:
            novas_notificacoes["curral"][
                f"curral:{curral.id_curral}:venda"
            ] = (
                (
                    f"1 adulto da baia {curral.id_curral} "
                    "disponível para venda"
                )
                if adultos == 1
                else (
                    f"{adultos} adultos da baia {curral.id_curral} "
                    "disponíveis para venda"
                )
            )

    configuracao_abas = (
        ("campo", "#btn-aba-fazenda", "Campo"),
        ("cozinha", "#btn-aba-cozinha", "Cozinha"),
        ("curral", "#btn-aba-curral", "Curral")
    )
    for chave_aba, seletor, nome_aba in configuracao_abas:
        ativos = novas_notificacoes[chave_aba]
        anteriores = notificacoes_ativas[chave_aba]
        novas = set(ativos) - set(anteriores)
        notificacoes_lidas[chave_aba].intersection_update(ativos)
        if chave_aba == ABA_ATIVA:
            notificacoes_lidas[chave_aba].update(ativos)
        elif novas:
            textos = [ativos[chave] for chave in sorted(novas)]
            resumo = "; ".join(textos[:2])
            if len(textos) > 2:
                resumo += f"; e mais {len(textos) - 2}"
            mostrar_aviso_aba(chave_aba, resumo)

        notificacoes_ativas[chave_aba] = ativos
        aba = document.querySelector(seletor)
        indicador = aba.querySelector(".tab-notificacao")
        pendentes = set(ativos) - notificacoes_lidas[chave_aba]
        indicador.innerText = str(len(pendentes))
        indicador.hidden = not pendentes
        detalhes = "; ".join(
            ativos[chave] for chave in sorted(ativos)
        )
        descricao = (
            nome_aba
            if not ativos
            else f"{nome_aba}: {detalhes}"
        )
        aba.setAttribute("aria-label", descricao)
        aba.setAttribute("title", descricao)


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

        currais_salvos = dados.get("currais", [])
        for i, curral in enumerate(currais):
            if i >= len(currais_salvos):
                continue

            salvo = currais_salvos[i]
            curral.comprado = bool(salvo["comprado"])
            curral.animal = None
            curral.animais = []
            if not curral.comprado:
                curral.alimentado = False
                curral.proxima_alimentacao = None
                curral.proxima_reproducao = None
                continue

            chave_animal = salvo.get("animal")
            if chave_animal not in ANIMAIS_POR_CHAVE:
                continue

            curral.animal = ANIMAIS_POR_CHAVE[chave_animal]
            curral.animais = [
                max(0.0, float(idade))
                for idade in salvo.get("idades", [])
            ]
            curral.alimentado = bool(salvo.get("alimentado", False))
            curral.ultima_atualizacao = float(
                salvo.get("ultima_atualizacao", time())
            )
            curral.proxima_alimentacao = salvo.get(
                "proxima_alimentacao"
            )
            if curral.proxima_alimentacao is not None:
                curral.proxima_alimentacao = float(
                    curral.proxima_alimentacao
                )
            curral.proxima_reproducao = salvo.get(
                "proxima_reproducao"
            )
            if curral.proxima_reproducao is not None:
                curral.proxima_reproducao = float(
                    curral.proxima_reproducao
                )
            curral.processar_ciclo(jogador)

        atualizar_tela()
        mostrar_mensagem("Progresso carregado com sucesso!")

    except Exception as e:
        print("Erro ao carregar jogo:", e)
        mostrar_mensagem("Erro ao carregar o salvamento.")
        
def salvar_jogo():
    global ultimo_salvamento_progresso
    dados_salvamento = {
        "versao": 4,
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
        ],
        "currais": [
            {
                "id": curral.id_curral,
                "comprado": curral.comprado,
                "animal": curral.animal.chave if curral.animal else None,
                "idades": curral.animais,
                "alimentado": curral.alimentado,
                "ultima_atualizacao": curral.ultima_atualizacao,
                "proxima_alimentacao": curral.proxima_alimentacao,
                "proxima_reproducao": curral.proxima_reproducao
            }
            for curral in currais
        ]
    }

    window.localStorage.setItem(
        "fazenda_paraiso_save",
        json.dumps(dados_salvamento)
    )
    ultimo_salvamento_progresso = time()
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
    for seletor in (
        "#seletor-sementes", "#seletor-receitas", "#seletor-animais"
    ):
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
    elif tipo == "receita":
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
    else:
        painel = document.querySelector("#seletor-animais")
        if tipo == "animal":
            opcoes = []
            for animal in ANIMAIS_POR_CHAVE.values():
                alimento = ", ".join(
                    f"{quantidade} "
                    f"{PLANTAS_POR_NOME[nome].nome_exibicao}"
                    for nome, quantidade in animal.alimento.items()
                )
                pode_comprar = jogador.moedas >= animal.custo
                status = (
                    "Pronto para comprar"
                    if pode_comprar else "Moedas insuficientes"
                )
                atributo_disabled = "" if pode_comprar else "disabled"
                opcoes.append(
                    f'<button class="opcao-selecao" data-chave="'
                    f'{escape(animal.chave, quote=True)}" '
                    f'{atributo_disabled}>'
                    f'<span class="opcao-emoji">{escape(animal.emoji)}</span>'
                    f'<span class="opcao-nome">{escape(animal.nome)}</span>'
                    f'<span class="opcao-detalhe">Preço: {animal.custo} '
                    f'moedas · Alimentação: {alimento} a cada '
                    f'{animal.intervalo_alimentacao}s</span>'
                    f'<span class="opcao-status">Cresce em '
                    f'{animal.tempo_crescimento}s · '
                    f'Venda adulta: {animal.valor_venda} · {status}</span>'
                    '</button>'
                )
            titulo = f"Escolha um animal para a baia {objeto.id_curral}"
        else:
            animal = objeto.animal
            adultos = objeto.adultos()
            alimento = ", ".join(
                f"{quantidade * len(objeto.animais)} "
                f"{PLANTAS_POR_NOME[nome].nome_exibicao}"
                for nome, quantidade in animal.alimento.items()
            )
            restante = objeto.tempo_para_crescer()
            status_alimentacao = (
                "Alimentado"
                if objeto.alimentado else "Aguardando alimento"
            )
            status_crescimento = (
                "Pronto para venda"
                if adultos else f"Crescimento: {restante}s"
            )
            habilitar_venda = adultos > 0
            atributo_venda_disabled = "" if habilitar_venda else "disabled"
            pode_comprar = (
                len(objeto.animais) < animal.capacidade
                and jogador.moedas >= animal.custo
            )
            atributo_compra_disabled = "" if pode_comprar else "disabled"
            opcoes = [
                (
                    '<div class="detalhe-animal">'
                    f'<span class="opcao-emoji">{escape(animal.emoji)}</span>'
                    f'<strong>{escape(animal.nome)} · '
                    f'{len(objeto.animais)}/{animal.capacidade}</strong>'
                    f'<span>{adultos} adulto(s) · '
                    f'{len(objeto.animais) - adultos} filhote(s)</span>'
                    f'<span>{status_alimentacao} · Próxima ração: '
                    f'{alimento}</span>'
                    f'<span>{status_crescimento}</span>'
                    '</div>'
                    '<button class="opcao-selecao acao-animal" '
                    'data-action="buy" '
                    f'{atributo_compra_disabled}>'
                    '<span class="opcao-emoji">➕</span>'
                    '<span class="opcao-nome">Comprar mais um</span>'
                    f'<span class="opcao-detalhe">Adicionar um jovem '
                    f'{escape(animal.nome)} · {animal.custo} moedas'
                    '</span></button>'
                    '<button class="opcao-selecao acao-animal" '
                    'data-action="sell" '
                    f'{atributo_venda_disabled}>'
                    '<span class="opcao-emoji">🪙</span>'
                    '<span class="opcao-nome">Vender 1 adulto</span>'
                    f'<span class="opcao-detalhe">+{animal.valor_venda} '
                    'moedas · A reprodução acontece quando houver dois '
                    'adultos e espaço na baia.</span></button>'
                )
            ]
            titulo = f"Baia {objeto.id_curral}"

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
    alvo = event.target.closest(
        "[data-chave], [data-action], [data-cancelar]"
    )
    if alvo is None:
        return
    if alvo.hasAttribute("data-cancelar"):
        fechar_seletor()
        return
    if selecao_atual is None:
        return

    tipo, objeto = selecao_atual
    acao = alvo.getAttribute("data-action")
    if tipo == "semente":
        chave = alvo.getAttribute("data-chave")
        planta = PLANTAS_POR_NOME[chave]
        sucesso, mensagem = objeto.plantar(planta, jogador)
    elif tipo == "receita":
        chave = alvo.getAttribute("data-chave")
        receita = RECEITAS_POR_NOME[chave]
        sucesso, mensagem = objeto.cozinhar(receita, jogador)
    elif tipo == "animal":
        chave = alvo.getAttribute("data-chave")
        animal = ANIMAIS_POR_CHAVE[chave]
        sucesso, mensagem = objeto.comprar_animal(animal, jogador)
    elif acao == "buy":
        sucesso, mensagem = objeto.adicionar_animal(jogador)
    elif acao == "sell":
        sucesso, mensagem = objeto.vender_adulto(jogador)
    else:
        return

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
    document.querySelector("#txt-lotes-comprados").innerText = str(
        sum(lote.comprado for lote in lotes)
    )
    document.querySelector("#txt-currais-comprados").innerText = str(
        sum(curral.comprado for curral in currais)
    )
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

    proximo_curral = next(
        (curral.id_curral for curral in currais if not curral.comprado),
        None
    )
    for curral in currais:
        elemento = document.querySelector(f"#curral-{curral.id_curral}")
        elemento.disabled = False

        if not curral.comprado:
            if curral.id_curral == proximo_curral:
                preco = preco_curral(curral.id_curral)
                elemento.className = "curral DISPONIVEL"
                conteudo = (
                    '<span class="emoji-status">🪙</span>'
                    '<span>DESBLOQUEAR BAIA</span>'
                    f'<span class="tempo-txt">{preco} moedas</span>'
                )
            else:
                elemento.className = "curral BLOQUEADO"
                elemento.disabled = True
                conteudo = (
                    '<span class="emoji-status">🔒</span>'
                    '<span>BAIA BLOQUEADA</span>'
                )
        elif curral.animal is None:
            elemento.className = "curral VAZIO"
            conteudo = (
                '<span class="emoji-status">🛖</span>'
                '<span>BAIA LIVRE</span>'
                '<span class="tempo-txt">Clique para escolher animais</span>'
            )
        else:
            animal = curral.animal
            adultos = curral.adultos()
            filhotes = len(curral.animais) - adultos
            status_alimentacao = (
                "Alimentado"
                if curral.alimentado else "Precisa de alimento"
            )
            if adultos:
                status_crescimento = f"{adultos} adulto(s)"
            else:
                status_crescimento = (
                    f"Cresce em {curral.tempo_para_crescer()}s"
                )
            elemento.className = "curral OCUPADO"
            conteudo = (
                f'<span class="emoji-status">{escape(animal.emoji)}</span>'
                f'<span>{escape(animal.nome)} · '
                f'{len(curral.animais)}/{animal.capacidade}</span>'
                f'<span class="tempo-txt">{status_crescimento} · '
                f'{filhotes} filhote(s)</span>'
                f'<span class="tempo-txt">{status_alimentacao}</span>'
            )
        elemento.innerHTML = conteudo

    atualizar_notificacoes_abas()

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


def ao_clicar_no_curral(event):
    id_curral = int(event.currentTarget.id.split("-")[1])
    curral = currais[id_curral - 1]

    if curral.comprado:
        if curral.animal is None:
            abrir_seletor("animal", curral)
            mostrar_mensagem("Escolha um animal para esta baia.")
        else:
            abrir_seletor("animal_options", curral)
            mostrar_mensagem(
                f"Gerenciando a baia de {curral.animal.nome}."
            )
    else:
        proximo_curral = next(
            (item for item in currais if not item.comprado), None
        )
        if proximo_curral is curral:
            preco = preco_curral(curral.id_curral)
            if jogador.moedas >= preco:
                jogador.moedas -= preco
                curral.comprado = True
                salvar_jogo()
                mostrar_mensagem(
                    f"Baia {curral.id_curral} desbloqueada por "
                    f"{preco} moedas!"
                )
            else:
                mostrar_mensagem(
                    "Você não tem moedas suficientes para desbloquear "
                    "esta baia."
                )

    atualizar_tela()


# --- Lógica Alternância de Abas Corrigida e Expandida ---
def alternar_para_fazenda(event):
    global ABA_ATIVA
    fechar_seletor()
    ABA_ATIVA = "campo"
    reconhecer_notificacoes_aba(ABA_ATIVA)
    document.querySelector("#painel-plantacao").classList.add("ativa")
    document.querySelector("#painel-cozinha").classList.remove("ativa")
    document.querySelector("#painel-curral").classList.remove("ativa")
    
    document.querySelector("#btn-aba-fazenda").classList.add("ativa")
    document.querySelector("#btn-aba-cozinha").classList.remove("ativa")
    document.querySelector("#btn-aba-curral").classList.remove("ativa")
    mostrar_mensagem("Visualizando o campo de plantação.")

def alternar_para_cozinha(event):
    global ABA_ATIVA
    fechar_seletor()
    ABA_ATIVA = "cozinha"
    reconhecer_notificacoes_aba(ABA_ATIVA)
    document.querySelector("#painel-plantacao").classList.remove("ativa")
    document.querySelector("#painel-cozinha").classList.add("ativa")
    document.querySelector("#painel-curral").classList.remove("ativa")
    
    document.querySelector("#btn-aba-fazenda").classList.remove("ativa")
    document.querySelector("#btn-aba-cozinha").classList.add("ativa")
    document.querySelector("#btn-aba-curral").classList.remove("ativa")
    mostrar_mensagem("Entrou na Cozinha! O que vamos preparar hoje?")

def alternar_para_curral(event):
    global ABA_ATIVA
    fechar_seletor()
    ABA_ATIVA = "curral"
    reconhecer_notificacoes_aba(ABA_ATIVA)
    document.querySelector("#painel-plantacao").classList.remove("ativa")
    document.querySelector("#painel-cozinha").classList.remove("ativa")
    document.querySelector("#painel-curral").classList.add("ativa")
    
    document.querySelector("#btn-aba-fazenda").classList.remove("ativa")
    document.querySelector("#btn-aba-cozinha").classList.remove("ativa")
    document.querySelector("#btn-aba-curral").classList.add("ativa")
    mostrar_mensagem(
        "Alimente seus animais com as colheitas para fazê-los crescer."
    )


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

    for seletor in (
        "#seletor-sementes", "#seletor-receitas", "#seletor-animais"
    ):
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

    for curral in currais:
        elemento_curral = document.querySelector(
            f"#curral-{curral.id_curral}"
        )
        if elemento_curral is not None:
            registrar_evento(
                elemento_curral, "click", ao_clicar_no_curral
            )


async def ciclo_atualizacao():
    while True:
        for lote in lotes:
            if lote.comprado:
                lote.checar_crescimento()
        for fogao in fogoes:
            if fogao.comprado:
                fogao.checar_cozinhar()
        eventos_animais = []
        for curral in currais:
            eventos_animais.extend(curral.processar_ciclo(jogador))
        if eventos_animais:
            mostrar_mensagem(" ".join(eventos_animais))
        if time() - ultimo_salvamento_progresso >= 5:
            salvar_jogo()
        atualizar_tela()
        await asyncio.sleep(1)

# --- Fluxo de Entrada Executado uma única vez ---
inicializar_controles_dinamicos()
atualizar_tela()
carregar_jogo()
inicializar_botoes()
asyncio.ensure_future(ciclo_atualizacao())
