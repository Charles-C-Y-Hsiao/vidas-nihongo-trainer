const fs = require("fs/promises");
const path = require("path");
const express = require("express");

const app = express();
const PORT = Number(process.env.PORT || 3003);
const ROOT_DIR = __dirname;
const OUTPUT_DIR = path.join(ROOT_DIR, "output");
const PUBLIC_DIR = path.join(ROOT_DIR, "public");

function isMarkdownFile(fileName) {
  return /^[a-zA-Z0-9._-]+\.md$/.test(fileName);
}

async function listMarkdownFiles() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  const entries = await fs.readdir(OUTPUT_DIR, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && isMarkdownFile(entry.name))
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
}

app.use(express.static(PUBLIC_DIR));

app.get("/api/files", async (_req, res, next) => {
  try {
    const files = await listMarkdownFiles();
    res.json({ files });
  } catch (error) {
    next(error);
  }
});

app.get("/api/files/:fileName", async (req, res, next) => {
  try {
    const { fileName } = req.params;
    if (!isMarkdownFile(fileName)) {
      res.status(400).json({ error: "Invalid Markdown file name." });
      return;
    }

    const filePath = path.join(OUTPUT_DIR, fileName);
    const resolvedPath = path.resolve(filePath);
    const resolvedOutputDir = path.resolve(OUTPUT_DIR);
    if (!resolvedPath.startsWith(resolvedOutputDir + path.sep)) {
      res.status(400).json({ error: "Invalid file path." });
      return;
    }

    const content = await fs.readFile(resolvedPath, "utf8");
    res.type("text/plain").send(content);
  } catch (error) {
    if (error.code === "ENOENT") {
      res.status(404).json({ error: "Markdown file not found." });
      return;
    }
    next(error);
  }
});

app.use((error, _req, res, _next) => {
  console.error(error);
  res.status(500).json({ error: "Server error." });
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`VIDAS Markdown reader running at http://localhost:${PORT}`);
  });
}

module.exports = { app, listMarkdownFiles };
