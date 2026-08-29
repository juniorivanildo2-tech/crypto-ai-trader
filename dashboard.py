import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime


# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="Crypto AI Trader V3",
    page_icon="🤖",
    layout="centered"
)

COINS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "Cardano": "cardano",
    "Dogecoin": "dogecoin"
}


# =========================================================
# ESTADO DO PAPER TRADING
# =========================================================

if "saldo" not in st.session_state:
    st.session_state.saldo = 10000.0

if "moedas" not in st.session_state:
    st.session_state.moedas = 0.0

if "preco_entrada" not in st.session_state:
    st.session_state.preco_entrada = 0.0

if "valor_entrada" not in st.session_state:
    st.session_state.valor_entrada = 0.0

if "operacao_aberta" not in st.session_state:
    st.session_state.operacao_aberta = False

if "historico" not in st.session_state:
    st.session_state.historico = []

if "acertos" not in st.session_state:
    st.session_state.acertos = 0

if "erros" not in st.session_state:
    st.session_state.erros = 0

if "analise" not in st.session_state:
    st.session_state.analise = None

if "precos" not in st.session_state:
    st.session_state.precos = None


# =========================================================
# FUNÇÃO PARA PEGAR DADOS
# =========================================================

def buscar_mercado(coin_id):

    url = (
        "https://api.coingecko.com/api/v3/coins/"
        f"{coin_id}/market_chart"
        "?vs_currency=usd&days=7&interval=hourly"
    )

    resposta = requests.get(
        url,
        timeout=20,
        headers={
            "accept": "application/json",
            "user-agent": "CryptoAITrader/3.0"
        }
    )

    resposta.raise_for_status()

    dados = resposta.json()

    precos = dados.get("prices", [])
    volumes = dados.get("total_volumes", [])

    if len(precos) < 30:
        raise Exception(
            "O mercado retornou poucos dados."
        )

    df = pd.DataFrame(
        precos,
        columns=["timestamp", "price"]
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms"
    )

    if volumes:

        volume_df = pd.DataFrame(
            volumes,
            columns=["timestamp", "volume"]
        )

        volume_df["timestamp"] = pd.to_datetime(
            volume_df["timestamp"],
            unit="ms"
        )

        df = pd.merge_asof(
            df.sort_values("timestamp"),
            volume_df.sort_values("timestamp"),
            on="timestamp"
        )

    else:

        df["volume"] = 0.0

    return df


# =========================================================
# RSI
# =========================================================

