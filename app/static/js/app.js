(() => {
  "use strict";

  /* ── 1. Dynamic Abstract Background Randomizer ── */
  const authShellBackgrounds = [
    "/static/img/abstract/sky-glass-waves.svg",
    "/static/img/abstract/geometric-orbs.svg",
    "/static/img/abstract/crystal-prism.svg",
    "/static/img/abstract/fluid-mesh.svg",
  ];

  const authHeroImages = [
    "/static/img/auth/auth-bg-1.jpg",
    "/static/img/auth/auth-bg-2.jpg",
    "/static/img/auth/auth-bg-3.jpg",
    "/static/img/auth/auth-vector-1.svg",
    "/static/img/auth/auth-vector-2.svg",
    "/static/img/auth/auth-vector-3.svg",
  ];

  const authShell = document.querySelector(".auth-shell");
  if (authShell) {
    const selectedShellBg = authShellBackgrounds[Math.floor(Math.random() * authShellBackgrounds.length)];
    authShell.style.backgroundImage = `radial-gradient(circle at 50% 0%, rgba(241, 245, 249, 0.88) 0%, rgba(226, 232, 240, 0.96) 100%), url('${selectedShellBg}')`;
    authShell.style.backgroundRepeat = "no-repeat";
    authShell.style.backgroundSize = "cover";
    authShell.style.backgroundPosition = "center center";
  }

  const authVisualHero = document.getElementById("authVisualHero");
  if (authVisualHero) {
    const heroBg = authHeroImages[Math.floor(Math.random() * authHeroImages.length)];
    authVisualHero.style.backgroundImage = `url('${heroBg}')`;
    authVisualHero.style.backgroundRepeat = "no-repeat";
    authVisualHero.style.backgroundSize = "cover";
    authVisualHero.style.backgroundPosition = "center center";
  }

  /* ── 2. Mobile Sidebar & Backdrop Drawer ── */
  const menuToggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  const sidebarBackdrop = document.getElementById("sidebarBackdrop");

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove("open");
    if (sidebarBackdrop) sidebarBackdrop.classList.remove("active");
  }

  function openSidebar() {
    if (sidebar) sidebar.classList.add("open");
    if (sidebarBackdrop) sidebarBackdrop.classList.add("active");
  }

  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", () => {
      if (sidebar.classList.contains("open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    if (sidebarBackdrop) {
      sidebarBackdrop.addEventListener("click", closeSidebar);
    }

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && sidebar.classList.contains("open")) {
        closeSidebar();
      }
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 960 && sidebar.classList.contains("open")) {
        closeSidebar();
      }
    });
  }

  /* ── 3. Toast / Flash Notification Dismissal ── */
  const flashStack = document.getElementById("flashStack");
  if (flashStack) {
    flashStack.addEventListener("click", (event) => {
      const closeBtn = event.target.closest(".flash-close");
      if (!closeBtn) return;
      const flash = closeBtn.closest(".flash");
      if (flash) {
        flash.style.opacity = "0";
        flash.style.transform = "translateY(-8px)";
        window.setTimeout(() => flash.remove(), 250);
      }
    });

    const successFlashes = flashStack.querySelectorAll(".flash-success, .flash-info");
    successFlashes.forEach((flash) => {
      window.setTimeout(() => {
        if (flash.isConnected) {
          flash.style.opacity = "0";
          flash.style.transform = "translateY(-8px)";
          window.setTimeout(() => flash.remove(), 250);
        }
      }, 6000);
    });
  }

  /* ── 4. Real-Time Table Search Filters ── */
  function initTableSearch(inputId, bodyId, countId) {
    const searchInput = document.getElementById(inputId);
    const tableBody = document.getElementById(bodyId);
    const countDisplay = document.getElementById(countId);
    if (!searchInput || !tableBody) return;

    searchInput.addEventListener("input", () => {
      const query = searchInput.value.trim().toLowerCase();
      const rows = tableBody.querySelectorAll(".table-row");
      let visibleCount = 0;

      rows.forEach((row) => {
        const searchTerm = row.dataset.searchTerm || row.textContent.toLowerCase();
        const matches = !query || searchTerm.includes(query);
        row.style.display = matches ? "" : "none";
        if (matches) visibleCount += 1;
      });

      if (countDisplay) {
        countDisplay.textContent = String(visibleCount);
      }
    });
  }

  initTableSearch("documentTableSearch", "documentsTableBody", "filteredDocCount");
  initTableSearch("generatedTableSearch", "generatedTableBody", "filteredGenCount");
  initTableSearch("historyTableSearch", "historyTableBody", "filteredHistCount");

  /* ── 5. Staggered & Intersection Observers (No Layout Shift) ── */
  const observeTargets = document.querySelectorAll(
    ".stat-card, .document-row-card, .table-row, .side-card, .tip-card, .activity-card, " +
    ".merge-document-card, .profile-card, .upload-panel, .list-panel, .analytics-card"
  );

  if ("IntersectionObserver" in window && observeTargets.length > 0) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.05, rootMargin: "0px 0px -20px 0px" });

    observeTargets.forEach((element) => {
      observer.observe(element);
    });
  }

  /* ── 6. Robust Upload Experience with Multi-Stage Progress ── */
  const fileInput = document.getElementById("pdfFile");
  const dropZone = document.getElementById("dropZone");
  if (!fileInput || !dropZone) return;

  const panel = document.querySelector(".upload-panel");
  const progress = document.getElementById("uploadProgress");
  const progressBar = document.getElementById("progressBar");
  const progressPercent = document.getElementById("uploadPercent");
  const status = document.getElementById("uploadStatus");
  const name = document.getElementById("uploadName");
  const errorBox = document.getElementById("uploadError");
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const csrfToken = csrfMeta ? csrfMeta.content : "";

  const browseBtn = document.getElementById("browseFile");
  if (browseBtn) {
    browseBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      fileInput.click();
    });
  }

  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) upload(fileInput.files[0]);
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    panel.addEventListener(eventName, (event) => {
      event.preventDefault();
      panel.classList.add("drag-over");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    panel.addEventListener(eventName, (event) => {
      event.preventDefault();
      if (eventName === "drop" && event.dataTransfer && event.dataTransfer.files[0]) {
        upload(event.dataTransfer.files[0]);
      }
      panel.classList.remove("drag-over");
    });
  });

  function upload(file) {
    errorBox.classList.add("hidden");
    if (!file.name.toLowerCase().endsWith(".pdf") || (file.type && file.type !== "application/pdf")) {
      showError("Please choose a valid PDF file (.pdf extension).");
      return;
    }

    name.textContent = file.name;
    status.textContent = `${formatBytes(file.size)} · Streaming to secure workspace…`;
    progressPercent.textContent = "0%";
    progressBar.style.width = "0%";

    progress.classList.remove("hidden");
    dropZone.classList.add("hidden");

    const body = new FormData();
    body.append("file", file);

    const request = new XMLHttpRequest();
    request.open("POST", "/pdf/upload");
    if (csrfToken) {
      request.setRequestHeader("X-CSRFToken", csrfToken);
    }
    request.setRequestHeader("Accept", "application/json");

    request.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) return;
      const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
      progressBar.style.width = `${percent}%`;
      progressPercent.textContent = `${percent}%`;

      if (percent >= 100) {
        status.textContent = "Verifying PDF signatures and parsing structure…";
        const steps = progress.querySelectorAll(".step-item");
        if (steps.length > 1) {
          steps[0].classList.add("step-done");
          steps[1].classList.add("step-active");
        }
      }
    });

    request.addEventListener("load", () => {
      let result;
      try {
        result = JSON.parse(request.responseText);
      } catch {
        result = { error: "The server returned an unexpected response." };
      }

      if (request.status >= 200 && request.status < 300 && result.workspace_url) {
        status.textContent = "Preparing page studio…";
        progressBar.style.width = "100%";
        progressPercent.textContent = "100%";
        const steps = progress.querySelectorAll(".step-item");
        if (steps.length > 2) {
          steps[1].classList.add("step-done");
          steps[2].classList.add("step-done");
        }
        window.setTimeout(() => {
          window.location.assign(result.workspace_url);
        }, 350);
        return;
      }

      showError(result.error || "The upload could not be completed.");
    });

    request.addEventListener("error", () => {
      showError("A network interruption occurred. Please verify your connection and try again.");
    });

    request.addEventListener("abort", () => {
      showError("The upload operation was cancelled.");
    });

    request.send(body);
  }

  function showError(message) {
    progress.classList.add("hidden");
    dropZone.classList.remove("hidden");
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
    fileInput.value = "";
  }

  function formatBytes(bytes) {
    if (bytes < 1024 * 1024) {
      return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
})();
