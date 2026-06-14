const appShell = document.querySelector(".app-shell");
const fileList = document.querySelector("#fileList");
const fileTitle = document.querySelector("#fileTitle");
const content = document.querySelector("#content");
const refreshButton = document.querySelector("#refreshButton");
const collapseSidebarButton = document.querySelector("#collapseSidebarButton");

const SIDEBAR_STATE_KEY = "vidas-reader-sidebar";

let activeFile = null;

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderInline(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function renderMarkdown(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let listOpen = false;

  function closeList() {
    if (listOpen) {
      html.push("</ul>");
      listOpen = false;
    }
  }

  for (const line of lines) {
    const trimmed = line.trim();

    if (!trimmed) {
      closeList();
      continue;
    }

    if (/^#{1,3}\s+/.test(trimmed)) {
      closeList();
      const level = trimmed.match(/^#+/)[0].length;
      const text = trimmed.replace(/^#{1,3}\s+/, "");
      html.push(`<h${level}>${renderInline(text)}</h${level}>`);
      continue;
    }

    if (/^[-*_]{3,}$/.test(trimmed)) {
      closeList();
      html.push("<hr>");
      continue;
    }

    if (/^[─⸻]{3,}$/.test(trimmed)) {
      closeList();
      html.push(`<div class="separator-line">${escapeHtml(trimmed)}</div>`);
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      if (!listOpen) {
        html.push("<ul>");
        listOpen = true;
      }
      html.push(`<li>${renderInline(trimmed.replace(/^[-*]\s+/, ""))}</li>`);
      continue;
    }

    closeList();
    html.push(`<p>${renderInline(trimmed)}</p>`);
  }

  closeList();
  return html.join("\n");
}

function setStatus(message) {
  content.innerHTML = `<p class="status">${escapeHtml(message)}</p>`;
}

function getShortFileName(file) {
  return file.replace(/\.md$/i, "");
}

function applySidebarState(collapsed) {
  appShell.classList.toggle("sidebar-collapsed", collapsed);
  collapseSidebarButton.textContent = collapsed ? ">" : "<";
  collapseSidebarButton.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
  collapseSidebarButton.setAttribute(
    "aria-label",
    collapsed ? "Expand sidebar" : "Collapse sidebar",
  );
  localStorage.setItem(SIDEBAR_STATE_KEY, collapsed ? "collapsed" : "expanded");
}

function initializeSidebarState() {
  const savedState = localStorage.getItem(SIDEBAR_STATE_KEY);
  applySidebarState(savedState === "collapsed");
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function fetchText(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.text();
}

async function loadFileIndex() {
  try {
    return await fetchJson("api/files");
  } catch (_error) {
    return fetchJson(`files.json?t=${Date.now()}`);
  }
}

async function loadMarkdownText(fileName) {
  const encodedFileName = encodeURIComponent(fileName);
  try {
    return await fetchText(`api/files/${encodedFileName}`);
  } catch (_error) {
    return fetchText(`output/${encodedFileName}?t=${Date.now()}`);
  }
}

function createFileButton(file) {
  const button = document.createElement("button");
  const shortLabel = document.createElement("span");
  const label = document.createElement("span");

  button.type = "button";
  button.className = "file-button";
  button.dataset.file = file;
  button.title = file;

  shortLabel.className = "file-short-label";
  shortLabel.textContent = getShortFileName(file);

  label.className = "file-label";
  label.textContent = file;

  button.append(shortLabel, label);
  button.addEventListener("click", () => loadFile(file));
  return button;
}

async function loadFiles() {
  fileList.innerHTML = "";
  setStatus("Loading file list...");

  const { files } = await loadFileIndex();
  if (!files.length) {
    fileList.innerHTML = '<p class="status">No .md files in output.</p>';
    setStatus("No Markdown files found in output.");
    fileTitle.textContent = "No files";
    return;
  }

  for (const file of files) {
    fileList.append(createFileButton(file));
  }

  await loadFile(activeFile && files.includes(activeFile) ? activeFile : files[0]);
}

async function loadFile(fileName) {
  activeFile = fileName;
  fileTitle.textContent = fileName;
  setStatus("Loading Markdown...");

  for (const button of fileList.querySelectorAll(".file-button")) {
    button.classList.toggle("active", button.dataset.file === fileName);
  }

  const markdown = await loadMarkdownText(fileName);
  content.innerHTML = renderMarkdown(markdown);
}

collapseSidebarButton.addEventListener("click", () => {
  applySidebarState(!appShell.classList.contains("sidebar-collapsed"));
});

refreshButton.addEventListener("click", () => {
  loadFiles().catch((error) => {
    fileTitle.textContent = "Load failed";
    setStatus(error.message);
  });
});

initializeSidebarState();
loadFiles().catch((error) => {
  fileTitle.textContent = "Load failed";
  setStatus(error.message);
});
