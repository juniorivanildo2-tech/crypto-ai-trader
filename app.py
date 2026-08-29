import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime, timezone

# ============================================================
# CRYPTO AI TRADER V4
# Motor de aprendizado + análise técnica + Paper Trading
# Sem sklearn
# ============================================================

st.set_page_config(
    page_title="Crypto AI Trader",
    page_icon="🤖",
    layout="wide"
)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

APP_VERSION = "V4"
STATE_FILE = "ai_learning.json"

BINANCE_URL = "https://api.binance.com/api/v3/klines"

COINS = {
    "Bitcoin": "BTCUSDT",
    "Ethereum": "ETHUSDT",
    "Solana": "SOLUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
    "Cardano": "ADAUSDT",
    "Dogecoin": "DOGEUSDT"
}

INTERVAL = "1h"
CANDLE_LIMIT = 300

# ============================================================
# ESTADO DO APRENDIZADO
# ============================================================

DEFAULT_LEARNING = {
    "version": 4,
    "assets": {},
    "total_predictions": 0,
    "correct_predictions": 0,
    "wrong_predictions": 0
}


def create_asset_state():
    return {
        "predictions": [],
        "correct": 0,
        "wrong": 0,
        "signals": 0,

        "weights": {
            "trend": 1.0,
            "rsi": 1.0,
            "momentum": 1.0,
            "macd": 1.0,
            "volume": 1.0
        }
    }


def load_learning():
    if not os.path.exists(STATE_FILE):
        return DEFAULT_LEARNING.copy()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return DEFAULT_LEARNING.copy()

        data.setdefault("version", 4)
        data.setdefault("assets", {})
        data.setdefault("total_predictions", 0)
        data.setdefault("correct_predictions", 0)
        data.setdefault("wrong_predictions", 0)

        return data

    except Exception:
        return DEFAULT_LEARNING.copy()


def save_learning(data):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


if "learning" not in st.session_state:
    st.session_state.learning = load_learning()


learning = st.session_state.learning


# ============================================================
# FUNÇÕES DE MERCADO
# ============================================================

def get_market_data(symbol):
    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "limit": CANDLE_LIMIT
    }

    response = requests.get(
        BINANCE_URL,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    columns = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_base",
        "taker_quote",
        "ignore"
    ]

    df = pd.DataFrame(data, columns=columns)

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["datetime"] = pd.to_datetime(
        df["open_time"],
        unit="ms",
        utc=True
    )

    return df


# ============================================================
# INDICADORES
# ============================================================

def calculate_rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


def calculate_ema(series, period):
    return series.ewm(
        span=period,
        adjust=False
    ).mean()


def calculate_macd(series):
    ema12 = calculate_ema(series, 12)
    ema26 = calculate_ema(series, 26)

    macd = ema12 - ema26
    signal = calculate_ema(macd, 9)

    histogram = macd - signal

    return macd, signal, histogram


def add_indicators(df):
    df = df.copy()

    df["ema5"] = calculate_ema(df["close"], 5)
    df["ema20"] = calculate_ema(df["close"], 20)
    df["ema50"] = calculate_ema(df["close"], 50)

    df["rsi"] = calculate_rsi(df["close"], 14)

    (
        df["macd"],
        df["macd_signal"],
        df["macd_hist"]
    ) = calculate_macd(df["close"])

    df["momentum"] = (
        df["close"].pct_change(5) * 100
    )

    df["volume_ma"] = (
        df["volume"].rolling(20).mean()
    )

    df["volume_ratio"] = (
        df["volume"] /
        df["volume_ma"].replace(0, np.nan)
    )

    df["volatility"] = (
        df["close"].pct_change()
        .rolling(20)
        .std() * 100
    )

    return df


# ============================================================
# MOTOR DE INTELIGÊNCIA
# ============================================================

def get_asset_state(asset):
    if asset not in learning["assets"]:
        learning["assets"][asset] = create_asset_state()

    state = learning["assets"][asset]

    state.setdefault("predictions", [])
    state.setdefault("correct", 0)
    state.setdefault("wrong", 0)
    state.setdefault("signals", 0)

    state.setdefault(
        "weights",
        {
            "trend": 1.0,
            "rsi": 1.0,
            "momentum": 1.0,
            "macd": 1.0,
            "volume": 1.0
        }
    )

    return state


def normalize_weights(weights):
    for key in weights:
        weights[key] = max(
            0.25,
            min(3.0, float(weights[key]))
        )


