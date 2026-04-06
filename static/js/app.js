async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.detail || "Request failed.");
    }
    return data;
}

function renderChatMessage(message) {
    const thread = document.querySelector("#chat-thread");
    if (!thread) {
        return;
    }

    const article = document.createElement("article");
    article.className = `message message-${message.role}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = message.role === "assistant" ? "AI" : "You";

    const card = document.createElement("div");
    card.className = "message-card";
    const pre = document.createElement("pre");
    pre.textContent = message.content;
    card.appendChild(pre);

    if (message.summary) {
        const summaryGrid = document.createElement("div");
        summaryGrid.className = "summary-grid";
        [
            ["Decision", message.summary.decision],
            ["Risk", message.summary.risk_level],
            ["Allowed", message.summary.allowed],
            ["Blocked", message.summary.blocked],
            ["Clarify", message.summary.clarification]
        ].forEach(([label, value]) => {
            const item = document.createElement("div");
            const span = document.createElement("span");
            span.textContent = label;
            const strong = document.createElement("strong");
            strong.textContent = value;
            item.appendChild(span);
            item.appendChild(strong);
            summaryGrid.appendChild(item);
        });
        card.appendChild(summaryGrid);
    }

    article.appendChild(avatar);
    article.appendChild(card);
    thread.appendChild(article);
    thread.scrollTop = thread.scrollHeight;
}

function setupLogin() {
    const form = document.querySelector("#login-form");
    if (!form) {
        return;
    }

    const errorNode = form.querySelector('[data-role="form-error"]');
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        errorNode.textContent = "";
        const formData = new FormData(form);
        try {
            const response = await postJson("/api/login", {
                username: formData.get("username"),
                password: formData.get("password")
            });
            window.location.href = response.redirect_url;
        } catch (error) {
            errorNode.textContent = error.message;
        }
    });
}

function setupChat() {
    const form = document.querySelector("#chat-form");
    if (!form) {
        return;
    }

    const textarea = form.querySelector("textarea");
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const message = textarea.value.trim();
        if (!message) {
            return;
        }

        renderChatMessage({ role: "user", content: message });
        textarea.value = "";

        try {
            const response = await postJson("/api/chat", { message });
            renderChatMessage(response.message);
        } catch (error) {
            renderChatMessage({
                role: "assistant",
                content: `Request failed: ${error.message}`,
                summary: {
                    decision: "ERROR",
                    risk_level: "unknown",
                    allowed: 0,
                    blocked: 0,
                    clarification: 0
                }
            });
        }
    });
}

function setupOpenClaw() {
    const connectForm = document.querySelector("#openclaw-connect-form");
    const simulateForm = document.querySelector("#openclaw-simulate-form");
    if (!connectForm || !simulateForm) {
        return;
    }

    const statusNode = document.querySelector("#connect-status");
    const errorNode = simulateForm.querySelector('[data-role="simulation-error"]');
    const outputNode = document.querySelector("#simulation-output");

    connectForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const formData = new FormData(connectForm);
        const response = await postJson("/api/openclaw/connect", {
            agent_name: formData.get("agent_name"),
            agent_id: formData.get("agent_id"),
            broker: formData.get("broker"),
            mode: formData.get("mode")
        });
        statusNode.textContent = `Connected to ${response.config.agent_name} in ${response.config.mode} mode.`;
    });

    simulateForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        errorNode.textContent = "";
        const formData = new FormData(simulateForm);
        try {
            const response = await postJson("/api/openclaw/simulate", {
                instruction: formData.get("instruction")
            });
            outputNode.innerHTML = `<pre>${JSON.stringify(response.result, null, 2)}</pre>`;
        } catch (error) {
            errorNode.textContent = error.message;
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupLogin();
    setupChat();
    setupOpenClaw();
});
