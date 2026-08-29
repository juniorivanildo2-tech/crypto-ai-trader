import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Crypto AI Trader V2",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Crypto AI Trader V2")
st.caption("Motor de aprendizado de máquina + Paper Trading")


# ============================================================
# CRIPTOMOEDAS
# ============================================================

COINS = {
    "Bitcoin (BTC)": "bitcoin",
    "Ethereum (ETH)": "ethereum",
    "Solana (SOL)": "solana",
    "BNB (BNB)": "binancecoin",
    "XRP (XRP)": "ripple",
    "Dogecoin (DOGE)": "dogecoin",
    "Cardano (ADA)": "cardano",
    "Avalanche (AVAX)": "avalanche-2",
    "Chainlink (LINK)": "chainlink",
    "Polkadot (DOT)": "polkadot"
}


# ============================================================
# BUSCAR PREÇO ATUAL
# ============================================================

def get_current_price(coin_id):

    url = "https://api.coingecko.com/api/v3/simple/price"

    params = {
        "ids": coin_id,
        "vs_currencies": "usd"
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    return float(data[coin_id]["usd"])


# ============================================================
# BUSCAR HISTÓRICO
# ============================================================

def get_history(coin_id, days=90):

    url = (
        f"https://api.coingecko.com/api/v3/coins/"
        f"{coin_id}/market_chart"
    )

    params = {
        "vs_currency": "usd",
        "days": str(days)
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    prices = data.get("prices", [])

    if len(prices) < 100:
        raise ValueError(
            "Dados históricos insuficientes."
        )

    df = pd.DataFrame(
        prices,
        columns=["timestamp", "price"]
    )

    df["datetime"] = pd.to_datetime(
        df["timestamp"],
        unit="ms"
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    )

    df = df.dropna()

    # Evita dados duplicados
    df = df.drop_duplicates(
        subset=["datetime"]
    )

    return df


# ============================================================
# CRIAR INDICADORES
# ============================================================

def create_features(df):

    df = df.copy()

    # Retornos
    df["return_1"] = df["price"].pct_change(1)
    df["return_3"] = df["price"].pct_change(3)
    df["return_6"] = df["price"].pct_change(6)
    df["return_12"] = df["price"].pct_change(12)

    # Médias móveis
    df["ma_5"] = df["price"].rolling(5).mean()
    df["ma_10"] = df["price"].rolling(10).mean()
    df["ma_20"] = df["price"].rolling(20).mean()
    df["ma_50"] = df["price"].rolling(50).mean()

    # Relação entre preço e médias
    df["price_ma5"] = df["price"] / df["ma_5"] - 1
    df["price_ma20"] = df["price"] / df["ma_20"] - 1

    # Relação entre médias
    df["ma5_ma20"] = df["ma_5"] / df["ma_20"] - 1
    df["ma10_ma20"] = df["ma_10"] / df["ma_20"] - 1

    # Volatilidade
    df["volatility"] = (
        df["return_1"]
        .rolling(20)
        .std()
    )

    # RSI
    delta = df["price"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["rsi"] = 100 - (
        100 / (1 + rs)
    )

    # Tendência
    df["trend"] = (
        df["ma_5"] / df["ma_20"] - 1
    )

    return df


# ============================================================
# CRIAR ALVO DO APRENDIZADO
# ============================================================

def create_target(df):

    df = df.copy()

    # Retorno futuro de aproximadamente 6 períodos
    future_return = (
        df["price"].shift(-6)
        / df["price"]
        - 1
    )

    # Classes:
    # 2 = COMPRA
    # 1 = HOLD
    # 0 = VENDA

    df["target"] = 1

    df.loc[
        future_return > 0.008,
        "target"
    ] = 2

    df.loc[
        future_return < -0.008,
        "target"
    ] = 0

    return df


# ============================================================
# TREINAR MODELO
# ============================================================

def train_model(df):

    feature_columns = [
        "return_1",
        "return_3",
        "return_6",
        "return_12",
        "price_ma5",
        "price_ma20",
        "ma5_ma20",
        "ma10_ma20",
        "volatility",
        "rsi",
        "trend"
    ]

    data = df.dropna().copy()

    if len(data) < 150:
        raise ValueError(
            "Poucos dados para treinar o modelo."
        )

    X = data[feature_columns]
    y = data["target"]

    # Separação cronológica.
    # Nunca embaralhamos os dados financeiros.
    split = int(len(data) * 0.80)

    X_train = X.iloc[:split]
    y_train = y.iloc[:split]

    X_test = X.iloc[split:]
    y_test = y.iloc[split:]

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        class_weight="balanced"
    )

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    return (
        model,
        feature_columns,
        accuracy,
        len(X_train),
        len(X_test)
    )


# ============================================================
# GERAR SINAL
# ============================================================

def generate_signal(
    model,
    feature_columns,
    df
):

    data = df.dropna().copy()

    last = data.iloc[-1]

    X_last = pd.DataFrame(
        [last[feature_columns].values],
        columns=feature_columns
    )

    prediction = int(
        model.predict(X_last)[0]
    )

    probabilities = model.predict_proba(
        X_last
    )[0]

    classes = model.classes_

    probability_map = {}

    for cls, prob in zip(
        classes,
        probabilities
    ):
        probability_map[int(cls)] = float(prob)

    buy_prob = probability_map.get(2, 0)
    hold_prob = probability_map.get(1, 0)
    sell_prob = probability_map.get(0, 0)

    if prediction == 2:
        signal = "COMPRA"
        confidence = buy_prob

    elif prediction == 0:
        signal = "VENDA"
        confidence = sell_prob

    else:
        signal = "HOLD"
        confidence = hold_prob

    # Filtro de segurança:
    # se a confiança for baixa, não operar.
    if confidence < 0.55:

        signal = "HOLD"

        reason = (
            "O modelo encontrou uma direção, "
            "mas a confiança está baixa. "
            "Por segurança, o sistema permanece em HOLD."
        )

    elif signal == "COMPRA":

        reason = (
            "O modelo identificou maior probabilidade "
            "de movimento de alta."
        )

    elif signal == "VENDA":

        reason = (
            "O modelo identificou maior probabilidade "
            "de movimento de baixa."
        )

    else:

        reason = (
            "O modelo não identificou uma oportunidade "
            "com confiança suficiente."
        )

    return (
        signal,
        confidence,
        buy_prob,
        hold_prob,
        sell_prob,
        reason
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Configurações")

coin_name = st.sidebar.selectbox(
    "Criptomoeda",
    list(COINS.keys())
)

coin_id = COINS[coin_name]

capital = st.sidebar.number_input(
    "Capital simulado (US$)",
    min_value=100.0,
    max_value=1000000.0,
    value=1000.0,
    step=100.0
)

st.sidebar.divider()

st.sidebar.info(
    "🧠 O modelo aprende com dados históricos "
    "e testa seu desempenho em dados posteriores."
)

st.sidebar.warning(
    "⚠️ Este sistema NÃO executa ordens reais."
)


# ============================================================
# PAPER TRADING
# ============================================================

if "balance" not in st.session_state:
    st.session_state.balance = capital

if "position" not in st.session_state:
    st.session_state.position = False

if "entry_price" not in st.session_state:
    st.session_state.entry_price = 0.0

if "invested" not in st.session_state:
    st.session_state.invested = 0.0


# ============================================================
# CONEXÃO
# ============================================================

try:

    current_price = get_current_price(
        coin_id
    )

    st.metric(
        "💰 Preço atual",
        f"US$ {current_price:,.2f}"
    )

    st.success(
        "🟢 Mercado conectado"
    )

except Exception as e:

    current_price = None

    st.error(
        "🔴 Erro ao conectar ao mercado."
    )

    st.code(str(e))


st.divider()


# ============================================================
# MOTOR DE IA
# ============================================================

st.header("🧠 Motor de Aprendizado")


if current_price is not None:

    try:

        with st.spinner(
            "Baixando dados e treinando o modelo..."
        ):

            history = get_history(
                coin_id,
                days=90
            )

            features = create_features(
                history
            )

            dataset = create_target(
                features
            )

            (
                model,
                feature_columns,
                accuracy,
                train_size,
                test_size
            ) = train_model(
                dataset
            )

            (
                signal,
                confidence,
                buy_prob,
                hold_prob,
                sell_prob,
                reason
            ) = generate_signal(
                model,
                feature_columns,
                features
            )


        # ====================================================
        # SINAL
        # ====================================================

        st.subheader("🤖 Sinal atual")

        if signal == "COMPRA":

            st.success(
                "🟢 COMPRA"
            )

        elif signal == "VENDA":

            st.error(
                "🔴 VENDA"
            )

        else:

            st.warning(
                "🟡 HOLD"
            )

        st.info(
            f"💡 {reason}"
        )


        # ====================================================
        # CONFIANÇA
        # ====================================================

        st.subheader(
            "🎯 Probabilidades do modelo"
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "COMPRA",
                f"{buy_prob * 100:.1f}%"
            )

        with c2:

            st.metric(
                "HOLD",
                f"{hold_prob * 100:.1f}%"
            )

        with c3:

            st.metric(
                "VENDA",
                f"{sell_prob * 100:.1f}%"
            )


        st.progress(
            min(confidence, 1.0),
            text=(
                f"Confiança do sinal: "
                f"{confidence * 100:.1f}%"
            )
        )


        # ====================================================
        # DESEMPENHO
        # ====================================================

        st.subheader(
            "📊 Desempenho do aprendizado"
        )

        a, b, c = st.columns(3)

        with a:

            st.metric(
                "Acurácia do teste",
                f"{accuracy * 100:.1f}%"
            )

        with b:

            st.metric(
                "Dados de treinamento",
                train_size
            )

        with c:

            st.metric(
                "Dados de teste",
                test_size
            )


        # ====================================================
        # GRÁFICO
        # ====================================================

        st.subheader(
            "📈 Mercado + médias móveis"
        )

        chart = features[
            [
                "datetime",
                "price",
                "ma_5",
                "ma_20"
            ]
        ].dropna()

        chart = chart.set_index(
            "datetime"
        )

        chart.columns = [
            "Preço",
            "Média 5",
            "Média 20"
        ]

        st.line_chart(
            chart.tail(300)
        )


        # ====================================================
        # INDICADORES
        # ====================================================

        last = features.dropna().iloc[-1]

        st.subheader(
            "📌 Indicadores utilizados pela IA"
        )

        i1, i2, i3, i4 = st.columns(4)

        with i1:

            st.metric(
                "RSI",
                f"{last['rsi']:.1f}"
            )

        with i2:

            st.metric(
                "Volatilidade",
                f"{last['volatility'] * 100:.2f}%"
            )

        with i3:

            st.metric(
                "Tendência",
                f"{last['trend'] * 100:.2f}%"
            )

        with i4:

            st.metric(
                "Retorno 12",
                f"{last['return_12'] * 100:.2f}%"
            )


    except Exception as e:

        st.error(
            "❌ Não foi possível treinar o modelo."
        )

        st.code(str(e))


else:

    st.warning(
        "Aguardando conexão com o mercado."
    )


# ============================================================
# PAPER TRADING
# ============================================================

st.divider()

st.header("💱 Operação Simulada")

p1, p2 = st.columns(2)

with p1:

    st.metric(
        "Saldo",
        f"US$ {st.session_state.balance:,.2f}"
    )

with p2:

    if st.session_state.position:

        st.metric(
            "Posição",
            "COMPRADO"
        )

    else:

        st.metric(
            "Posição",
            "FORA DO MERCADO"
        )


if current_price is not None:

    if not st.session_state.position:

        amount = st.number_input(
            "Valor da operação (US$)",
            min_value=10.0,
            max_value=float(
                st.session_state.balance
            ),
            value=min(
                100.0,
                float(st.session_state.balance)
            ),
            step=10.0
        )

        if st.button(
            "🟢 COMPRAR SIMULADO",
            use_container_width=True
        ):

            if amount <= st.session_state.balance:

                st.session_state.balance -= amount

                st.session_state.position = True

                st.session_state.entry_price = current_price

                st.session_state.invested = amount

                st.success(
                    "Compra simulada realizada."
                )

                st.rerun()

    else:

        current_value = (
            st.session_state.invested
            * current_price
            / st.session_state.entry_price
        )

        profit = (
            current_value
            - st.session_state.invested
        )

        st.write(
            f"Preço de entrada: "
            f"US$ {st.session_state.entry_price:,.2f}"
        )

        st.write(
            f"Valor investido: "
            f"US$ {st.session_state.invested:,.2f}"
        )

        st.write(
            f"Valor atual: "
            f"US$ {current_value:,.2f}"
        )

        if profit >= 0:

            st.success(
                f"🟢 Lucro simulado: "
                f"US$ {profit:,.2f}"
            )

        else:

            st.error(
                f"🔴 Prejuízo simulado: "
                f"US$ {profit:,.2f}"
            )

        if st.button(
            "🔴 VENDER SIMULADO",
            use_container_width=True
        ):

            st.session_state.balance += current_value

            st.session_state.position = False

            st.session_state.entry_price = 0.0

            st.session_state.invested = 0.0

            st.success(
                "Venda simulada realizada."
            )

            st.rerun()


# ============================================================
# STATUS
# ============================================================

st.divider()

st.subheader("📊 Status")

st.write(
    f"**Ativo:** {coin_name}"
)

st.write(
    "**Motor:** Random Forest"
)

st.write(
    "**Modo:** Paper Trading"
)

st.write(
    "**Ordens reais:** DESATIVADAS"
)

st.write(
    f"**Atualização:** "
    f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
)

st.divider()

st.caption(
    "⚠️ Acurácia histórica não garante lucro futuro. "
    "Use esta versão para testes e aprendizado."
)
