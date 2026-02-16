AUTO_DESLIGADO = 0
AUTO_ASSISTIDO = 1
AUTO_TOTAL = 2


class AutoMode:
    def __init__(self):
        self.nivel = AUTO_DESLIGADO

    def ativar_assistido(self):
        self.nivel = AUTO_ASSISTIDO

    def ativar_total(self):
        self.nivel = AUTO_TOTAL

    def desativar(self):
        self.nivel = AUTO_DESLIGADO

    def pode_aplicar(self):
        return self.nivel in [AUTO_ASSISTIDO, AUTO_TOTAL]
