import streamlit as st
import urllib.request
import json
import os
import csv
import math
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Crypto AI Trader",
    page_icon="🤖",
    layout="wide"
)

HISTORICO = "historico_sinais.csv"
SALDO_INICIAL = 10000.0

CRYPTOS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "Cardano": "cardano",
    "Dogecoin": "dogecoin"
}

# ============================================================
# FUNÇÕES DE MERCADO
# ============================================================

def buscar_dados(crypto):
    coin_id = CRYPTOS[crypto]

    url = (
        "https://api.coingecko.com/api/v3/coins/"
        + coin_id
        + "/market_chart?vs_currency=usd&days=7&interval=hourly"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CryptoAITrader/2.0"
        }
    )

    with urllib.request.urlopen(request, timeout=15) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))

    precos = [float(x[1]) for x in dados["prices"]]

    if len(precos) < 25:
        raise Exception("Dados insuficientes para análise.")

    return precos


def preco_atual(precos):
    return precos[-1]


# ============================================================
# INDICADORES
# ============================================================

def media(precos, periodo):
    if len(precos) < periodo:
        return None

    return sum(precos[-periodo:]) / periodo


def calcular_rsi(precos, periodo=14):
    if len(precos) < periodo + 1:
        return 50.0

    ganhos = []
    perdas = []

    for i in range(len(precos) - periodo, len(precos)):
        diferenca = precos[i] - precos[i - 1]

        if diferenca > 0:
            ganhos.append(diferenca)
            perdas.append(0)
        else:
            ganhos.append(0)
            perdas.append(abs(diferenca))

    ganho_medio = sum(ganhos) / periodo
    perda_media = sum(perdas) / periodo

    if perda_media == 0:
        return 100.0

    rs = ganho_medio / perda_media

    return 100 - (100 / (1 + rs))


def calcular_momentum(precos, periodo=5):
    if len(precos) <= periodo:
        return 0.0

    anterior = precos[-periodo - 1]

    if anterior == 0:
        return 0.0

    return ((precos[-1] - anterior) / anterior) * 100


def calcular_volatilidade(precos, periodo=20):
    if len(precos) < periodo:
        return 0.0

    valores = precos[-periodo:]

    media_valor = sum(valores) / len(valores)

    if media_valor == 0:
        return 0.0

    variancia = sum(
        (x - media_valor) ** 2 for x in valores
    ) / len(valores)

    desvio = math.sqrt(variancia)

    return (desvio / media_valor) * 100


# ============================================================
# MOTOR DE APRENDIZADO
# ============================================================

def carregar_historico():
    if not os.path.exists(HISTORICO):
        return []

    registros = []

    try:
        with open(
            HISTORICO,
            "r",
            newline="",
            encoding="utf-8"
        ) as arquivo:

            leitor = csv.DictReader(arquivo)

            for linha in leitor:
                registros.append(linha)

    except Exception:
        return []

    return registros


def salvar_sinal(
    crypto,
    sinal,
    preco,
    confianca,
    rsi,
    momentum,
    media5,
    media20
):

    arquivo_existe = os.path.exists(HISTORICO)

    campos = [
        "data",
        "crypto",
        "sinal",
        "preco",
        "confianca",
        "rsi",
        "momentum",
        "media5",
        "media20",
        "resultado"
    ]

    with open(
        HISTORICO,
        "a",
        newline="",
        encoding="utf-8"
    ) as arquivo:

        escritor = csv.DictWriter(
            arquivo,
            fieldnames=campos
        )

        if not arquivo_existe:
            escritor.writeheader()

        escritor.writerow({
            "data": datetime.now().isoformat(),
            "crypto": crypto,
            "sinal": sinal,
            "preco": round(preco, 2),
            "confianca": round(confianca, 2),
            "rsi": round(rsi, 2),
            "momentum": round(momentum, 4),
            "media5": round(media5, 2),
            "media20": round(media20, 2),
            "resultado": "PENDENTE"
        })


