(() => {
  const documentId = document.querySelector('meta[name="document-id"]')?.content;
  if (!documentId) return;

  const totalPages = Number(document.getElementById("pageRangeLabel").textContent.match(/of (\d+)/)[1]);
  const batchSize = 48;
  let selectedPages = [];
  let selectedPageSet = new Set();
  let firstPage = 1;
  let draggedPage = null;
  let orderOffset = 0;
  let operationMode = "extract";
  const orderBatchSize = 48;
  const grid = document.getElementById("pageGrid");
  const list = document.getElementById("selectedOrderList");
  const orderPanel = document.getElementById("selectedOrderPanel");
  const count = document.getElementById("selectedCount");
  const remaining = document.getElementById("remainingCount");
  const footerSelection = document.getElementById("footerSelection");
  const createButton = document.getElementById("createPdf");
  const operationFeedback = document.getElementById("operationFeedback");
  let operationError = "";
  const extractMode = document.getElementById("extractMode");
  const removeMode = document.getElementById("removeMode");
  const csrf = document.querySelector('meta[name="csrf-token"]').content;

  renderBatch();

  document.getElementById("prevBatch").addEventListener("click", () => {
    firstPage = Math.max(1, firstPage - batchSize);
    renderBatch();
  });
  document.getElementById("nextBatch").addEventListener("click", () => {
    firstPage = Math.min(totalPages, firstPage + batchSize);
    renderBatch();
  });
  document.getElementById("selectAll").addEventListener("click", () => {
    setSelection(Array.from({ length: totalPages }, (_, index) => index + 1));
  });
  document.getElementById("selectOdd").addEventListener("click", () => {
    setSelection(Array.from({ length: Math.ceil(totalPages / 2) }, (_, index) => index * 2 + 1));
  });
  document.getElementById("selectEven").addEventListener("click", () => {
    setSelection(Array.from({ length: Math.floor(totalPages / 2) }, (_, index) => index * 2 + 2));
  });
  document.getElementById("clearSelection").addEventListener("click", () => setSelection([]));
  extractMode.addEventListener("click", () => setOperationMode("extract"));
  removeMode.addEventListener("click", () => setOperationMode("remove"));
  document.getElementById("applyRange").addEventListener("click", applyRange);
  document.getElementById("orderPrev").addEventListener("click", () => {
    orderOffset = Math.max(0, orderOffset - orderBatchSize);
    renderOrder();
  });
  document.getElementById("orderNext").addEventListener("click", () => {
    orderOffset = Math.min(Math.floor((selectedPages.length - 1) / orderBatchSize) * orderBatchSize, orderOffset + orderBatchSize);
    renderOrder();
  });
  document.getElementById("rangeInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") applyRange();
  });
  createButton.addEventListener("click", generate);
  document.getElementById("closeResult").addEventListener("click", closeResult);
  document.getElementById("createAnother").addEventListener("click", () => {
    closeResult();
    setSelection([]);
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  document.getElementById("resultModal").addEventListener("click", (event) => {
    if (event.target.id === "resultModal") closeResult();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeResult();
  });

  function renderBatch() {
    const lastPage = Math.min(totalPages, firstPage + batchSize - 1);
    document.getElementById("pageRangeLabel").textContent = `Pages ${firstPage}–${lastPage} of ${totalPages}`;
    document.getElementById("prevBatch").disabled = firstPage === 1;
    document.getElementById("nextBatch").disabled = lastPage === totalPages;
    grid.replaceChildren();
    const fragment = document.createDocumentFragment();
    for (let pageNumber = firstPage; pageNumber <= lastPage; pageNumber += 1) {
      fragment.append(createPageCard(pageNumber));
    }
    grid.append(fragment);
  }

  function createPageCard(pageNumber) {
    const card = document.createElement("article");
    card.className = `page-card${selectedPageSet.has(pageNumber) ? " selected" : ""}`;
    card.dataset.page = String(pageNumber);
    card.tabIndex = 0;
    card.setAttribute("role", "checkbox");
    card.setAttribute("aria-checked", String(selectedPageSet.has(pageNumber)));
    card.setAttribute("aria-label", `Page ${pageNumber}`);
    const thumb = document.createElement("div");
    thumb.className = "page-thumb";
    const loading = document.createElement("span");
    loading.className = "thumb-loading";
    loading.textContent = "Loading…";
    thumb.append(loading);
    const image = document.createElement("img");
    image.alt = `Preview of page ${pageNumber}`;
    image.loading = "lazy";
    image.src = `/pdf/${documentId}/thumbnail/${pageNumber}`;
    image.addEventListener("load", () => loading.remove(), { once: true });
    image.addEventListener("error", () => {
      loading.textContent = "Preview unavailable";
      document.getElementById("thumbnailError").classList.remove("hidden");
    }, { once: true });
    thumb.append(image);
    const check = document.createElement("span");
    check.className = "selected-check";
    check.textContent = "✓";
    const label = document.createElement("div");
    label.className = "page-number";
    label.innerHTML = `<span>Page ${pageNumber}</span>`;
    card.append(thumb, check, label);
    card.addEventListener("click", () => togglePage(pageNumber));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        togglePage(pageNumber);
      }
    });
    return card;
  }

  function togglePage(pageNumber) {
    operationError = "";
    if (selectedPageSet.has(pageNumber)) {
      selectedPageSet.delete(pageNumber);
      selectedPages.splice(selectedPages.indexOf(pageNumber), 1);
    } else {
      selectedPageSet.add(pageNumber);
      selectedPages.push(pageNumber);
    }
    updateSelection();
  }

  function setSelection(pages) {
    operationError = "";
    selectedPages = [...new Set(pages)];
    selectedPageSet = new Set(selectedPages);
    orderOffset = Math.min(orderOffset, Math.floor(Math.max(0, selectedPages.length - 1) / orderBatchSize) * orderBatchSize);
    updateSelection();
  }

  function updateSelection() {
    orderOffset = Math.min(orderOffset, Math.floor(Math.max(0, selectedPages.length - 1) / orderBatchSize) * orderBatchSize);
    count.textContent = String(selectedPages.length);
    remaining.textContent = `${totalPages - selectedPages.length} remaining`;
    const selectionLabel = `${selectedPages.length} page${selectedPages.length === 1 ? "" : "s"}`;
    const wouldRemoveAll = operationMode === "remove" && selectedPages.length === totalPages;
    footerSelection.textContent = selectedPages.length
      ? `${selectionLabel} ${operationMode === "remove" ? "to remove" : "selected"}`
      : `No pages ${operationMode === "remove" ? "marked for removal" : "selected"}`;
    document.getElementById("selectionDescription").textContent =
      operationMode === "remove"
        ? `of ${totalPages} pages marked for removal`
        : `of ${totalPages} pages selected`;
    document.getElementById("footerNote").textContent = wouldRemoveAll
      ? "Leave at least one page in the new PDF."
      : operationMode === "remove"
        ? "Marked pages will be removed; all other pages stay in order."
        : "Your original PDF will remain unchanged.";
    createButton.disabled = selectedPages.length === 0 || wouldRemoveAll;
    createButton.innerHTML = operationMode === "remove"
      ? 'Create PDF without selected pages <span>→</span>'
      : 'Create PDF for selected pages <span>→</span>';
    orderPanel.hidden = selectedPages.length === 0 || operationMode === "remove";
    operationFeedback.classList.toggle("hidden", !wouldRemoveAll && !operationError);
    operationFeedback.classList.toggle("feedback-error", Boolean(operationError));
    operationFeedback.textContent = operationError || (
      wouldRemoveAll ? "A PDF must keep at least one page. Deselect a page to continue." : ""
    );
    grid.querySelectorAll(".page-card").forEach((card) => {
      const selected = selectedPageSet.has(Number(card.dataset.page));
      card.classList.toggle("selected", selected);
      card.setAttribute("aria-checked", String(selected));
      card.setAttribute(
        "aria-label",
        `Page ${card.dataset.page}${selected ? operationMode === "remove" ? ", marked for removal" : ", selected" : ""}`,
      );
    });
    renderOrder();
  }

  function setOperationMode(mode) {
    operationMode = mode;
    operationError = "";
    grid.classList.toggle("remove-mode", mode === "remove");
    extractMode.classList.toggle("active", mode === "extract");
    removeMode.classList.toggle("active", mode === "remove");
    extractMode.setAttribute("aria-pressed", String(mode === "extract"));
    removeMode.setAttribute("aria-pressed", String(mode === "remove"));
    updateSelection();
  }

  function renderOrder() {
    list.replaceChildren();
    const pagination = document.getElementById("orderPagination");
    const end = Math.min(selectedPages.length, orderOffset + orderBatchSize);
    pagination.classList.toggle("hidden", selectedPages.length <= orderBatchSize);
    document.getElementById("orderRangeLabel").textContent =
      `Pages ${orderOffset + 1}–${end} of ${selectedPages.length}`;
    document.getElementById("orderPrev").disabled = orderOffset === 0;
    document.getElementById("orderNext").disabled = end === selectedPages.length;
    const fragment = document.createDocumentFragment();
    selectedPages.slice(orderOffset, end).forEach((pageNumber) => {
      const chip = document.createElement("div");
      chip.className = "order-chip";
      chip.draggable = true;
      chip.dataset.page = String(pageNumber);
      chip.setAttribute("aria-label", `Selected page ${pageNumber}; drag to reorder`);
      const label = document.createElement("span");
      label.textContent = String(pageNumber);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.setAttribute("aria-label", `Remove page ${pageNumber}`);
      remove.textContent = "×";
      remove.addEventListener("click", (event) => {
        event.stopPropagation();
        togglePage(pageNumber);
      });
      chip.addEventListener("dragstart", (event) => {
        draggedPage = pageNumber;
        chip.classList.add("dragging");
        event.dataTransfer.effectAllowed = "move";
      });
      chip.addEventListener("dragend", () => {
        draggedPage = null;
        chip.classList.remove("dragging");
      });
      chip.addEventListener("dragover", (event) => event.preventDefault());
      chip.addEventListener("drop", (event) => {
        event.preventDefault();
        const targetPage = Number(chip.dataset.page);
        if (draggedPage === null || draggedPage === targetPage) return;
        const from = selectedPages.indexOf(draggedPage);
        const to = selectedPages.indexOf(targetPage);
        selectedPages.splice(from, 1);
        selectedPages.splice(to, 0, draggedPage);
        orderOffset = Math.floor(to / orderBatchSize) * orderBatchSize;
        updateSelection();
      });
      chip.append(label, remove);
      fragment.append(chip);
    });
    list.append(fragment);
  }

  function applyRange() {
    const input = document.getElementById("rangeInput");
    const value = input.value.trim();
    if (!value) return rangeError("Enter a page range, such as 1-4, 8.");
    const pages = new Set();
    for (const piece of value.split(",")) {
      const part = piece.trim();
      const match = part.match(/^(\d+)(?:\s*-\s*(\d+))?$/);
      if (!match) return rangeError("Use page numbers or ranges, separated by commas.");
      const start = Number(match[1]);
      const end = match[2] ? Number(match[2]) : start;
      if (start < 1 || end < start || end > totalPages) {
        return rangeError(`Page numbers must be between 1 and ${totalPages}.`);
      }
      for (let page = start; page <= end; page += 1) pages.add(page);
    }
    setSelection([...pages]);
    const first = pages.values().next().value;
    if (first < firstPage || first >= firstPage + batchSize) {
      firstPage = Math.floor((first - 1) / batchSize) * batchSize + 1;
      renderBatch();
      updateSelection();
    }
    input.setCustomValidity("");
    input.reportValidity();
  }

  function rangeError(message) {
    const input = document.getElementById("rangeInput");
    input.setCustomValidity(message);
    input.reportValidity();
    input.focus();
  }

  async function generate() {
    if (createButton.disabled) return;
    operationError = "";
    operationFeedback.classList.add("hidden");
    createButton.disabled = true;
    createButton.innerHTML = '<span class="button-spinner" aria-hidden="true"></span> Creating your PDF…';
    try {
      const endpoint = operationMode === "remove" ? "remove" : "generate";
      const response = await fetch(`/pdf/${documentId}/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "Idempotency-Key": crypto.randomUUID(),
          Accept: "application/json",
        },
        body: JSON.stringify({ pages: [...selectedPages] }),
      });
      const result = await response.json();
      if (response.status !== 202 || !result.status_url) {
        throw new Error(result.error || "Your PDF could not be queued.");
      }
      let job;
      const deadline = Date.now() + 10 * 60 * 1000;
      do {
        await new Promise((resolve) => window.setTimeout(resolve, 600));
        if (Date.now() > deadline) {
          throw new Error("Processing is taking longer than expected. Your job may still finish; check Generated PDFs shortly.");
        }
        const statusResponse = await fetch(result.status_url, { headers: { Accept: "application/json" } });
        job = await statusResponse.json();
        if (!statusResponse.ok) throw new Error(job.error || "The processing status could not be loaded.");
        if (job.status === "pending") {
          createButton.innerHTML = '<span class="button-spinner" aria-hidden="true"></span> Processing pages…';
        }
      } while (job.status === "pending");
      if (job.status !== "complete") throw new Error(job.error || "Your PDF could not be created.");
      document.getElementById("resultDetails").textContent =
        job.operation_type === "remove"
          ? `${job.filename} keeps ${job.page_count} pages from ${job.original_filename} and removes the selected pages.`
          : `${job.filename} contains the ${job.page_count} pages you selected from ${job.original_filename}.`;
      document.getElementById("resultMeta").innerHTML =
        `<div><strong>${job.original_pages}</strong><small>ORIGINAL PAGES</small></div><div><strong>${job.page_count}</strong><small>SELECTED PAGES</small></div><div><strong>${job.duration}s</strong><small>PROCESSING TIME</small></div>`;
      document.getElementById("downloadResult").href = job.download_url;
      document.getElementById("resultModal").classList.remove("hidden");
      document.getElementById("closeResult").focus();
    } catch (error) {
      operationError = error.message || "The PDF operation failed. Please try again.";
    } finally {
      updateSelection();
    }
  }

  function closeResult() {
    document.getElementById("resultModal").classList.add("hidden");
    createButton.focus();
  }
})();
