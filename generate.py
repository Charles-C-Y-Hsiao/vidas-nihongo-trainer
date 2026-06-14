from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TOPICS_PATH = ROOT / "topics.json"
PROMPT_TEMPLATE_PATH = ROOT / "prompt_template.md"
OUTPUT_DIR = ROOT / "output"
PUBLIC_DIR = ROOT / "public"
DOCS_DIR = ROOT / "docs"
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_CODEX_BIN = "codex"


@dataclass(frozen=True)
class Topic:
    day: int
    title: str
    description: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Topic":
        try:
            return cls(
                day=int(data["day"]),
                title=str(data["title"]).strip(),
                description=str(data.get("description", "")).strip(),
            )
        except KeyError as exc:
            raise ValueError(f"topics.json 缺少必要欄位: {exc.args[0]}") from exc


def load_topics(path: Path = TOPICS_PATH) -> list[Topic]:
    if not path.exists():
        raise FileNotFoundError(f"找不到主題檔案: {path}")

    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, list):
        raise ValueError("topics.json 最外層必須是陣列。")

    topics = [Topic.from_dict(item) for item in raw]
    if not topics:
        raise ValueError("topics.json 目前沒有任何主題。")

    return sorted(topics, key=lambda topic: topic.day)


def load_prompt_template(path: Path = PROMPT_TEMPLATE_PATH) -> str:
    if not path.exists():
        raise FileNotFoundError(f"找不到 prompt template: {path}")
    return path.read_text(encoding="utf-8-sig")


def render_prompt(template: str, topic: Topic) -> str:
    generation_guard = """

# 產生方式限制

請只輸出最後要寫入 Markdown 檔案的內容。
不要說明你正在使用 Codex。
不要呼叫工具、不要執行命令、不要修改檔案。
不要輸出程式碼區塊外殼。
"""

    return (
        template.replace("{{day}}", str(topic.day))
        .replace("{{title}}", topic.title)
        .replace("{{description}}", topic.description)
        + generation_guard
    )


def powershell_find_codex() -> str | None:
    if os.name != "nt":
        return None

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "(Get-Command codex -ErrorAction SilentlyContinue).Source",
    ]
    completed = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None

    candidate = completed.stdout.strip().splitlines()
    return candidate[0] if candidate else None


def resolve_codex_bin(requested: str) -> str:
    env_codex_bin = os.getenv("CODEX_BIN")
    candidate = env_codex_bin or requested or DEFAULT_CODEX_BIN
    candidate_path = Path(candidate).expanduser()

    if candidate_path.exists():
        return str(candidate_path)

    found = shutil.which(candidate)
    if found:
        return found

    if candidate == DEFAULT_CODEX_BIN:
        powershell_candidate = powershell_find_codex()
        if powershell_candidate:
            return powershell_candidate

    raise FileNotFoundError(
        "找不到 codex CLI 執行檔。\n"
        "請先確認在 PowerShell 執行 `codex --version` 是否正常。\n"
        "如果正常但 Python 找不到，請改用完整路徑，例如：\n"
        'python generate.py --day 1 --codex-bin "C:\\Program Files\\WindowsApps\\...\\codex.exe"\n'
        "或先設定環境變數：\n"
        '$env:CODEX_BIN="C:\\完整路徑\\codex.exe"'
    )