def calcular_aprendizado(historico, crypto):
    registros = [
        x for x in historico
        if x.get("crypto") == crypto
        and x.get("resultado") in ["ACERTO", "ERRO"]
    ]

    if not registros:
        return {
            "acertos": 0,
            "erros": 0,
            "taxa": 50.0,
            "amostra": 0
        }

    acertos = sum(
        1 for x in registros
        if x["resultado"] == "ACERTO"
    )

    erros = sum(
        1 for x in registros
        if x["resultado"] == "ERRO"
    )

    total = acertos + erros

    taxa = (acertos / total) * 100

    return {
        "acertos": acertos,
        "erros": erros,
        "taxa": taxa,
        "amostra": total
    }


# ============================================================
# MOTOR DE SINAL
# ============================================================

def analisar(precos, crypto):

    atual = preco_atual(precos)

    media5 = media(precos, 5)
    media20 = media(precos, 20)

    rsi = calcular_rsi(precos)
    momentum = calcular_momentum(precos)
    volatilidade = calcular_volatilidade(precos)

    pontos_compra = 0
    pontos_venda = 0

    motivos_compra = []
    motivos_venda = []

    # --------------------------------------------------------
    # MÉDIAS
    # --------------------------------------------------------

    if media5 > media20:
        pontos_compra += 2
        motivos_compra.append("Média 5 acima da Média 20")

    elif media5 < media20:
        pontos_venda += 2
        motivos_venda.append("Média 5 abaixo da Média 20")

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if rsi < 35:
        pontos_compra += 2
        motivos_compra.append("RSI indica região de sobrevenda")

    elif rsi > 65:
        pontos_venda += 2
        motivos_venda.append("RSI indica região de sobrecompra")

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    if momentum > 0.20:
        pontos_compra += 2
        motivos_compra.append("Momentum positivo")

    elif momentum < -0.20:
        pontos_venda += 2
        motivos_venda.append("Momentum negativo")

    # --------------------------------------------------------
    # PREÇO X MÉDIA
    # --------------------------------------------------------

    if atual > media20:
        pontos_compra += 1
        motivos_compra.append("Preço acima da Média 20")

    elif atual < media20:
        pontos_venda += 1
        motivos_venda.append("Preço abaixo da Média 20")

    # --------------------------------------------------------
    # VOLATILIDADE
    # --------------------------------------------------------

    if volatilidade > 3:
        # mercado muito volátil:
        # reduzimos a confiança
        penalidade_volatilidade = 10
    else:
        penalidade_volatilidade = 0

    # --------------------------------------------------------
    # APRENDIZADO
    # --------------------------------------------------------

    historico = carregar_historico()

    aprendizado = calcular_aprendizado(
        historico,
        crypto
    )

    taxa_aprendizado = aprendizado["taxa"]

    if pontos_compra > pontos_venda:
        sinal = "COMPRA"

        diferenca = pontos_compra - pontos_venda

        confianca = 50 + (diferenca * 8)

        if taxa_aprendizado > 50:
            confianca += (taxa_aprendizado - 50) * 0.15

        motivo = " | ".join(motivos_compra)

    elif pontos_venda > pontos_compra:
        sinal = "VENDA"

        diferenca = pontos_venda - pontos_compra

        confianca = 50 + (diferenca * 8)

        if taxa_aprendizado > 50:
            confianca += (taxa_aprendizado - 50) * 0.15

        motivo = " | ".join(motivos_venda)

    else:
        sinal = "HOLD"

        confianca = 50

        motivo = (
            "Indicadores misturados. "
            "Aguardando confirmação."
        )

    confianca -= penalidade_volatilidade

    confianca = max(50, min(confianca, 95))

    return {
        "sinal": sinal,
        "confianca": confianca,
        "preco": atual,
        "media5": media5,
        "media20": media20,
        "rsi": rsi,
        "momentum": momentum,
        "volatilidade": volatilidade,
        "motivo": motivo,
        "aprendizado": aprendizado
    }


# ============================================================
# PAPER TRADING
# ============================================================

def inicializar_estado():

    if "saldo" not in st.session_state:
        st.session_state.saldo = SALDO_INICIAL

    if "posicao" not in st.session_state:
        st.session_state.posicao = None

    if "preco_entrada" not in st.session_state:
        st.session_state.preco_entrada = 0.0

    if "quantidade" not in st.session_state:
        st.session_state.quantidade = 0.0

    if "operacoes" not in st.session_state:
        st.session_state.operacoes = []


