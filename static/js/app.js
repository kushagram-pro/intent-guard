function showToast(message, variant = "info") {
    const root = document.querySelector("#toast-root");
    if (!root) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${variant}`;
    toast.textContent = message;
    root.appendChild(toast);

    requestAnimationFrame(() => {
        toast.dataset.visible = "true";
    });

    setTimeout(() => {
        toast.dataset.visible = "false";
        setTimeout(() => root.removeChild(toast), 220);
    }, 3200);
}

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

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function formatSimulationResult(result) {
    const decision = result?.execution_result?.agent_decision || "UNKNOWN";
    const canExecute = result?.execution_result?.can_execute_any_action ? "Yes" : "No";
    const clarification = result?.safety_result?.clarification || {};
    const questions = Array.isArray(clarification.questions) ? clarification.questions : [];
    const primaryQuestion = clarification.primary_question || "";
    const executionLog = Array.isArray(result?.execution_result?.execution_log)
        ? result.execution_result.execution_log
        : [];

    const logHtml = executionLog.length
        ? executionLog
            .map((item) => {
                const action = escapeHtml(item.action || "Unknown action");
                const status = escapeHtml(item.execution_status || "UNKNOWN");
                const message = escapeHtml(item.message || "");
                return `<li><strong>${action}</strong> - ${status}<br><span>${message}</span></li>`;
            })
            .join("")
        : "<li>No actions were forwarded or blocked.</li>";

    const questionsHtml = questions.length
        ? questions
            .map((item, index) => `<li><strong>Q${index + 1}:</strong> ${escapeHtml(item.question || "")}</li>`)
            .join("")
        : "<li>No clarification question required.</li>";

    return `
        <div class="simulation-summary">
            <div><span>Decision</span><strong>${escapeHtml(decision)}</strong></div>
            <div><span>Can execute now</span><strong>${canExecute}</strong></div>
            <div><span>Needs clarification</span><strong>${clarification.needed ? "Yes" : "No"}</strong></div>
        </div>
        <div class="simulation-section">
            <h3>Execution outcome</h3>
            <ul>${logHtml}</ul>
        </div>
        <div class="simulation-section">
            <h3>Follow-up question for user</h3>
            <p class="follow-up-highlight">${escapeHtml(primaryQuestion || "No follow-up question generated.")}</p>
            <ul>${questionsHtml}</ul>
        </div>
    `;
}

let monitorRefreshTimer = null;

function extractMonitoredSymbol(message) {
    const intents = message?.details?.intent_data?.intents;
    if (!Array.isArray(intents)) {
        return "";
    }
    const monitorIntent = intents.find((item) => item?.type === "monitor" && item?.stock);
    return monitorIntent ? String(monitorIntent.stock).toUpperCase() : "";
}

function drawPriceChart(canvas, points) {
    if (!canvas || !Array.isArray(points) || points.length < 2) {
        return;
    }
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const padding = 24;
    const values = points.map((p) => p.c);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const spread = Math.max(max - min, 0.001);

    ctx.strokeStyle = "rgba(148, 163, 184, 0.35)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.stroke();

    ctx.strokeStyle = "#60a5fa";
    ctx.lineWidth = 2;
    ctx.beginPath();
    points.forEach((point, index) => {
        const x = padding + (index / (points.length - 1)) * (width - padding * 2);
        const y = height - padding - ((point.c - min) / spread) * (height - padding * 2);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.fillStyle = "#cbd5e1";
    ctx.font = "12px Segoe UI";
    ctx.fillText(`Low ${min.toFixed(2)}`, padding, 16);
    ctx.fillText(`High ${max.toFixed(2)}`, width - 88, 16);
}

async function refreshMonitor(symbol) {
    const panel = document.querySelector("#monitor-panel");
    const symbolNode = document.querySelector("#monitor-symbol");
    const metaNode = document.querySelector("#monitor-meta");
    const canvas = document.querySelector("#monitor-chart");
    if (!panel || !symbolNode || !metaNode || !canvas || !symbol) {
        return;
    }

    symbolNode.textContent = symbol;
    metaNode.textContent = "Fetching latest market data...";

    try {
        const response = await fetch(`/api/market/${encodeURIComponent(symbol)}`);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || "Could not load market data.");
        }
        drawPriceChart(canvas, data.points || []);
        const last = data.points?.[data.points.length - 1]?.c;
        const sourceLabel = data.source === "demo" ? "demo feed" : "free market feed";
        metaNode.textContent = last
            ? `Last price: ${Number(last).toFixed(2)} • Source: ${sourceLabel} • Auto-refreshing every 60 seconds`
            : "No latest price found.";
    } catch (error) {
        metaNode.textContent = `Monitor failed: ${error.message}`;
    }
}

function startMonitoring(symbol) {
    if (!symbol) {
        return;
    }
    if (monitorRefreshTimer) {
        clearInterval(monitorRefreshTimer);
    }
    refreshMonitor(symbol);
    monitorRefreshTimer = setInterval(() => refreshMonitor(symbol), 60000);
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
        const button = form.querySelector("button[type='submit']");
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = "Signing in…";
        try {
            const response = await postJson("/api/login", {
                username: formData.get("username"),
                password: formData.get("password")
            });
            showToast("Signed in to Intent Guard", "success");
            window.location.href = response.redirect_url;
        } catch (error) {
            errorNode.textContent = error.message;
            showToast(error.message, "error");
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    });
}

function setupSignup() {
    const form = document.querySelector("#signup-form");
    if (!form) {
        return;
    }

    const errorNode = form.querySelector('[data-role="form-error"]');
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        errorNode.textContent = "";
        const formData = new FormData(form);
        const button = form.querySelector("button[type='submit']");
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = "Creating account...";
        try {
            const response = await postJson("/api/signup", {
                name: formData.get("name"),
                username: formData.get("username"),
                password: formData.get("password")
            });
            showToast("Account created. Please log in.", "success");
            window.location.href = response.redirect_url;
        } catch (error) {
            errorNode.textContent = error.message;
            showToast(error.message, "error");
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    });
}

function setupChat() {
    const form = document.querySelector("#chat-form");
    if (!form) {
        return;
    }

    const textarea = form.querySelector("textarea");
    const button = form.querySelector("button[type='submit']");
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const message = textarea.value.trim();
        if (!message) {
            return;
        }

        renderChatMessage({ role: "user", content: message });
        textarea.value = "";
        button.disabled = true;
        button.textContent = "Sending…";

        try {
            const response = await postJson("/api/chat", { message });
            renderChatMessage(response.message);
            const monitoredSymbol = extractMonitoredSymbol(response.message);
            if (monitoredSymbol) {
                startMonitoring(monitoredSymbol);
                showToast(`Started monitoring ${monitoredSymbol}`, "success");
            }
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
            showToast(error.message, "error");
        } finally {
            button.disabled = false;
            button.textContent = "Send";
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
        const button = connectForm.querySelector("button[type='submit']");
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = "Saving…";
        try {
            const response = await postJson("/api/openclaw/connect", {
                agent_name: formData.get("agent_name"),
                agent_id: formData.get("agent_id"),
                broker: formData.get("broker"),
                mode: formData.get("mode")
            });
            statusNode.textContent = `Connected to ${response.config.agent_name} in ${response.config.mode} mode.`;
            showToast("OpenClaw profile saved", "success");
        } catch (error) {
            showToast(error.message, "error");
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    });

    simulateForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        errorNode.textContent = "";
        const formData = new FormData(simulateForm);
        const button = simulateForm.querySelector("button[type='submit']");
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = "Simulating…";
        try {
            const response = await postJson("/api/openclaw/simulate", {
                instruction: formData.get("instruction")
            });
            outputNode.innerHTML = formatSimulationResult(response.result);
            showToast("Simulation completed", "success");
        } catch (error) {
            errorNode.textContent = error.message;
            showToast(error.message, "error");
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupLogin();
    setupSignup();
    setupChat();
    setupOpenClaw();
});