def validate_codex(codex_bin: str) -> None:
    completed = subprocess.run(
        [codex_bin, "--version"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "沒有錯誤訊息。"
        raise RuntimeError(f"codex CLI 無法執行: {details}")


def get_codex_exec_help(codex_bin: str) -> str:
    completed = subprocess.run(
        [codex_bin, "exec", "--help"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "沒有錯誤訊息。"
        raise RuntimeError(f"無法讀取 codex exec --help: {details}")
    return completed.stdout


def validate_codex_exec_options(codex_bin: str) -> None:
    help_text = get_codex_exec_help(codex_bin)
    required_options = [
        "--model",
        "--skip-git-repo-check",
        "--ephemeral",
        "--color",
        "--sandbox",
        "--output-last-message",
    ]
    missing_options = [option for option in required_options if option not in help_text]
    if missing_options:
        joined = ", ".join(missing_options)
        raise RuntimeError(f"目前 codex exec 不支援必要參數: {joined}")


def run_codex(prompt: str, model: str, codex_bin: str) -> str:
    with tempfile.TemporaryDirectory(prefix="vidas-codex-") as temp_dir:
        output_path = Path(temp_dir) / "last-message.md"
        command = [
            codex_bin,
            "exec",
            "--model",
            model,
            "--skip-git-repo-check",
            "--ephemeral",
            "--color",
            "never",
            "--sandbox",
            "read-only",
            "--output-last-message",
            str(output_path),
            "-",
        ]

        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=ROOT,
            check=False,
        )

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            details = stderr or stdout or "沒有錯誤訊息。"
            raise RuntimeError(f"codex CLI 執行失敗: {details}")

        if output_path.exists():
            markdown = output_path.read_text(encoding="utf-8").strip()
        else:
            markdown = completed.stdout.strip()

        if not markdown:
            raise RuntimeError("codex CLI 沒有產生任何 Markdown 內容。")

        return markdown


def clean_generated_markdown(markdown: str) -> str:
    lines = markdown.splitlines()
    cleaned_lines: list[str] = []

    for line in lines:
        normalized = line.strip()
        if (
            normalized.startswith("🔥 日文句子拆解")
            and "v260613 Short v2" in normalized
        ):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def write_output(topic: Topic, markdown: str, output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"day{topic.day:02d}.md"

    header = f"# Day {topic.day:02d} - {topic.title}\n\n"
    output_path.write_text(header + clean_generated_markdown(markdown) + "\n", encoding="utf-8")
    return output_path


def is_markdown_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".md"


def sync_docs(
    public_dir: Path = PUBLIC_DIR,
    output_dir: Path = OUTPUT_DIR,
    docs_dir: Path = DOCS_DIR,
) -> list[str]:
    if not public_dir.exists():
        raise FileNotFoundError(f"找不到 public 目錄: {public_dir}")

    if docs_dir.exists():
        shutil.rmtree(docs_dir)

    shutil.copytree(public_dir, docs_dir)

    docs_output_dir = docs_dir / "output"
    if output_dir.exists():
        shutil.copytree(output_dir, docs_output_dir)
        files = sorted(path.name for path in output_dir.iterdir() if is_markdown_file(path))
    else:
        docs_output_dir.mkdir(parents=True, exist_ok=True)
        files = []

    (docs_dir / "files.json").write_text(
        json.dumps({"files": files}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return files


def find_topic(topics: list[Topic], day: int) -> Topic:
    for topic in topics:
        if topic.day == day:
            return topic
    raise ValueError(f"找不到 day {day} 的主題。請確認 topics.json。")


def generate_for_topic(
    template: str,
    topic: Topic,
    model: str,
    codex_bin: str,
) -> Path:
    prompt = render_prompt(template, topic)
    markdown = run_codex(prompt=prompt, model=model, codex_bin=codex_bin)
    return write_output(topic, markdown)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用本機 codex CLI 產生 VIDAS 日文學習 Markdown 內容。"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--day", type=int, help="產生指定天數，例如 --day 1")
    group.add_argument("--all", action="store_true", help="產生 topics.json 內全部天數")
    group.add_argument("--check", action="store_true", help="只驗證設定，不產生檔案")
    parser.add_argument(
        "--model",
        default=os.getenv("CODEX_MODEL", DEFAULT_MODEL),
        help=f"codex CLI 使用的模型，預設為 {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--codex-bin",
        default=DEFAULT_CODEX_BIN,
        help="codex CLI 執行檔名稱或完整路徑，也可用 CODEX_BIN 設定。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    topics = load_topics()
    template = load_prompt_template()
    codex_bin = resolve_codex_bin(args.codex_bin)
    validate_codex(codex_bin)
    validate_codex_exec_options(codex_bin)

    print(f"codex CLI: {codex_bin}")
    print(f"model: {args.model}")

    if args.check:
        print("驗證完成：topics.json、prompt_template.md、codex CLI 都可使用。")
        return

    selected_topics = topics if args.all else [find_topic(topics, args.day)]

    for topic in selected_topics:
        output_path = generate_for_topic(
            template=template,
            topic=topic,
            model=args.model,
            codex_bin=codex_bin,
        )
        print(f"已產生: {output_path}")

    docs_files = sync_docs()
    print(f"已更新 docs: {DOCS_DIR}")
    print(f"Markdown files: {', '.join(docs_files) if docs_files else '(none)'}")


if __name__ == "__main__":
    main()
