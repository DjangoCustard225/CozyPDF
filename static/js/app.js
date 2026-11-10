/*
  CozyPDF – the JavaScript for every page.

  It has three parts:
    1. Theme toggle (light / dark) – runs on every page.
    2. Search and category filter – runs on the home page.
    3. Upload form – runs on each tool page. It sends the files to the
       API with a progress bar and shows a download button at the end.
*/

// The version number main.py puts on the <html> tag (see static_version() there).
const STATIC_VERSION = document.documentElement.dataset.staticVersion;

// HTML for one icon from static/icons.svg (same as icon() in the templates).
function iconHTML(name, extraClass = "") {
  return `<svg class="icon ${extraClass}" aria-hidden="true"><use href="/static/icons.svg?v=${STATIC_VERSION}#${name}"></use></svg>`;
}

// Turn a number of bytes into text like "1.4 MB".
function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

/* ------------------------------------------------------------------ */
/* 1. Theme toggle                                                     */
/* ------------------------------------------------------------------ */
function setupThemeToggle() {
  const button = document.getElementById("theme-toggle");
  if (!button) return;

  button.addEventListener("click", () => {
    const root = document.documentElement;
    const newTheme = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = newTheme;
    try {
      localStorage.setItem("theme", newTheme);
    } catch (error) {
      // Private browsing can block storage. The toggle still works for this page.
    }
  });
}

/* ------------------------------------------------------------------ */
/* 2. Home page: search box and category chips                         */
/* ------------------------------------------------------------------ */
function setupToolFilter() {
  const searchInput = document.getElementById("tool-search");
  if (!searchInput) return; // we are not on the home page

  const chips = document.querySelectorAll("#category-chips .chip");
  const cards = document.querySelectorAll("#tools .tool-card");
  const noResults = document.getElementById("no-results");
  let activeCategory = "All";

  function applyFilter() {
    const query = searchInput.value.trim().toLowerCase();
    let visibleCount = 0;

    cards.forEach((card) => {
      const matchesSearch = card.dataset.search.includes(query);
      const matchesCategory = activeCategory === "All" || card.dataset.category === activeCategory;
      const show = matchesSearch && matchesCategory;
      card.hidden = !show;
      if (show) visibleCount++;
    });

    noResults.hidden = visibleCount > 0;
  }

  searchInput.addEventListener("input", applyFilter);

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      activeCategory = chip.dataset.category;
      applyFilter();
    });
  });
}