def executar_compra(preco, valor):

    if st.session_state.posicao is not None:
        return

    if valor <= 0:
        return

    if valor > st.session_state.saldo:
        valor = st.session_state.saldo

    if valor <= 0:
        return

    quantidade = valor / preco

    st.session_state.saldo -= valor
    st.session_state.quantidade = quantidade
    st.session_state.preco_entrada = preco
    st.session_state.posicao = "LONG"

    st.session_state.operacoes.append({
        "tipo": "COMPRA",
        "preco": preco,
        "valor": valor,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })


def executar_venda(preco):

    if st.session_state.posicao != "LONG":
        return

    valor = (
        st.session_state.quantidade
        * preco
    )

    st.session_state.saldo += valor

    lucro = (
        preco - st.session_state.preco_entrada
    ) * st.session_state.quantidade

    st.session_state.operacoes.append({
        "tipo": "VENDA",
        "preco": preco,
        "valor": valor,
        "lucro": lucro,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })

    st.session_state.posicao = None
    st.session_state.quantidade = 0.0
    st.session_state.preco_entrada = 0.0


# ============================================================
# INTERFACE
# ============================================================

inicializar_estado()

st.title("🤖 Crypto AI Trader")

st.caption(
    "Sistema de análise técnica + aprendizado "
    "estatístico + Paper Trading"
)

st.divider()

# ============================================================
# SELEÇÃO
# ============================================================

crypto = st.selectbox(
    "🪙 Criptomoeda",
    list(CRYPTOS.keys())
)

col1, col2 = st.columns([3, 1])

with col1:
    analisar_botao = st.button(
        "🔄 ANALISAR MERCADO",
        use_container_width=True
    )

with col2:
    atualizar = st.button(
        "♻️ Atualizar",
        use_container_width=True
    )

# ============================================================
# ANÁLISE
# ============================================================

if analisar_botao or atualizar or "analise" not in st.session_state:

    try:

        with st.spinner("Analisando mercado..."):

            precos = buscar_dados(crypto)

            resultado = analisar(
                precos,
                crypto
            )

            st.session_state.analise = resultado

    except Exception as e:

        st.error(
            "❌ Não foi possível realizar a análise."
        )

        st.warning(
            "A API pode estar temporariamente "
            "limitada ou indisponível."
        )

        st.stop()


resultado = st.session_state.analise

# ============================================================
# SINAL
# ============================================================

st.divider()

st.header("🤖 Sinal do Trader")

sinal = resultado["sinal"]

if sinal == "COMPRA":
    st.success("🟢 COMPRA")

elif sinal == "VENDA":
    st.error("🔴 VENDA")

else:
    st.warning("🟡 HOLD")

st.metric(
    "Confiança",
    f'{resultado["confianca"]:.1f}%'
)

st.info(
    "💡 " + resultado["motivo"]
)

# ============================================================
# MERCADO
# ============================================================

st.divider()

st.header("💰 Mercado")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Preço atual",
        f'${resultado["preco"]:,.2f}'
    )

with c2:
    st.metric(
        "Média 5",
        f'${resultado["media5"]:,.2f}'
    )

with c3:
    st.metric(
        "Média 20",
        f'${resultado["media20"]:,.2f}'
    )

# ============================================================
# INDICADORES
# ============================================================

st.header("📊 Indicadores")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "RSI",
        f'{resultado["rsi"]:.2f}'
    )

with c2:
    st.metric(
        "Momentum",
        f'{resultado["momentum"]:.2f}%'
    )

with c3:
    st.metric(
        "Volatilidade",
        f'{resultado["volatilidade"]:.2f}%'
    )

with c4:
    st.metric(
        "Sinal",
        sinal
    )

# ============================================================
# APRENDIZADO
# ============================================================

st.divider()

st.header("🧠 Motor de Aprendizado")

aprendizado = resultado["aprendizado"]

a1, a2, a3 = st.columns(3)

with a1:
    st.metric(
        "Taxa de acerto",
        f'{aprendizado["taxa"]:.1f}%'
    )

with a2:
    st.metric(
        "Acertos",
        aprendizado["acertos"]
    )

