from yui_ai.voice.voice import ouvir

WAKE_WORDS = ["yui", "ei yui", "ei ui","ei","pina","0"]

def aguardar_wake_word():
    while True:
        texto = ouvir(timeout=2, limite=1)
        if not texto:
            continue

        texto = texto.lower()

        if any(p in texto for p in WAKE_WORDS):
            print("✨ Yui acordou!")
            return