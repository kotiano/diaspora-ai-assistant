const DiasporaUtils = (() => {

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatKey(key) {
    return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  }

  function formatValue(val) {
    if (val === null || val === undefined) return "—";
    if (typeof val === "boolean") return val ? "Yes" : "No";
    if (typeof val === "number") return val.toLocaleString("en-KE");
    return escHtml(String(val));
  }

  function formatDate(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "—";
      return d.toLocaleString("en-KE", {
        timeZone: "Africa/Nairobi",
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return "—";
    }
  }

  function relativeTime(iso) {
    if (!iso) return "—";
    try {
      const diff = Date.now() - new Date(iso).getTime();
      const mins  = Math.floor(diff / 60000);
      const hours = Math.floor(diff / 3600000);
      const days  = Math.floor(diff / 86400000);
      if (mins  <  1) return "just now";
      if (mins  < 60) return `${mins}m ago`;
      if (hours < 24) return `${hours}h ago`;
      if (days  <  7) return `${days}d ago`;
      return formatDate(iso);
    } catch {
      return "—";
    }
  }

  let _toastTimer = null;

  function toast(message, type = "success", duration = 3500) {
    let container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      document.body.appendChild(container);
    }

    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    el.innerHTML = `
      <span class="toast-icon">${type === "success" ? "✓" : type === "error" ? "✕" : "ℹ"}</span>
      <span class="toast-msg">${escHtml(message)}</span>
    `;
    container.appendChild(el);

    requestAnimationFrame(() => el.classList.add("toast-visible"));

    setTimeout(() => {
      el.classList.remove("toast-visible");
      el.addEventListener("transitionend", () => el.remove(), { once: true });
    }, duration);
  }

  async function copyToClipboard(text, successMsg = "Copied!") {
    try {
      await navigator.clipboard.writeText(text);
      toast(successMsg, "success");
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.cssText = "position:fixed;opacity:0;pointer-events:none";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      toast(successMsg, "success");
    }
  }


  const INTENT_COLORS = {
    send_money:       { bg: "rgba(0,192,118,0.12)",  color: "#00c076", border: "rgba(0,192,118,0.3)" },
    verify_document:  { bg: "rgba(245,166,35,0.12)", color: "#f5a623", border: "rgba(245,166,35,0.3)" },
    hire_service:     { bg: "rgba(79,142,247,0.12)", color: "#4f8ef7", border: "rgba(79,142,247,0.3)" },
    airport_transfer: { bg: "rgba(192,100,247,0.12)",color: "#c064f7", border: "rgba(192,100,247,0.3)" },
    check_status:     { bg: "rgba(120,130,160,0.12)",color: "#7a82a0", border: "rgba(120,130,160,0.3)" },
  };

  function intentStyle(intent) {
    return INTENT_COLORS[intent] || INTENT_COLORS["check_status"];
  }

  function buildEntityRows(entities) {
    const entries = Object.entries(entities || {})
      .filter(([, v]) => v !== null && v !== "" && v !== undefined);

    if (entries.length === 0) {
      return `<p class="empty-note">No structured entities extracted.</p>`;
    }

    return entries.map(([k, v]) => `
      <div class="entity-row">
        <span class="entity-key">${formatKey(k)}</span>
        <span class="entity-val">${formatValue(v)}</span>
      </div>
    `).join("");
  }

  function buildStepsList(steps) {
    if (!steps || steps.length === 0) {
      return `<p class="empty-note">No steps generated.</p>`;
    }
    return steps.map((s, i) => `
      <li>
        <span class="step-num">${i + 1}</span>
        <span>${escHtml(s.description || String(s))}</span>
      </li>
    `).join("");
  }

  return {
    escHtml,
    formatKey,
    formatValue,
    formatDate,
    relativeTime,
    toast,
    copyToClipboard,
    intentStyle,
    buildEntityRows,
    buildStepsList,
  };

})();