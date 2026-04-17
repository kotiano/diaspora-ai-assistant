(function () {
  "use strict";

  //  DOM refs 
  const requestInput = document.getElementById("requestInput");
  const submitBtn    = document.getElementById("submitBtn");
  const charCount    = document.getElementById("charCount");
  const errorBanner  = document.getElementById("errorBanner");
  const resultPanel  = document.getElementById("resultPanel");

  // Guard
  if (!requestInput) return;

  //Module state
  const state = {
    messages: {},
    activeChannel: "whatsapp",
  };

  //  Character counter
  requestInput.addEventListener("input", () => {
    const len = requestInput.value.length;
    charCount.textContent = `${len} / 1000`;
    charCount.style.color = len > 900 ? "var(--red)" : "var(--text-dim)";
  });

  // Example pills
  document.querySelectorAll(".example-pill").forEach(btn => {
    btn.addEventListener("click", () => {
      requestInput.value = btn.dataset.text;
      requestInput.dispatchEvent(new Event("input"));
      requestInput.focus();
      requestInput.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });

  // Submit 
  submitBtn.addEventListener("click", handleSubmit);
  // Ctrl+Enter / Cmd+Enter submits
  requestInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleSubmit();
  });

  async function handleSubmit() {
    const message = requestInput.value.trim();

    if (!message) {
      showError("Please describe what you need done.");
      requestInput.focus();
      return;
    }
    if (message.length < 10) {
      showError("Please provide a bit more detail — a sentence or two is enough.");
      return;
    }

    setLoading(true);
    hideError();

    try {
      const res = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      // Always parse JSON 
      let data;
      try {
        data = await res.json();
      } catch {
        showError("Server returned an unexpected response. Please try again.");
        return;
      }

      if (!res.ok) {
        // Show the server's error message 
        showError(data.error || `Server error (${res.status}) — please try again.`);
        return;
      }

      renderResult(data);
      DiasporaUtils.toast(`Task ${data.task_code} created`, "success");

    } catch (err) {
      showError("Network error — check your connection and try again.");
      console.error("[request.js] fetch error:", err);
    } finally {
      setLoading(false);
    }
  }

  // result panel
  function renderResult(task) {
    // Task code
    document.getElementById("resultTaskCode").textContent = task.task_code;

    // Intent tag — per-intent colour from utils
    const intentEl = document.getElementById("resultIntent");
    intentEl.textContent = task.intent.replace(/_/g, " ");
    const { bg, color, border } = DiasporaUtils.intentStyle(task.intent);
    intentEl.style.cssText = `background:${bg};color:${color};border-color:${border}`;
    intentEl.className = "intent-tag";

    // Risk badge
    const riskEl = document.getElementById("resultRisk");
    riskEl.textContent = `${task.risk_label.toUpperCase()} · ${task.risk_score}/100`;
    riskEl.className = `risk-badge risk-${task.risk_label}`;

    // Team
    document.getElementById("resultTeam").textContent = task.assigned_team || "—";

    // Entities + steps via shared utils
    document.getElementById("resultEntities").innerHTML =
      DiasporaUtils.buildEntityRows(task.entities);
    document.getElementById("resultSteps").innerHTML =
      DiasporaUtils.buildStepsList(task.steps);

    // Messages
    state.messages = task.messages || {};
    state.activeChannel = "whatsapp";

    // Reset tab active state 
    resultPanel.querySelectorAll(".msg-tab").forEach(t =>
      t.classList.toggle("active", t.dataset.channel === "whatsapp")
    );

    renderMessageTab("whatsapp");

    resultPanel.classList.remove("hidden");

    setTimeout(() => {
      resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 50);
  }

  // Message tabs 
  resultPanel.addEventListener("click", e => {
    const tab = e.target.closest(".msg-tab");
    if (!tab) return;

    resultPanel.querySelectorAll(".msg-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    state.activeChannel = tab.dataset.channel;
    renderMessageTab(tab.dataset.channel);
  });

  function renderMessageTab(channel) {
    const msgs    = state.messages;
    const display = document.getElementById("messageDisplay");

    if (!display) return;

    const content   = msgs[channel] || "(No message generated for this channel.)";
    let header = "";
    let extra  = "";

    if (channel === "sms") {
      const len       = content.length;
      const overLimit = len > 160;
      extra = `<div class="sms-counter ${overLimit ? "sms-over" : ""}">
        ${len}/160 characters ${overLimit ? "⚠ over limit" : "✓"}
      </div>`;
    } else if (channel === "email") {
      const subject = msgs.email_subject || "";
      if (subject) {
        header = `<div class="email-subject-line">
          <span class="email-subject-label">Subject:</span>
          ${DiasporaUtils.escHtml(subject)}
        </div>`;
      }
    }

    display.innerHTML = `
      ${header}
      <div class="message-body">${DiasporaUtils.escHtml(content)}</div>
      ${extra}
      <button class="copy-btn" title="Copy to clipboard">Copy</button>
    `;

    display.querySelector(".copy-btn")._rawContent = content;
    display.querySelector(".copy-btn").addEventListener("click", function () {
      DiasporaUtils.copyToClipboard(this._rawContent, "Message copied!");
    });
  }

  // UI helpers 
  function setLoading(on) {
    submitBtn.disabled = on;
    submitBtn.classList.toggle("loading", on);
    const btnText = submitBtn.querySelector(".btn-text");
    const btnIcon = submitBtn.querySelector(".btn-icon");
    if (btnText) btnText.textContent = on ? "Processing…" : "Process Request";
    if (btnIcon) btnIcon.textContent = on ? "" : "→";
  }

  function showError(msg) {
    errorBanner.textContent = msg;
    errorBanner.classList.remove("hidden");
    errorBanner.setAttribute("role", "alert");
    errorBanner.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function hideError() {
    errorBanner.classList.add("hidden");
    errorBanner.removeAttribute("role");
  }

})();