def calcular_rsi(series, periodo=14):

    delta = series.diff()

    ganhos = delta.clip(lower=0)
    perdas = -delta.clip(upper=0)

    media_ganho = ganhos.rolling(
        periodo
    ).mean()

    media_perda = perdas.rolling(
        periodo
    ).mean()

    rs = media_ganho / media_perda.replace(
        0,
        float("nan")
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi.fillna(50)


# =========================================================
# EMA
# =========================================================

def calcular_ema(series, periodo):

    return series.ewm(
        span=periodo,
        adjust=False
    ).mean()


# =========================================================
# MACD
# =========================================================

def calcular_macd(series):

    ema12 = calcular_ema(
        series,
        12
    )

    ema26 = calcular_ema(
        series,
        26
    )

    macd = ema12 - ema26

    sinal = calcular_ema(
        macd,
        9
    )

    histograma = macd - sinal

    return macd, sinal, histograma


# =========================================================
# MOMENTUM
# =========================================================

def calcular_momentum(series, periodo=6):

    if len(series) <= periodo:
        return 0.0

    antigo = float(
        series.iloc[-periodo]
    )

    atual = float(
        series.iloc[-1]
    )

    if antigo == 0:
        return 0.0

    return (
        (atual - antigo)
        / antigo
    ) * 100


# =========================================================
# ANÁLISE
# =========================================================

def analisar(df):

    prices = df["price"]

    atual = float(
        prices.iloc[-1]
    )

    media5 = float(
        prices.rolling(5).mean().iloc[-1]
    )

    media20 = float(
        prices.rolling(20).mean().iloc[-1]
    )

    rsi = float(
        calcular_rsi(prices).iloc[-1]
    )

    macd, macd_sinal, histograma = (
        calcular_macd(prices)
    )

    macd_atual = float(
        macd.iloc[-1]
    )

    macd_sinal_atual = float(
        macd_sinal.iloc[-1]
    )

    hist_atual = float(
        histograma.iloc[-1]
    )

    momentum = calcular_momentum(
        prices
    )

    if len(prices) >= 2:

        variacao_1h = (
            (
                prices.iloc[-1]
                - prices.iloc[-2]
            )
            / prices.iloc[-2]
        ) * 100

    else:

        variacao_1h = 0

    if len(prices) >= 25:

        variacao_24h = (
            (
                prices.iloc[-1]
                - prices.iloc[-25]
            )
            / prices.iloc[-25]
        ) * 100

    else:

        variacao_24h = 0

    if len(prices) >= 169:

        variacao_7d = (
            (
                prices.iloc[-1]
                - prices.iloc[-169]
            )
            / prices.iloc[-169]
        ) * 100

    else:

        variacao_7d = 0


    # =====================================================
    # VOLUME
    # =====================================================

    volume_atual = float(
        df["volume"].iloc[-1]
    )

    volume_medio = float(
        df["volume"]
        .rolling(20)
        .mean()
        .iloc[-1]
    )

    if volume_medio > 0:

        volume_ratio = (
            volume_atual
            / volume_medio
        )

    else:

        volume_ratio = 1.0


    # =====================================================
    # SCORE
    # =====================================================

    score = 0

    motivos_compra = []
    motivos_venda = []


    # MÉDIAS

    if media5 > media20:

        score += 2

        motivos_compra.append(
            "Média curta acima da média longa"
        )

    else:

        score -= 2

        motivos_venda.append(
            "Média curta abaixo da média longa"
        )


    # RSI

    if 50 <= rsi <= 70:

        score += 1

        motivos_compra.append(
            "RSI favorece força compradora"
        )

    elif rsi < 30:

        score += 1

        motivos_compra.append(
            "RSI indica região de sobrevenda"
        )

    elif rsi > 70:

        score -= 1

        motivos_venda.append(
            "RSI indica região de sobrecompra"
        )

    elif rsi < 50:

        score -= 1

        motivos_venda.append(
            "RSI abaixo de 50"
        )


    # MACD

    if macd_atual > macd_sinal_atual:

        score += 2

        motivos_compra.append(
            "MACD acima da linha de sinal"
        )

    else:

        score -= 2

        motivos_venda.append(
            "MACD abaixo da linha de sinal"
        )


    # HISTOGRAMA MACD

    if hist_atual > 0:

        score += 1

    else:

        score -= 1


    # MOMENTUM

    if momentum > 0.20:

        score += 1

        motivos_compra.append(
            "Momentum positivo"
        )

    elif momentum < -0.20:

        score -= 1

        motivos_venda.append(
            "Momentum negativo"
        )


    # VARIAÇÃO 24H

    if variacao_24h > 1:

        score += 1

    elif variacao_24h < -1:

        score -= 1


    # VOLUME

    if volume_ratio > 1.2:

        if score > 0:

            score += 1

            motivos_compra.append(
                "Volume acima da média"
            )

        elif score < 0:

            score -= 1

            motivos_venda.append(
                "Volume reforça movimento vendedor"
            )


    # =====================================================
    # SINAL
    # =====================================================

    if score >= 5:

        sinal = "COMPRA"

    elif score <= -5:

        sinal = "VENDA"

    else:

        sinal = "HOLD"


    # =====================================================
    # CONFIANÇA
    # =====================================================

    confianca = 50 + (
        abs(score) * 5
    )

    confianca = min(
        95,
        max(
            50,
            confianca
        )
    )


    # =====================================================
    # MOTIVO
    # =====================================================

    if sinal == "COMPRA":

        if motivos_compra:

            motivo = " • ".join(
                motivos_compra[:4]
            )

        else:

            motivo = (
                "Predominância dos indicadores "
                "positivos."
            )

    elif sinal == "VENDA":

        if motivos_venda:

            motivo = " • ".join(
                motivos_venda[:4]
            )

        else:

            motivo = (
                "Predominância dos indicadores "
                "negativos."
            )

    else:

        motivo = (
            "Os indicadores estão divididos. "
            "O sistema prefere aguardar uma "
            "confirmação mais forte."
        )


    return {

        "preco": atual,

        "media5": media5,

        "media20": media20,

        "rsi": rsi,

        "macd": macd_atual,

        "macd_sinal": macd_sinal_atual,

        "histograma": hist_atual,

        "momentum": momentum,

        "variacao_1h": variacao_1h,

        "variacao_24h": variacao_24h,

        "variacao_7d": variacao_7d,

        "volume_ratio": volume_ratio,

        "score": score,

        "sinal": sinal,

        "confianca": confianca,

        "motivo": motivo
    }


# =========================================================
# TOPO
# =========================================================

st.title("🤖 Crypto AI Trader")

st.caption(
    "V3 • Inteligência de mercado • Paper Trading"
)

st.divider()


# =========================================================
# ESCOLHA
# =========================================================

crypto_nome = st.selectbox(
    "Criptomoeda",
    list(COINS.keys())
)

crypto_id = COINS[crypto_nome]


# =========================================================
# ANALISAR
# =========================================================

if st.button(
    "🔄 ANALISAR MERCADO",
    use_container_width=True
):

    try:

        with st.spinner(
            "Buscando dados do mercado..."
        ):

            df = buscar_mercado(
                crypto_id
            )

            resultado = analisar(
                df
            )

            st.session_state.analise = resultado

            st.session_state.precos = df

            st.session_state.crypto = (
                crypto_nome
            )

        st.success(
            "✅ Mercado analisado com sucesso."
        )

    except Exception as erro:

        st.error(
            "❌ Não foi possível analisar o mercado."
        )

        st.warning(
            f"Detalhes: {erro}"
        )


# =========================================================
# RESULTADO
# =========================================================

if st.session_state.analise:

    resultado = (
        st.session_state.analise
    )

    st.divider()

    st.header("🤖 Sinal do Trader")

    sinal = resultado["sinal"]

    if sinal == "COMPRA":

        st.success(
            "🟢 COMPRA"
        )

    elif sinal == "VENDA":

        st.error(
            "🔴 VENDA"
        )

    else:

        st.warning(
            "🟡 HOLD"
        )

    st.metric(
        "Confiança",
        f'{resultado["confianca"]:.0f}%'
    )

    st.info(
        f'💡 {resultado["motivo"]}'
    )


    # =====================================================
    # PREÇO
    # =====================================================

    st.divider()

    st.header("💰 Mercado")

    st.metric(
        "Preço atual",
        f'${resultado["preco"]:,.2f}'
    )


    # =====================================================
    # INDICADORES
    # =====================================================

    st.header("📊 Indicadores")

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "Média 5",
            f'${resultado["media5"]:,.2f}'
        )

        st.metric(
            "RSI",
            f'{resultado["rsi"]:.1f}'
        )

        st.metric(
            "Momentum",
            f'{resultado["momentum"]:.2f}%'
        )

    with c2:

        st.metric(
            "Média 20",
            f'${resultado["media20"]:,.2f}'
        )

        st.metric(
            "MACD",
            f'{resultado["macd"]:.4f}'
        )

        st.metric(
            "Volume",
            f'{resultado["volume_ratio"]:.2f}x'
        )


    # =====================================================
    # SCORE
    # =====================================================

    st.header("🧠 Score do Motor")

    score = resultado["score"]

    st.metric(
        "Pontuação",
        score
    )

    progresso = (
        score + 10
    ) / 20

    progresso = min(
        1.0,
        max(
            0.0,
            progresso
        )
    )

    st.progress(
        progresso
    )


    # =====================================================
    # VARIAÇÕES
    # =====================================================

    st.header("📈 Variações")

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "1h",
            f'{resultado["variacao_1h"]:.2f}%'
        )

    with c2:

        st.metric(
            "24h",
            f'{resultado["variacao_24h"]:.2f}%'
        )

    with c3:

        st.metric(
            "7d",
            f'{resultado["variacao_7d"]:.2f}%'
        )


    # =====================================================
    # GRÁFICO
    # =====================================================

    st.header("📉 Gráfico")

    df_grafico = (
        st.session_state.precos
        .copy()
    )

    df_grafico = (
        df_grafico
        .set_index("timestamp")
    )

    st.line_chart(
        df_grafico["price"]
    )


