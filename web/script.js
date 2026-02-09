const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");

function appendMessage(author, text, isYui) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${isYui ? "message-yui" : "message-user"}`;

  const authorEl = document.createElement("div");
  authorEl.className = "message-author";
  authorEl.textContent = author;

  const bodyEl = document.createElement("div");
  bodyEl.className = "message-body";
  bodyEl.textContent = text;

  wrapper.appendChild(authorEl);
  wrapper.appendChild(bodyEl);
  chatLog.appendChild(wrapper);
  chatLog.scrollTop = chatLog.scrollHeight;

  return wrapper;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  appendMessage("Você", text, false);
  chatInput.value = "";

  const loadingBubble = appendMessage("Yui", "Pensando...", true);
  loadingBubble.classList.add("loading");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: text }),
    });

    loadingBubble.remove();

    if (!response.ok) {
      appendMessage(
        "Yui",
        "Tive um problema ao falar com o servidor. Tente de novo.",
        true
      );
      return;
    }

    const data = await response.json();
    if (data.reply) {
      appendMessage("Yui", data.reply, true);
    } else if (data.error) {
      appendMessage("Yui", data.error, true);
    } else {
      appendMessage(
        "Yui",
        "Não consegui entender a resposta do servidor.",
        true
      );
    }
  } catch (err) {
    loadingBubble.remove();
    appendMessage(
      "Yui",
      "Erro de rede ao tentar enviar sua mensagem.",
      true
    );
  }
});

