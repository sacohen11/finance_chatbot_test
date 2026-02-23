const chatForm = document.getElementById("chat-form");

if (chatForm) {
  chatForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const input = document.getElementById("chat-input");
    const log = document.getElementById("chat-log");
    const text = input.value.trim();

    if (!text) {
      return;
    }

    const userLine = document.createElement("p");
    userLine.innerHTML = `<strong>You:</strong> ${text}`;
    log.appendChild(userLine);

    const botLine = document.createElement("p");
    botLine.innerHTML = "<strong>Assistant:</strong> Thanks — this is a minimal demo response.";
    log.appendChild(botLine);

    input.value = "";
  });
}