# =========================================================
# PAPER TRADING
# =========================================================

st.divider()

st.header("💰 Paper Trading")

st.metric(
    "Saldo disponível",
    f'US$ {st.session_state.saldo:,.2f}'
)


# =========================================================
# COMPRA SIMULADA
# =========================================================

valor_compra = st.number_input(
    "Valor da compra simulada (US$)",
    min_value=10.0,
    max_value=st.session_state.saldo,
    value=min(
        1000.0,
        st.session_state.saldo
    ),
    step=100.0
)


if st.button(
    "🟢 COMPRAR SIMULADO",
    use_container_width=True
):

    if not st.session_state.analise:

        st.warning(
            "Faça uma análise primeiro."
        )

    elif st.session_state.operacao_aberta:

        st.warning(
            "Já existe uma operação aberta."
        )

    elif valor_compra > st.session_state.saldo:

        st.error(
            "Saldo insuficiente."
        )

    else:

        preco = (
            st.session_state
            .analise["preco"]
        )

        quantidade = (
            valor_compra
            / preco
        )

        st.session_state.saldo -= (
            valor_compra
        )

        st.session_state.moedas = (
            quantidade
        )

        st.session_state.preco_entrada = (
            preco
        )

        st.session_state.valor_entrada = (
            valor_compra
        )

        st.session_state.operacao_aberta = (
            True
        )

        st.success(
            "🟢 Compra simulada realizada."
        )


