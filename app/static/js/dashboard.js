(function () {
  "use strict";

  window.updateStatus = async function (taskId, newStatus, selectEl) {
    const card = document.querySelector(`.task-card[data-task-id="${taskId}"]`);

    if (selectEl) {
      selectEl.disabled = true;
      selectEl.style.opacity = "0.4";
    }

    try {
      const res = await fetch(`/api/tasks/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });

      if (!res.ok) {
        const err = await res.json();
        DiasporaUtils.toast(err.error || "Status update failed", "error");
        // Revert the select to its previous value
        if (selectEl) selectEl.value = card?.dataset.status || selectEl.value;
        return;
      }

      if (card) {
        card.dataset.status = newStatus;
        // Smooth opacity change for completed tasks
        card.style.transition = "opacity 0.4s ease";
        card.style.opacity = newStatus === "Completed" ? "0.55" : "1";
      }

      if (selectEl) {
        selectEl.className = `status-select status-${newStatus.toLowerCase().replace(/\s/g, "-")}`;
      }

      DiasporaUtils.toast(`Status updated to ${newStatus}`, "success");

      // Re-apply active filter
      const activeFilter = document.querySelector(".filter-btn.active")?.dataset.filter || "all";
      applyFilter(activeFilter);

    } catch (err) {
      console.error("[dashboard.js] status update error:", err);
      DiasporaUtils.toast("Network error — please try again", "error");
      if (selectEl && card) selectEl.value = card.dataset.status;
    } finally {
      if (selectEl) {
        selectEl.disabled = false;
        selectEl.style.opacity = "1";
      }
    }
  };

  // Modal 
  window.openDetail = async function (taskId) {
    const modal   = document.getElementById("detailModal");
    const content = document.getElementById("modalContent");

    modal.classList.remove("hidden");
    content.innerHTML = buildModalSkeleton();

    try {
      const res = await fetch(`/api/tasks/${taskId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const task = await res.json();
      content.innerHTML = buildModalHTML(task);
      initModalTabs(task);
    } catch (err) {
      console.error("[dashboard.js] modal load error:", err);
      content.innerHTML = `
        <div class="modal-error">
          <p>Failed to load task details.</p>
          <button class="action-btn secondary" onclick="document.getElementById('detailModal').classList.add('hidden')">Close</button>
        </div>`;
    }
  };

  window.closeModal = function (event) {
    if (event.target.id === "detailModal") {
      document.getElementById("detailModal").classList.add("hidden");
    }
  };

  // Keyboard: Escape closes modal
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") {
      document.getElementById("detailModal")?.classList.add("hidden");
    }
  });

  // Filter
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      applyFilter(btn.dataset.filter);
    });
  });

  function applyFilter(filter) {
    const cards = document.querySelectorAll(".task-card");
    let visibleCount = 0;

    cards.forEach(card => {
      const matches = filter === "all" || card.dataset.status === filter;

      card.style.display = matches ? "flex" : "none";
      if (matches) visibleCount++;
    });

    // Empty state message
    const grid     = document.getElementById("taskGrid");
    let emptyMsg   = document.getElementById("filterEmpty");

    if (visibleCount === 0 && grid) {
      if (!emptyMsg) {
        emptyMsg = document.createElement("p");
        emptyMsg.id = "filterEmpty";
        emptyMsg.className = "filter-empty-note";
        grid.appendChild(emptyMsg);
      }
      emptyMsg.textContent = `No tasks with status "${filter}".`;
      emptyMsg.style.display = "block";
    } else if (emptyMsg) {
      emptyMsg.style.display = "none";
    }
  }

  // timestamps
  document.querySelectorAll(".meta-timestamp").forEach(el => {
    const iso = el.dataset.iso;
    if (iso) {
      el.textContent = DiasporaUtils.relativeTime(iso);
      el.title = DiasporaUtils.formatDate(iso);
      el.style.cursor = "help";
    }
  });

  //Build modal HTML
  function buildModalHTML(task) {
    const { escHtml, buildEntityRows, buildStepsList, formatDate } = DiasporaUtils;

    const history = (task.status_history || [])
      .slice()        
      .reverse()
      .map(h => `
        <div class="history-row">
          <span class="history-transition">
            ${h.old_status
              ? `${escHtml(h.old_status)} <span class="history-arrow">→</span> ${escHtml(h.new_status)}`
              : `Created as <strong>${escHtml(h.new_status)}</strong>`}
          </span>
          <span class="history-time" title="${escHtml(h.changed_at || "")}">
            ${formatDate(h.changed_at)}
          </span>
        </div>
      `).join("") || `<p class="empty-note">No history yet.</p>`;

    return `
      <div class="modal-task-header">
        <span class="task-code">${escHtml(task.task_code)}</span>
        <span class="intent-tag" style="
          background:${DiasporaUtils.intentStyle(task.intent).bg};
          color:${DiasporaUtils.intentStyle(task.intent).color};
          border-color:${DiasporaUtils.intentStyle(task.intent).border}
        ">${escHtml(task.intent.replace(/_/g, " "))}</span>
        <span class="risk-badge risk-${task.risk_label}">
          ${task.risk_label.toUpperCase()} · ${task.risk_score}/100
        </span>
        <span class="modal-status-badge status-badge-${task.status.toLowerCase().replace(/\s/g,"-")}">
          ${escHtml(task.status)}
        </span>
      </div>

      <blockquote class="modal-original-request">
        "${escHtml(task.original_request)}"
      </blockquote>

      <div class="modal-meta-row">
        <span>👥 ${escHtml(task.assigned_team || "—")}</span>
        <span title="${escHtml(task.created_at || "")}">
          🕐 ${formatDate(task.created_at)}
        </span>
      </div>

      <div class="modal-section">
        <h4>Extracted Details</h4>
        <div class="entities-list">${buildEntityRows(task.entities)}</div>
      </div>

      <div class="modal-section">
        <h4>Fulfilment Steps</h4>
        <ol class="steps-list">${buildStepsList(task.steps)}</ol>
      </div>

      <div class="modal-section">
        <h4>Confirmation Messages</h4>
        <div class="message-tabs" id="modalTabs">
          <button class="msg-tab active" data-channel="whatsapp">WhatsApp</button>
          <button class="msg-tab" data-channel="email">Email</button>
          <button class="msg-tab" data-channel="sms">SMS</button>
        </div>
        <div id="modalMessageDisplay" class="message-display"></div>
      </div>

      <div class="modal-section">
        <h4>Status History</h4>
        <div class="history-list">${history}</div>
      </div>
    `;
  }

  function buildModalSkeleton() {
    return `
      <div class="skeleton-block" style="width:40%;height:1.2rem;margin-bottom:1rem"></div>
      <div class="skeleton-block" style="width:100%;height:3rem;margin-bottom:1.5rem"></div>
      <div class="skeleton-block" style="width:100%;height:8rem;margin-bottom:1rem"></div>
      <div class="skeleton-block" style="width:100%;height:6rem"></div>
    `;
  }

  function initModalTabs(task) {
    const msgs    = task.messages || {};
    const display = document.getElementById("modalMessageDisplay");

    function renderTab(channel) {
      const content   = msgs[channel] || "(No message for this channel.)";
      let header = "";
      let extra  = "";

      if (channel === "sms") {
        const len = content.length;
        extra = `<div class="sms-counter ${len > 160 ? "sms-over" : ""}">
          ${len}/160 chars ${len > 160 ? "⚠ over limit" : "✓"}
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
        <button class="copy-btn" data-copy="${DiasporaUtils.escHtml(content)}">Copy</button>
      `;

      display.querySelector(".copy-btn").addEventListener("click", e => {
        DiasporaUtils.copyToClipboard(e.currentTarget.dataset.copy, "Message copied!");
      });
    }

    renderTab("whatsapp");

    document.querySelectorAll("#modalTabs .msg-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        document.querySelectorAll("#modalTabs .msg-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        renderTab(tab.dataset.channel);
      });
    });
  }

})();