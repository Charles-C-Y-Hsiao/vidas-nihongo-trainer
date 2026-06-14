# VIDAS Nihongo Trainer

每天依照 `topics.json` 的 VIDAS 操作主題，自動組 prompt，呼叫本機 `codex` CLI，使用目前登入帳號可用的 `gpt-5.5` 產生日文學習 Markdown。

## 前置需求

1. 已安裝本機 Codex CLI。
2. 已完成 Codex CLI 登入。
3. 目前登入帳號可使用 `gpt-5.5`。

本專案只呼叫本機 `codex` CLI，不需要額外 API key。

## 使用方式

先驗證設定：

```powershell
python generate.py --check
```

產生第 1 天內容：

```powershell
python generate.py --day 1
```

產生全部天數：

```powershell
python generate.py --all
```

輸出檔案會放在 `output/`：

```text
output/day01.md
output/day02.md
```

## 可調整選項

指定其他模型：

```powershell
python generate.py --day 1 --model gpt-5.5
```

指定 Codex CLI 路徑：

```powershell
python generate.py --day 1 --codex-bin "C:\path\to\codex.exe"
```

如果 PowerShell 可以執行 `codex --version`，但 Python 找不到 `codex`，可以先設定：

```powershell
$env:CODEX_BIN="C:\完整路徑\codex.exe"
python generate.py --check
```

## 可修改檔案

- `topics.json`: 每日 VIDAS 操作主題
- `prompt_template.md`: 你的「日文句子拆解 v260613 Short v2」提示詞

## Markdown 閱讀器

安裝 Node.js 套件：

```powershell
npm install
```

啟動 Express 閱讀器：

```powershell
npm start
```

打開：

```text
http://localhost:3003
```

左側會顯示 `output/*.md` 檔案列表，右側會顯示選取的 Markdown 內容。

## GitHub Pages 發布

GitHub Pages 不能執行 Express，所以要先產生靜態版：

```powershell
npm run build:pages
```

這會產生 `docs/`：

```text
docs/index.html
docs/app.js
docs/styles.css
docs/files.json
docs/output/day01.md
```

上傳到 GitHub 後，在 repository 的 `Settings` → `Pages` 設定：

```text
Source: Deploy from a branch
Branch: main
Folder: /docs
```

儲存後等待 GitHub Pages 建置完成，就可以用手機開 GitHub Pages 網址閱讀。
