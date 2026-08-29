class PaperTrader:

    def __init__(self, saldo_inicial=10000.0):
        self.saldo = saldo_inicial
        self.posicao = 0.0
        self.preco_entrada = 0.0
        self.lucro_prejuizo = 0.0

    def comprar(self, preco, valor):
        if valor <= 0:
            return "Valor de compra inválido."

        if valor > self.saldo:
            return "Saldo virtual insuficiente."

        quantidade = valor / preco

        self.saldo -= valor
        self.posicao += quantidade

        if self.preco_entrada == 0:
            self.preco_entrada = preco

        return f"Compra simulada: {quantidade:.6f} unidades."

    def vender(self, preco):
        if self.posicao <= 0:
            return "Não existe posição para vender."

        valor_venda = self.posicao * preco

        self.lucro_prejuizo = (
            (preco - self.preco_entrada)
            * self.posicao
        )

        self.saldo += valor_venda
        self.posicao = 0.0
        self.preco_entrada = 0.0

        return f"Venda simulada: ${valor_venda:,.2f}"

    def patrimonio(self, preco):
        valor_posicao = self.posicao * preco

        return self.saldo + valor_posicao

    def resultado(self, preco):
        if self.posicao <= 0:
            return 0.0

        return (
            (preco - self.preco_entrada)
            * self.posicao
      )
