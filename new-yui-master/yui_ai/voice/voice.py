import asyncio
import tempfile
import os

# Dependências de voz são opcionais.
try:
    import edge_tts  # type: ignore
    import playsound  # type: ignore
    import speech_recognition as sr  # type: ignore
except Exception:  # noqa: BLE001
    edge_tts = None
    playsound = None
    sr = None

# =============================
# CONFIGURAÇÃO DA VOZ DA YUI
# =============================
VOICE = "pt-BR-FranciscaNeural"
RATE = "+0%"
PITCH = "+0Hz"

recognizer = sr.Recognizer() if sr else None



async def _falar_edge(texto):
    """Gera o áudio via Edge TTS e reproduz."""
    if edge_tts is None or playsound is None:
        return

    caminho = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            caminho = f.name

        communicate = edge_tts.Communicate(
            texto,
            VOICE,
            rate=RATE,
            pitch=PITCH
        )

        await communicate.save(caminho)
        # playsound é síncrono e bloqueia o loop. 
        # Para sistemas robustos, considere rodar em um thread separado.
        playsound.playsound(caminho)
    finally:
        if caminho and os.path.exists(caminho):
            os.remove(caminho)


def falar(texto):
    """Interface síncrona para falar texto (TTS). Não imprime no console — quem chama é responsável por exibir."""
    if not texto:
        return

    # Se as dependências de voz não existirem, fica só no texto.
    if edge_tts is None or playsound is None:
        return

    try:
        # Tenta rodar o loop assíncrono
        asyncio.run(_falar_edge(texto))
    except RuntimeError:
        # Se já houver um loop rodando (comum em ambientes assíncronos)
        # usamos o threadsafe para não travar a aplicação principal
        asyncio.ensure_future(_falar_edge(texto))


def ouvir(timeout=5, limite=8):
    """Ouve o microfone e transcreve usando Whisper."""
    if sr is None or recognizer is None:
        return None

    try:
        with sr.Microphone() as source:
            # Ajuste de ruído mais curto para não atrasar a resposta
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=limite
            )

        # Usando o modelo Whisper (local ou API) via SpeechRecognition
        return recognizer.recognize_whisper(audio, language="portuguese").strip()

    except sr.WaitTimeoutError:
        return None
    except (sr.UnknownValueError, sr.RequestError):
        return None
    except Exception as e:
        print(f"❌ Erro no microfone: {e}")
        return None