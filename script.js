function sendMessage() {

    const input = document.getElementById("chatInput");
    const messages = document.getElementById("chatMessages");

    if (!input || !messages) return;

    const text = input.value.trim();

    if (!text) return;

    const userMessage = document.createElement("div");

    userMessage.className = "message user-message";

    userMessage.textContent = text;

    messages.appendChild(userMessage);

    input.value = "";

    setTimeout(() => {

        const botMessage = document.createElement("div");

        botMessage.className = "message bot-message";

        botMessage.textContent =
            "I can help you analyze financial, cybersecurity and agricultural risks. AI analysis will be connected to the backend in the next stage.";

        messages.appendChild(botMessage);

        messages.scrollTop = messages.scrollHeight;

    }, 600);
}


document.addEventListener("DOMContentLoaded", function () {

    const input = document.getElementById("chatInput");

    if (input) {

        input.addEventListener("keydown", function (event) {

            if (event.key === "Enter") {
                sendMessage();
            }

        });

    }

});