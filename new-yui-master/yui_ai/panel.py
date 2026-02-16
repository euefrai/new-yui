import customtkinter as ctk
from threading import Thread
from main import iniciar_yui  # vamos adaptar já já

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# =============================
# JANELA PRINCIPAL
# =============================
app = ctk.CTk()
app.title("Yui • Painel IA")
app.geometry("900x600")
app.resizable(False, False)

# =============================
# CORES
# =============================
ROXO = "#8f00ff"
FUNDO = "#0b0f1a"

app.configure(fg_color=FUNDO)

# =============================
# HEADER
# =============================
header = ctk.CTkFrame(app, height=60, fg_color="#111528")
header.pack(fill="x")

titulo = ctk.CTkLabel(
    header,
    text="YUI • ASSISTENTE IA",
    font=("Orbitron", 20, "bold"),
    text_color=ROXO
)
titulo.pack(pady=15)

# =============================
# CHAT
# =============================
chat = ctk.CTkTextbox(
    app,
    width=850,
    height=380,
    fg_color="#0f1424",
    text_color="white",
    font=("Consolas", 13),
    border_color=ROXO,
    border_width=2
)
chat.pack(pady=10)
chat.configure(state="disabled")

def escrever_chat(texto):
    chat.configure(state="normal")
    chat.insert("end", texto + "\n")
    chat.see("end")
    chat.configure(state="disabled")

# =============================
# INPUT
# =============================
entrada = ctk.CTkEntry(
    app,
    width=700,
    height=40,
    placeholder_text="Digite algo para a Yui...",
    fg_color="#0f1424",
    text_color="white",
    border_color=ROXO
)
entrada.pack(side="left", padx=15, pady=10)

def enviar_texto():
    msg = entrada.get()
    if not msg:
        return
    entrada.delete(0, "end")
    escrever_chat(f"Você: {msg}")
    Thread(target=iniciar_yui, args=(msg, escrever_chat)).start()

btn_enviar = ctk.CTkButton(
    app,
    text="Enviar",
    width=120,
    fg_color=ROXO,
    hover_color="#b14cff",
    command=enviar_texto
)
btn_enviar.pack(side="left", padx=10)

# =============================
# BOTÃO VOZ
# =============================
def ativar_voz():
    escrever_chat("🎤 Yui está ouvindo...")
    Thread(target=iniciar_yui, args=(None, escrever_chat, True)).start()

btn_voz = ctk.CTkButton(
    app,
    text="🎤 Voz",
    width=120,
    fg_color="#1e90ff",
    hover_color="#4aa3ff",
    command=ativar_voz
)
btn_voz.pack(side="left", padx=10)

# =============================
# STATUS
# =============================
status = ctk.CTkLabel(
    app,
    text="Status: Pronta",
    font=("Consolas", 12),
    text_color="#00ffcc"
)
status.pack(pady=5)

app.mainloop()
    