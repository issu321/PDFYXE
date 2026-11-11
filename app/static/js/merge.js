(() => {
  const grid = document.getElementById("mergeDocumentGrid");
  if (!grid) return;

  const selected = [];
  const pageCounts = new Map(
    [...grid.querySelectorAll(".merge-document-card")].map((card) => [
      Number(card.dataset.documentId),
      Number(card.dataset.pages),
    ]),
  );
  const orderList = document.getElementById("mergeOrderList");
  const orderPanel = document.getElementById("mergeOrderPanel");
  const mergeButton = document.getElementById("mergeButton");
  const feedback = document.getElementById("mergeFeedback");
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  let draggedId = null;

  grid.querySelectorAll(".merge-document-card").forEach((card) => {
    const checkbox = card.querySelector("input");
    checkbox.addEventListener("change", () => toggleDocument(Number(card.dataset.documentId)));
    card.addEventListener("click", (event) => {
      if (event.target !== checkbox) {
        event.preventDefault();
        toggleDocument(Number(card.dataset.documentId));
      }
    });
  });
  document.getElementById("mergeSelectAll").addEventListener("click", () => {
    selected.length = 0;
    for (const id of pageCounts.keys()) selected.push(id);
    update();
  });
  document.getElementById("mergeClear").addEventListener("click", () => {
    selected.length = 0;
    update();
  });
  mergeButton.addEventListener("click", mergePdfs);
  document.getElementById("closeMergeResult").addEventListener("click", closeResult);
  document.getElementById("mergeAgain").addEventListener("click", () => {
    closeResult();
    selected.length = 0;
    update();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  document.getElementById("mergeResultModal").addEventListener("click", (event) => {
    if (event.target.id === "mergeResultModal") closeResult();
  });

  function toggleDocument(documentId) {
    const index = selected.indexOf(documentId);
    if (index >= 0) selected.splice(index, 1);
    else selected.push(documentId);
    update();
  }

  function update() {
    const selectedIds = new Set(selected);
    grid.querySelectorAll(".merge-document-card").forEach((card) => {
      const id = Number(card.dataset.documentId);
      const checked = selectedIds.has(id);
      card.classList.toggle("selected", checked);
      card.querySelector("input").checked = checked;
    });
    const totalPages = selected.reduce((total, id) => total + pageCounts.get(id), 0);
    document.getElementById("mergeCount").textContent = String(selected.length);
    document.getElementById("mergePageCount").textContent = `${totalPages} pages combined`;
    document.getElementById("mergeFooterTitle").textContent =
      selected.length < 2
        ? "Select at least two PDFs"
        : `${selected.length} PDFs · ${totalPages} pages`;
    mergeButton.disabled = selected.length < 2;
    orderPanel.hidden = selected.length === 0;
    renderOrder();
  }

  function renderOrder() {
    orderList.replaceChildren();
    selected.forEach((id, index) => {
      const source = grid.querySelector(`[data-document-id="${id}"]`);
      const item = document.createElement("div");
      item.className = "merge-order-item";
      item.draggable = true;
      item.dataset.documentId = String(id);
      item.setAttribute("aria-label", `${source.dataset.name}, position ${index + 1}; drag to reorder`);
      const number = document.createElement("span");
      number.className = "merge-order-number";
      number.textContent = String(index + 1);
      const details = document.createElement("span");
      details.className = "merge-order-details";
      const name = document.createElement("strong");
      name.textContent = source.dataset.name;
      const pages = document.createElement("small");
      pages.textContent = `${pageCounts.get(id)} pages`;
      details.append(name, pages);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "merge-order-remove";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `Remove ${source.dataset.name} from merge`);
      remove.addEventListener("click", () => toggleDocument(id));
      item.addEventListener("dragstart", (event) => {
        draggedId = id;
        item.classList.add("dragging");
        event.dataTransfer.effectAllowed = "move";
      });
      item.addEventListener("dragend", () => {
        draggedId = null;
        item.classList.remove("dragging");
      });
      item.addEventListener("dragover", (event) => event.preventDefault());
      item.addEventListener("drop", (event) => {
        event.preventDefault();
        const targetId = Number(item.dataset.documentId);
        if (draggedId === null || draggedId === targetId) return;
        const from = selected.indexOf(draggedId);
        const to = selected.indexOf(targetId);
        selected.splice(from, 1);
        selected.splice(to, 0, draggedId);
        update();
      });
      item.append(number, details, remove);
      orderList.append(item);
    });
  }

  async function mergePdfs() {
    if (selected.length < 2) return;
    feedback.classList.add("hidden");
    feedback.textContent = "";
    mergeButton.disabled = true;
    mergeButton.innerHTML = '<span class="button-spinner" aria-hidden="true"></span> Preparing merge…';
    try {
      const response = await fetch("/pdf/merge", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "Idempotency-Key": crypto.randomUUID(),
          Accept: "application/json",
        },
        body: JSON.stringify({ document_ids: [...selected] }),
      });
      const queued = await response.json();
      if (!response.ok || !queued.status_url) {
        throw new Error(queued.error || "The merge could not be queued.");
      }
      let job;
      const deadline = Date.now() + 10 * 60 * 1000;
      do {
        await new Promise((resolve) => window.setTimeout(resolve, 600));
        if (Date.now() > deadline) {
          throw new Error("Processing is taking longer than expected. Check Generated PDFs shortly.");
        }
        const statusResponse = await fetch(queued.status_url, { headers: { Accept: "application/json" } });
        job = await statusResponse.json();
        if (!statusResponse.ok) throw new Error(job.error || "The merge status could not be loaded.");
        if (job.status === "pending") {
          mergeButton.innerHTML = '<span class="button-spinner" aria-hidden="true"></span> Merging your PDFs…';
        }
      } while (job.status === "pending");
      if (job.status !== "complete") throw new Error(job.error || "The PDFs could not be merged.");
      document.getElementById("mergeResultDetails").textContent =
        `${selected.length} PDFs were combined in your chosen order.`;
      document.getElementById("mergeResultMeta").innerHTML =
        `<div><strong>${selected.length}</strong><small>SOURCE PDFS</small></div><div><strong>${job.page_count}</strong><small>COMBINED PAGES</small></div><div><strong>${job.duration}s</strong><small>PROCESSING TIME</small></div>`;
      document.getElementById("mergeDownload").href = job.download_url;
      document.getElementById("mergeResultModal").classList.remove("hidden");
      document.getElementById("closeMergeResult").focus();
    } catch (error) {
      feedback.textContent = error.message || "The merge could not be completed. Please try again.";
      feedback.classList.remove("hidden");
    } finally {
      mergeButton.disabled = selected.length < 2;
      mergeButton.innerHTML = 'Merge selected PDFs <span>→</span>';
    }
  }

  function closeResult() {
    document.getElementById("mergeResultModal").classList.add("hidden");
    mergeButton.focus();
  }
})();