/* ------------------------------------------------------------------ */
/* 3. Tool page: choose files, upload, download                        */
/* ------------------------------------------------------------------ */
function setupToolForm() {
  const form = document.getElementById("tool-form");
  if (!form) return; // we are not on a tool page

  // Settings that the template put on the <form> as data-* attributes
  const endpoint = form.dataset.endpoint;          // e.g. "/api/merge"
  const fieldName = form.dataset.field;            // "file" or "files"
  const allowMultiple = form.dataset.multiple === "true";
  const allowedTypes = form.dataset.accept.split(","); // e.g. [".pdf"]

  // Elements we will update
  const fileInput = document.getElementById("file-input");
  const dropzone = document.getElementById("dropzone");
  const fileList = document.getElementById("file-list");
  const submitButton = document.getElementById("submit-button");
  const progress = document.getElementById("progress");
  const progressBar = document.getElementById("progress-bar");
  const progressLabel = document.getElementById("progress-label");
  const progressPercent = document.getElementById("progress-percent");
  const errorBox = document.getElementById("error");
  const errorText = document.getElementById("error-text");
  const resultBox = document.getElementById("result");
  const resultInfo = document.getElementById("result-info");
  const downloadLink = document.getElementById("download-link");
  const restartButton = document.getElementById("restart-button");

  let selectedFiles = []; // the files the user picked, in order

  // ----- Messages -----
  function showError(message) {
    errorText.textContent = message;
    errorBox.hidden = false;
  }

  function hideError() {
    errorBox.hidden = true;
  }

  // ----- Adding and removing files -----
  function hasAllowedType(file) {
    const name = file.name.toLowerCase();
    return allowedTypes.some((type) => name.endsWith(type));
  }

  function addFiles(newFiles) {
    hideError();
    for (const file of newFiles) {
      if (!hasAllowedType(file)) {
        showError(`"${file.name}" is not a supported file type.`);
        continue;
      }
      if (allowMultiple) {
        selectedFiles.push(file);
      } else {
        selectedFiles = [file]; // single-file tools keep only the latest file
      }
    }
    renderFileList();
  }

  function moveFile(index, direction) {
    const newIndex = index + direction;
    // Swap the two files
    [selectedFiles[index], selectedFiles[newIndex]] = [selectedFiles[newIndex], selectedFiles[index]];
    renderFileList();
  }

  function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
  }

  // Build one <li> per selected file.
  function renderFileList() {
    fileList.innerHTML = "";

    selectedFiles.forEach((file, index) => {
      const item = document.createElement("li");
      item.className = "file-item";
      item.innerHTML = `
        ${iconHTML("file", "file-icon")}
        <div class="file-info">
          <div class="file-name"></div>
          <div class="file-size">${formatSize(file.size)}</div>
        </div>
        <div class="file-actions"></div>
      `;
      // Set the name with textContent so odd file names can't break the HTML.
      item.querySelector(".file-name").textContent = file.name;

      const actions = item.querySelector(".file-actions");

      // Up/down buttons let the user choose the order (for merging).
      if (allowMultiple && selectedFiles.length > 1) {
        actions.append(
          makeIconButton("chevron-up", "Move up", index === 0, () => moveFile(index, -1)),
          makeIconButton("chevron-down", "Move down", index === selectedFiles.length - 1, () => moveFile(index, 1))
        );
      }
      const removeButton = makeIconButton("x", "Remove", false, () => removeFile(index));
      removeButton.classList.add("remove");
      actions.append(removeButton);

      fileList.append(item);
    });
  }

  function makeIconButton(icon, label, disabled, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.title = label;
    button.setAttribute("aria-label", label);
    button.disabled = disabled;
    button.innerHTML = iconHTML(icon);
    button.addEventListener("click", onClick);
    return button;
  }

  // Files chosen with the "browse" dialog
  fileInput.addEventListener("change", () => {
    addFiles(fileInput.files);
    fileInput.value = ""; // so choosing the same file again still works
  });

  // Files dragged onto the drop zone
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragging");
    });
  });
  dropzone.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));

  // ----- Sending the form -----
  form.addEventListener("submit", (event) => {
    event.preventDefault(); // stop the browser from leaving the page
    hideError();

    if (selectedFiles.length === 0) {
      showError(allowMultiple ? "Please add some files first." : "Please add a file first.");
      return;
    }

    // FormData collects the option fields (inputs with a name) from the form.
    const formData = new FormData(form);
    selectedFiles.forEach((file) => formData.append(fieldName, file));

    upload(formData);
  });

  // We use XMLHttpRequest (instead of fetch) because it can report upload progress.
  function upload(formData) {
    const request = new XMLHttpRequest();
    request.open("POST", endpoint);
    request.responseType = "blob"; // the answer is a file

    setWorking(true);

    request.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) return;
      const percent = Math.round((event.loaded / event.total) * 100);
      progressBar.style.width = percent + "%";
      progressPercent.textContent = percent + "%";
    });

    // Upload finished, now the server is working on the file
    request.upload.addEventListener("load", () => {
      progressLabel.textContent = "Processing…";
      progressPercent.textContent = "";
      progress.classList.add("working");
    });

    request.addEventListener("load", async () => {
      setWorking(false);
      if (request.status === 200) {
        showResult(request.response, getFileName(request));
      } else {
        showError(await readErrorMessage(request.response));
      }
    });

    request.addEventListener("error", () => {
      setWorking(false);
      showError("Couldn't reach the server. Check your connection and try again.");
    });

    request.send(formData);
  }

  function setWorking(isWorking) {
    submitButton.disabled = isWorking;
    progress.hidden = !isWorking;
    progress.classList.remove("working");
    progressBar.style.width = "0%";
    progressLabel.textContent = "Uploading…";
    progressPercent.textContent = "0%";
  }

  // The server sends the file name in the "Content-Disposition" header.
  function getFileName(request) {
    const header = request.getResponseHeader("Content-Disposition") || "";
    const match = header.match(/filename="([^"]+)"/);
    return match ? match[1] : "download";
  }

  // Errors come back as JSON like {"detail": "Something went wrong"}.
  async function readErrorMessage(blob) {
    try {
      const data = JSON.parse(await blob.text());
      if (typeof data.detail === "string") return data.detail;
      if (Array.isArray(data.detail)) return "Please fill in all the required options.";
    } catch (error) {
      // The answer wasn't JSON. Fall through to the general message.
    }
    return "Something went wrong while processing your file.";
  }

  // ----- Showing the result -----
  let downloadUrl = null;

  function showResult(blob, fileName) {
    if (downloadUrl) URL.revokeObjectURL(downloadUrl); // free the old one
    downloadUrl = URL.createObjectURL(blob);

    downloadLink.href = downloadUrl;
    downloadLink.download = fileName;
    resultInfo.textContent = `${fileName} · ${formatSize(blob.size)}`;

    form.hidden = true;
    resultBox.hidden = false;
  }

  restartButton.addEventListener("click", () => {
    selectedFiles = [];
    renderFileList();
    hideError();
    resultBox.hidden = true;
    form.hidden = false;
  });
}

/* ------------------------------------------------------------------ */
/* Start everything                                                    */
/* ------------------------------------------------------------------ */
setupThemeToggle();
setupToolFilter();
setupToolForm();