with a3:
    st.metric(
        "Operações avaliadas",
        aprendizado["amostra"]
    )

if aprendizado["amostra"] == 0:

    st.info(
        "🧠 O motor ainda está aprendendo. "
        "Ele precisa acumular operações avaliadas "
        "antes de ajustar seu comportamento."
    )

else:

    if aprendizado["taxa"] >= 60:

        st.success(
            "🧠 O histórico apresenta desempenho positivo."
        )

    elif aprendizado["taxa"] >= 50:

        st.warning(
            "🧠 O desempenho está equilibrado."
        )

    else:

        st.error(
            "🧠 O histórico apresenta desempenho abaixo "
            "de 50%. A estratégia precisa ser reavaliada."
        )

# ============================================================
# PAPER TRADING
# ============================================================

st.divider()

st.header("💵 Paper Trading")

p1, p2, p3 = st.columns(3)

with p1:
    st.metric(
        "Saldo disponível",
        f'${st.session_state.saldo:,.2f}'
    )

with p2:
    if st.session_state.posicao:
        st.metric(
            "Posição",
            st.session_state.posicao
        )
    else:
        st.metric(
            "Posição",
            "FORA"
        )

with p3:
    if st.session_state.posicao:
        lucro_atual = (
            resultado["preco"]
            - st.session_state.preco_entrada
        ) * st.session_state.quantidade

        st.metric(
            "Resultado",
            f'${lucro_atual:,.2f}'
        )
    else:
        st.metric(
            "Resultado",
            "$0.00"
        )

valor_operacao = st.number_input(
    "Valor da operação simulada (US$)",
    min_value=10.0,
    max_value=float(SALDO_INICIAL),
    value=1000.0,
    step=100.0
)

b1, b2 = st.columns(2)

with b1:

    if st.button(
        "🟢 COMPRA SIMULADA",
        use_container_width=True
    ):

        executar_compra(
            resultado["preco"],
            valor_operacao
        )

        st.success(
            "Compra simulada executada."
        )

with b2:

    if st.button(
        "🔴 VENDA SIMULADA",
        use_container_width=True
    ):

        executar_venda(
            resultado["preco"]
        )

        st.success(
            "Venda simulada executada."
        )

# ============================================================
# STOP / TAKE
# ============================================================

if st.session_state.posicao:

    entrada = st.session_state.preco_entrada

    stop = entrada * 0.98
    alvo = entrada * 1.04

    st.divider()

    st.header("🛡️ Gestão da operação")

    g1, g2 = st.columns(2)

    with g1:
        st.metric(
            "Stop Loss",
            f"${stop:,.2f}"
        )

    with g2:
        st.metric(
            "Take Profit",
            f"${alvo:,.2f}"
        )

    if resultado["preco"] <= stop:

        st.error(
            "⚠️ O preço atingiu o Stop Loss."
        )

    elif resultado["preco"] >= alvo:

        st.success(
            "🎯 O preço atingiu o Take Profit."
        )

# ============================================================
# HISTÓRICO
# ============================================================

st.divider()

st.header("📚 Histórico do sistema")

historico = carregar_historico()

historico_crypto = [
    x for x in historico
    if x.get("crypto") == crypto
]

if historico_crypto:

    ultimos = historico_crypto[-10:]

    st.dataframe(
        ultimos,
        use_container_width=True
    )

else:

    st.info(
        "Ainda não existem sinais registrados "
        "para esta criptomoeda."
    )

# ============================================================
# REGISTRAR NOVO SINAL
# ============================================================

st.divider()

if st.button(
    "🧠 Registrar sinal no aprendizado",
    use_container_width=True
):

    salvar_sinal(
        crypto,
        resultado["sinal"],
        resultado["preco"],
        resultado["confianca"],
        resultado["rsi"],
        resultado["momentum"],
        resultado["media5"],
        resultado["media20"]
    )

    st.success(
        "✅ Sinal registrado no histórico."
    )

    st.rerun()

# ============================================================
# AVISO
# ============================================================

st.divider()

st.caption(
    "⚠️ Este sistema é experimental e utiliza Paper Trading. "
    "Nenhuma ordem real é enviada para corretoras."
)
