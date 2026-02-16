MODO_TEXTO = "texto"
MODO_VOZ = "voz"

def alternar_modo(modo_atual, comando):
    comando = comando.lower()

    if comando == "voz":
        return MODO_VOZ, "Modo voz ativado."

    if comando in ["texto", "modo texto"]:
        return MODO_TEXTO, "Voltei pro teclado."

    return modo_atual, None
