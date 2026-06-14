const fs = require("fs/promises");
const path = require("path");

const ROOT_DIR = __dirname;
const PUBLIC_DIR = path.join(ROOT_DIR, "public");
const OUTPUT_DIR = path.join(ROOT_DIR, "output");
const DOCS_DIR = path.join(ROOT_DIR, "docs");

function isMarkdownFile(fileName) {
  return /^[a-zA-Z0-9._-]+\.md$/.test(fileName);
}

async function copyDirectory(source, target) {
  await fs.mkdir(target, { recursive: true });
  const entries = await fs.readdir(source, { withFileTypes: true });

  for (const entry of entries) {
    const sourcePath = path.join(source, entry.name);
    const targetPath = path.join(target, entry.name);

    if (entry.isDirectory()) {
      await copyDirectory(sourcePath, targetPath);
    } else if (entry.isFile()) {
      await fs.copyFile(sourcePath, targetPath);
    }
  }
}

async function buildPages() {
  await fs.rm(DOCS_DIR, { recursive: true, force: true });
  await copyDirectory(PUBLIC_DIR, DOCS_DIR);
  await copyDirectory(OUTPUT_DIR, path.join(DOCS_DIR, "output"));

  const outputEntries = await fs.readdir(OUTPUT_DIR, { withFileTypes: true });
  const files = outputEntries
    .filter((entry) => entry.isFile() && isMarkdownFile(entry.name))
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

  await fs.writeFile(
    path.join(DOCS_DIR, "files.json"),
    JSON.stringify({ files }, null, 2) + "\n",
    "utf8",
  );

  console.log(`Built GitHub Pages files in ${DOCS_DIR}`);
  console.log(`Markdown files: ${files.join(", ") || "(none)"}`);
}

buildPages().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