def calculate_signal(df, asset):
    state = get_asset_state(asset)
    weights = state["weights"]

    row = df.iloc[-1]

    scores = {
        "BUY": 0.0,
        "SELL": 0.0
    }

    explanations = []

    # --------------------------------------------------------
    # TENDÊNCIA
    # --------------------------------------------------------

    if row["ema5"] > row["ema20"] > row["ema50"]:
        scores["BUY"] += 2.0 * weights["trend"]
        explanations.append("Tendência de alta")

    elif row["ema5"] < row["ema20"] < row["ema50"]:
        scores["SELL"] += 2.0 * weights["trend"]
        explanations.append("Tendência de baixa")

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    rsi = float(row["rsi"])

    if rsi < 30:
        scores["BUY"] += 1.5 * weights["rsi"]
        explanations.append("RSI em região de sobrevenda")

    elif rsi > 70:
        scores["SELL"] += 1.5 * weights["rsi"]
        explanations.append("RSI em região de sobrecompra")

    elif rsi >= 50:
        scores["BUY"] += 0.5 * weights["rsi"]

    else:
        scores["SELL"] += 0.5 * weights["rsi"]

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    momentum = float(row["momentum"])

    if momentum > 0.5:
        scores["BUY"] += 1.2 * weights["momentum"]
        explanations.append("Momentum positivo")

    elif momentum < -0.5:
        scores["SELL"] += 1.2 * weights["momentum"]
        explanations.append("Momentum negativo")

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if row["macd_hist"] > 0:
        scores["BUY"] += 1.2 * weights["macd"]
        explanations.append("MACD favorece alta")

    elif row["macd_hist"] < 0:
        scores["SELL"] += 1.2 * weights["macd"]
        explanations.append("MACD favorece baixa")

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    volume_ratio = float(
        row["volume_ratio"]
        if not pd.isna(row["volume_ratio"])
        else 1.0
    )

    if volume_ratio > 1.2:
        if momentum >= 0:
            scores["BUY"] += 0.8 * weights["volume"]
            explanations.append("Volume acima da média")

        else:
            scores["SELL"] += 0.8 * weights["volume"]
            explanations.append("Volume confirma pressão vendedora")

    # --------------------------------------------------------
    # DECISÃO
    # --------------------------------------------------------

    buy_score = scores["BUY"]
    sell_score = scores["SELL"]

    total = buy_score + sell_score

    if total <= 0:
        return "HOLD", 50, explanations, scores

    difference = abs(buy_score - sell_score)

    confidence = 50 + (
        difference / total
    ) * 50

    confidence = max(
        50,
        min(95, confidence)
    )

    if difference < total * 0.15:
        signal = "HOLD"
        confidence = min(confidence, 65)

    elif buy_score > sell_score:
        signal = "BUY"

    else:
        signal = "SELL"

    return (
        signal,
        round(confidence),
        explanations,
        scores
    )


# ============================================================
# SISTEMA DE APRENDIZADO
# ============================================================

def register_prediction(
    asset,
    signal,
    confidence,
    price,
    timestamp
):
    if signal == "HOLD":
        return

    state = get_asset_state(asset)

    prediction = {
        "id": f"{timestamp}_{price}",
        "timestamp": timestamp,
        "signal": signal,
        "confidence": float(confidence),
        "entry_price": float(price),
        "evaluated": False
    }

    # Evita registrar repetidamente exatamente a mesma previsão
    for old in state["predictions"]:
        if old.get("id") == prediction["id"]:
            return

    state["predictions"].append(prediction)
    state["signals"] += 1

    learning["total_predictions"] += 1

    # Mantém somente as últimas 500 previsões
    if len(state["predictions"]) > 500:
        state["predictions"] = state["predictions"][-500:]

    save_learning(learning)


def evaluate_predictions(asset, df):
    state = get_asset_state(asset)

    if len(df) < 6:
        return

    current_index = len(df) - 1

    changed = False

    for prediction in state["predictions"]:

        if prediction.get("evaluated", False):
            continue

        try:
            prediction_time = pd.to_datetime(
                prediction["timestamp"],
                utc=True
            )

            distances = (
                df["datetime"] - prediction_time
            ).abs()

            start_index = int(
                distances.argmin()
            )

        except Exception:
            continue

        # Espera pelo menos 3 candles para avaliar
        if current_index - start_index < 3:
            continue

        future_index = min(
            start_index + 3,
            current_index
        )

        entry = float(
            prediction["entry_price"]
        )

        future_price = float(
            df.iloc[future_index]["close"]
        )

        signal = prediction["signal"]

        if signal == "BUY":
            correct = future_price > entry

        elif signal == "SELL":
            correct = future_price < entry

        else:
            correct = None

        if correct is None:
            continue

        prediction["evaluated"] = True
        prediction["result"] = (
            "WIN" if correct else "LOSS"
        )

        prediction["exit_price"] = future_price

        if correct:
            state["correct"] += 1
            learning["correct_predictions"] += 1
        else:
            state["wrong"] += 1
            learning["wrong_predictions"] += 1

        # ----------------------------------------------------
        # APRENDIZADO ADAPTATIVO
        # ----------------------------------------------------
        #
        # Quando acerta:
        # aumenta ligeiramente os pesos.
        #
        # Quando erra:
        # reduz ligeiramente os pesos.
        #
        # Isso não "garante" previsão futura.
        # É um mecanismo adaptativo baseado no histórico.
        # ----------------------------------------------------

        weights = state["weights"]

        if correct:
            factor = 1.03
        else:
            factor = 0.97

        for key in weights:
            weights[key] *= factor

        normalize_weights(weights)

        changed = True

    if changed:
        save_learning(learning)