# =========================================================
# OPERAÇÃO ABERTA
# =========================================================

if st.session_state.operacao_aberta:

    st.subheader(
        "📌 Operação aberta"
    )

    preco_atual = 0

    if st.session_state.analise:

        preco_atual = (
            st.session_state
            .analise["preco"]
        )

    valor_atual = (
        st.session_state.moedas
        * preco_atual
    )

    resultado_operacao = (
        valor_atual
        - st.session_state.valor_entrada
    )

    st.write(
        f"Quantidade: "
        f"**{st.session_state.moedas:.8f}**"
    )

    st.write(
        f"Preço de entrada: "
        f"**US$ {st.session_state.preco_entrada:,.2f}**"
    )

    st.write(
        f"Valor atual: "
        f"**US$ {valor_atual:,.2f}**"
    )

    st.write(
        f"Resultado: "
        f"**US$ {resultado_operacao:,.2f}**"
    )


    if st.button(
        "🔴 VENDER SIMULADO",
        use_container_width=True
    ):

        self_resultado = resultado_operacao

        st.session_state.saldo += (
            valor_atual
        )

        registro = {

            "data": datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            ),

            "ativo": (
                st.session_state.crypto
            ),

            "entrada": (
                st.session_state.preco_entrada
            ),

            "saida": preco_atual,

            "resultado": self_resultado
        }

        st.session_state.historico.append(
            registro
        )

        if self_resultado >= 0:

            st.session_state.acertos += 1

        else:

            st.session_state.erros += 1

        st.session_state.moedas = 0

        st.session_state.preco_entrada = 0

        st.session_state.valor_entrada = 0

        st.session_state.operacao_aberta = False

        st.success(
            "🔴 Venda simulada realizada."
        )

        st.rerun()


# =========================================================
# ESTATÍSTICAS
# =========================================================

st.divider()

st.header("🧠 Aprendizado")

c1, c2, c3 = st.columns(3)

with c1:

    st.metric(
        "Operações vencedoras",
        st.session_state.acertos
    )

with c2:

    st.metric(
        "Operações perdedoras",
        st.session_state.erros
    )

with c3:

    total = (
        st.session_state.acertos
        + st.session_state.erros
    )

    if total > 0:

        taxa = (
            st.session_state.acertos
            / total
        ) * 100

    else:

        taxa = 0

    st.metric(
        "Taxa de acerto",
        f"{taxa:.1f}%"
    )


# =========================================================
# HISTÓRICO
# =========================================================

if st.session_state.historico:

    st.header("📒 Histórico")

    historico_df = pd.DataFrame(
        st.session_state.historico
    )

    st.dataframe(
        historico_df,
        use_container_width=True
    )


# =========================================================
# ATUALIZAÇÃO
# =========================================================

st.divider()

if st.button(
    "🔄 ATUALIZAR MERCADO",
    use_container_width=True
):

    try:

        with st.spinner(
            "Atualizando..."
        ):

            df = buscar_mercado(
                crypto_id
            )

            resultado = analisar(
                df
            )

            st.session_state.analise = (
                resultado
            )

            st.session_state.precos = (
                df
            )

        st.rerun()

    except Exception as erro:

        st.error(
            f"Erro ao atualizar: {erro}"
        )


st.divider()

st.caption(
    "Crypto AI Trader V3 • "
    "Sistema experimental de Paper Trading"
)

st.caption(
    "Nenhuma ordem real é enviada para corretoras."
)