def get_accuracy(asset):
    state = get_asset_state(asset)

    total = (
        state["correct"] +
        state["wrong"]
    )

    if total == 0:
        return None

    return (
        state["correct"] /
        total
    ) * 100


# ============================================================
# PAPER TRADING
# ============================================================

def initialize_paper():
    if "paper" not in st.session_state:
        st.session_state.paper = {
            "balance": 10000.0,
            "initial_balance": 10000.0,
            "position": None,
            "trades": []
        }


initialize_paper()


def open_paper_trade(
    asset,
    signal,
    price,
    confidence,
    amount
):
    if signal not in ["BUY", "SELL"]:
        return False, "Sinal HOLD não gera operação."

    paper = st.session_state.paper

    if paper["position"] is not None:
        return False, "Já existe uma posição aberta."

    if amount <= 0:
        return False, "Valor inválido."

    if amount > paper["balance"]:
        return False, "Saldo insuficiente."

    quantity = amount / price

    paper["position"] = {
        "asset": asset,
        "signal": signal,
        "entry_price": price,
        "quantity": quantity,
        "amount": amount,
        "confidence": confidence,
        "opened_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    paper["balance"] -= amount

    return True, "Operação simulada aberta."


def close_paper_trade(price):
    paper = st.session_state.paper

    position = paper["position"]

    if position is None:
        return False, 0.0, "Não existe posição aberta."

    entry = position["entry_price"]
    quantity = position["quantity"]
    signal = position["signal"]

    if signal == "BUY":
        pnl = (
            price - entry
        ) * quantity

    else:
        pnl = (
            entry - price
        ) * quantity

    returned = position["amount"] + pnl

    paper["balance"] += returned

    trade = {
        "asset": position["asset"],
        "side": signal,
        "entry": entry,
        "exit": price,
        "amount": position["amount"],
        "pnl": pnl,
        "opened_at": position["opened_at"],
        "closed_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    paper["trades"].append(trade)
    paper["position"] = None

    return True, pnl, "Operação encerrada."


# ============================================================
# CABEÇALHO
# ============================================================

st.title("🤖 Crypto AI Trader")

st.caption(
    f"{APP_VERSION} • Inteligência de mercado • "
    "Motor de aprendizado • Paper Trading"
)

st.divider()


# ============================================================
# SELEÇÃO
# ============================================================

asset = st.selectbox(
    "Criptomoeda",
    list(COINS.keys())
)

symbol = COINS[asset]

analyze = st.button(
    "🔄 ANALISAR MERCADO",
    use_container_width=True
)


# ============================================================
# ANÁLISE
# ============================================================

if analyze:

    with st.spinner("Analisando mercado..."):

        try:

            df = get_market_data(symbol)

            df = add_indicators(df)

            # Avalia previsões antigas antes de gerar a nova
            evaluate_predictions(
                asset,
                df
            )

            signal, confidence, explanations, scores = (
                calculate_signal(
                    df,
                    asset
                )
            )

            row = df.iloc[-1]

            price = float(row["close"])

            timestamp = row["datetime"]

            register_prediction(
                asset,
                signal,
                confidence,
                price,
                timestamp.isoformat()
            )

            st.session_state.analysis = {
                "asset": asset,
                "symbol": symbol,
                "df": df,
                "signal": signal,
                "confidence": confidence,
                "explanations": explanations,
                "scores": scores,
                "price": price,
                "timestamp": timestamp
            }

            st.success(
                "✅ Mercado analisado com sucesso."
            )

        except Exception as e:

            st.error(
                "❌ Não foi possível atualizar o mercado."
            )

            st.caption(
                "Verifique sua conexão com a internet e "
                "tente novamente."
            )


# ============================================================
# RESULTADO DA ANÁLISE
# ============================================================

if "analysis" in st.session_state:

    analysis = st.session_state.analysis

    df = analysis["df"]

    signal = analysis["signal"]
    confidence = analysis["confidence"]
    price = analysis["price"]

    state = get_asset_state(
        analysis["asset"]
    )

    st.divider()

    st.header("🤖 Sinal do Trader")

    if signal == "BUY":
        st.success("🟢 COMPRAR")

    elif signal == "SELL":
        st.error("🔴 VENDER")

    else:
        st.warning("🟡 HOLD")

    st.metric(
        "Confiança",
        f"{confidence}%"
    )

    accuracy = get_accuracy(
        analysis["asset"]
    )

    if accuracy is not None:

        st.metric(
            "Taxa histórica de acerto",
            f"{accuracy:.1f}%"
        )

    else:

        st.info(
            "💡 A IA ainda está acumulando histórico "
            "para aprender."
        )

    st.divider()

    # ========================================================
    # MERCADO
    # ========================================================

    st.header("💰 Mercado")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Preço atual",
            f"${price:,.2f}"
        )

    with col2:
        st.metric(
            "RSI",
            f"{df.iloc[-1]['rsi']:.2f}"
        )

    with col3:
        st.metric(
            "Momentum",
            f"{df.iloc[-1]['momentum']:.2f}%"
        )

    st.subheader("📊 Indicadores")

    indicator_data = pd.DataFrame({
        "Indicador": [
            "Média 5",
            "Média 20",
            "Média 50",
            "RSI",
            "MACD",
            "Momentum",
            "Volatilidade"
        ],
        "Valor": [
            df.iloc[-1]["ema5"],
            df.iloc[-1]["ema20"],
            df.iloc[-1]["ema50"],
            df.iloc[-1]["rsi"],
            df.iloc[-1]["macd"],
            df.iloc[-1]["momentum"],
            df.iloc[-1]["volatility"]
        ]
    })

    st.dataframe(
        indicator_data,
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # GRÁFICO
    # ========================================================

    st.subheader("📈 Histórico de preço")

    chart_df = df[
        ["datetime", "close"]
    ].tail(100).copy()

    chart_df = chart_df.set_index(
        "datetime"
    )

    st.line_chart(
        chart_df["close"]
    )

    # ========================================================
    # EXPLICAÇÃO
    # ========================================================

    st.subheader("🧠 Por que a IA tomou essa decisão?")

    if analysis["explanations"]:

        for explanation in analysis["explanations"]:
            st.write(
                f"• {explanation}"
            )

    else:

        st.write(
            "• Os indicadores não apresentaram "
            "uma confirmação forte."
        )

    st.write(
        f"Pontuação de compra: "
        f"{analysis['scores']['BUY']:.2f}"
    )

    st.write(
        f"Pontuação de venda: "
        f"{analysis['scores']['SELL']:.2f}"
    )


# ============================================================
# MOTOR DE APRENDIZADO
# ============================================================

st.divider()

st.header("🧠 Motor de Aprendizado")

current_state = get_asset_state(asset)

total_asset_predictions = (
    current_state["correct"] +
    current_state["wrong"]
)

learning_col1, learning_col2, learning_col3 = st.columns(3)

with learning_col1:

    st.metric(
        "Previsões avaliadas",
        total_asset_predictions
    )

with learning_col2:

    st.metric(
        "Acertos",
        current_state["correct"]
    )

with learning_col3:

    st.metric(
        "Erros",
        current_state["wrong"]
    )


asset_accuracy = get_accuracy(asset)

if asset_accuracy is not None:

    st.progress(
        min(asset_accuracy / 100, 1.0)
    )

    st.write(
        f"Desempenho de {asset}: "
        f"**{asset_accuracy:.2f}% de acerto**"
    )

else:

    st.info(
        "A IA ainda não possui previsões suficientes "
        "para medir o desempenho."
    )


st.subheader("⚙️ Pesos que a IA está aprendendo")

weights_df = pd.DataFrame({
    "Indicador": list(
        current_state["weights"].keys()
    ),
    "Peso": list(
        current_state["weights"].values()
    )
})

st.dataframe(
    weights_df,
    use_container_width=True,
    hide_index=True
)

st.caption(
    "Os pesos aumentam ou diminuem gradualmente "
    "conforme o histórico de acertos e erros."
)


# ============================================================
# PAPER TRADING
# ============================================================

st.divider()

st.header("💰 Paper Trading")

paper = st.session_state.paper

total_pnl = sum(
    trade["pnl"]
    for trade in paper["trades"]
)

portfolio_value = paper["balance"]

if paper["position"] is not None:

    position = paper["position"]

    if (
        "analysis" in st.session_state
        and position["asset"] ==
        st.session_state.analysis["asset"]
    ):

        current_price = (
            st.session_state.analysis["price"]
        )

        if position["signal"] == "BUY":

            unrealized = (
                current_price -
                position["entry_price"]
            ) * position["quantity"]

        else:

            unrealized = (
                position["entry_price"] -
                current_price
            ) * position["quantity"]

        portfolio_value += (
            position["amount"] +
            unrealized
        )

else:

    unrealized = 0.0


paper_col1, paper_col2, paper_col3 = st.columns(3)

with paper_col1:

    st.metric(
        "Saldo disponível",
        f"US$ {paper['balance']:,.2f}"
    )

with paper_col2:

    st.metric(
        "P&L realizado",
        f"US$ {total_pnl:,.2f}"
    )

with paper_col3:

    st.metric(
        "Operações",
        len(paper["trades"])
    )


# ============================================================
# OPERAÇÃO SIMULADA
# ============================================================

if "analysis" in st.session_state:

    analysis = st.session_state.analysis

    st.subheader("🎯 Operação simulada")

    amount = st.number_input(
        "Valor da operação (US$)",
        min_value=10.0,
        max_value=paper["balance"]
        if paper["balance"] >= 10
        else 10.0,
        value=min(
            1000.0,
            paper["balance"]
        ) if paper["balance"] >= 10 else 10.0,
        step=10.0
    )

    trade_col1, trade_col2 = st.columns(2)

    with trade_col1:

        if st.button(
            "🚀 Abrir operação pelo sinal da IA",
            use_container_width=True
        ):

            success, message = open_paper_trade(
                analysis["asset"],
                analysis["signal"],
                analysis["price"],
                analysis["confidence"],
                amount
            )

            if success:
                st.success(message)
            else:
                st.warning(message)

    with trade_col2:

        if st.button(
            "🔒 Encerrar posição",
            use_container_width=True
        ):

            success, pnl, message = (
                close_paper_trade(
                    analysis["price"]
                )
            )

            if success:

                if pnl >= 0:
                    st.success(
                        f"{message} "
                        f"Lucro: US$ {pnl:,.2f}"
                    )
                else:
                    st.error(
                        f"{message} "
                        f"Resultado: US$ {pnl:,.2f}"
                    )

            else:

                st.warning(message)


# ============================================================
# POSIÇÃO ATUAL
# ============================================================

if paper["position"] is not None:

    st.subheader("📌 Posição aberta")

    position = paper["position"]

    position_df = pd.DataFrame([
        {
            "Cripto": position["asset"],
            "Direção": position["signal"],
            "Preço entrada": position["entry_price"],
            "Quantidade": position["quantity"],
            "Valor": position["amount"],
            "Confiança": f"{position['confidence']:.0f}%"
        }
    ])

    st.dataframe(
        position_df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# HISTÓRICO
# ============================================================

if paper["trades"]:

    st.subheader("📚 Histórico do Paper Trading")

    history = pd.DataFrame(
        paper["trades"]
    )

    st.dataframe(
        history,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# HISTÓRICO DA IA
# ============================================================

st.divider()

st.header("📚 Histórico de Aprendizado")

predictions = current_state["predictions"]

evaluated = [
    p for p in predictions
    if p.get("evaluated", False)
]

if evaluated:

    history_ai = pd.DataFrame(
        evaluated[-30:]
    )

    columns_to_show = [
        "timestamp",
        "signal",
        "confidence",
        "entry_price",
        "exit_price",
        "result"
    ]

    available = [
        c for c in columns_to_show
        if c in history_ai.columns
    ]

    st.dataframe(
        history_ai[available],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Ainda não existem previsões avaliadas. "
        "Continue analisando o mercado para o motor "
        "construir seu histórico."
    )


# ============================================================
# CONTROLE DO APRENDIZADO
# ============================================================

st.divider()

st.subheader("🔧 Controle do motor")

if st.button(
    "♻️ Resetar aprendizado desta criptomoeda",
    use_container_width=True
):

    learning["assets"][asset] = create_asset_state()

    save_learning(learning)

    st.success(
        f"Aprendizado de {asset} reiniciado."
    )

    st.rerun()


st.caption(
    "⚠️ Este aplicativo é experimental e utiliza "
    "Paper Trading. Os sinais não são garantia de lucro "
    "e não devem ser tratados como recomendação financeira."
)

st.caption(
    f"Crypto AI Trader {APP_VERSION}"
)
