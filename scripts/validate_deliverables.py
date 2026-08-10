#!/usr/bin/env python3
"""Validate anonymized resume deliverable files without echoing their contents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FILES = {
    "general": "匿名简历-通用版.md",
    "codecv": "匿名简历-CodeCV.md",
    "brief": "项目简介卡.md",
}
TEMPLATE_URL = "https://www.codecvcv.com/jianlimoban/15simple_versatile"
URL = re.compile(r"(?:https?://|www\.)[^\s)>]+", re.IGNORECASE)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
DATE = re.compile(r"(?:19|20)\d{2}(?:[./-]|年)")
BULLET = re.compile(r"^- \*\*([^*\n｜]{1,16})\*\*｜", re.MULTILINE)
BRIEF_HEADING = re.compile(r"^## (项目定位|服务场景|核心能力|技术要点|验证状态)$")


def visible_length(text: str) -> int:
    return len(re.sub(r"[*`_~]", "", text))


def load_banned_terms(path: Path) -> tuple[str, ...]:
    return tuple(item.strip() for item in path.read_text(encoding="utf-8").splitlines() if item.strip())


def validate(output_dir: Path, banned_terms: tuple[str, ...]) -> tuple[list[str], dict[str, dict[str, object]]]:
    errors: list[str] = []
    details: dict[str, dict[str, object]] = {}
    contents: dict[str, str] = {}
    for kind, filename in FILES.items():
        target = output_dir / filename
        if not target.is_file() or target.stat().st_size == 0:
            errors.append(f"缺少或为空：{filename}")
            continue
        text = target.read_text(encoding="utf-8")
        contents[kind] = text
        details[kind] = {"file": filename, "bytes": target.stat().st_size, "sha256": hashlib.sha256(text.encode()).hexdigest()}
        privacy_text = text.replace(TEMPLATE_URL, "")
        if URL.search(privacy_text) or EMAIL.search(privacy_text) or PHONE.search(privacy_text) or DATE.search(privacy_text) or any(term in privacy_text for term in banned_terms):
            errors.append(f"隐私扫描失败：{filename}")
    general = contents.get("general", "")
    codecv = contents.get("codecv", "")
    brief = contents.get("brief", "")
    if general and not all(token in general for token in ("# 匿名研发简历", "## 项目经历", "**项目简介**：")):
        errors.append("通用版缺少项目经历或项目简介")
    if codecv and not all(token in codecv for token in ("::: headStart", "::: headEnd", "## 项目经历", "**项目简介**：")):
        errors.append("CodeCV 版缺少结构或项目简介")
    if brief and not all(token in brief for token in ("# 项目简介卡", "## 项目定位", "## 服务场景", "## 核心能力", "## 技术要点", "## 验证状态")):
        errors.append("项目简介卡字段不完整")
    if brief:
        active_field = ""
        for raw_line in brief.splitlines():
            heading = BRIEF_HEADING.match(raw_line.strip())
            if heading:
                active_field = heading.group(1)
                continue
            if active_field and raw_line.strip() and visible_length(raw_line.strip()) > 120:
                errors.append(f"项目简介卡的{active_field}超过 120 个字符")
    if general and codecv:
        general_titles = set(BULLET.findall(general))
        codecv_titles = set(BULLET.findall(codecv))
        if not general_titles or general_titles != codecv_titles:
            errors.append("两份简历的成果条目不一致")
    return errors, details


def main() -> int:
    parser = argparse.ArgumentParser(description="校验匿名简历交付文件，不回显文件内容")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--banned-terms-file", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        errors, details = validate(args.output_dir, load_banned_terms(args.banned_terms_file))
    except OSError:
        errors, details = ["无法读取交付目录或临时敏感词表"], {}
    report = {"status": "passed" if not errors else "failed", "files": details, "errors": errors}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        print("交付校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1
    print("交付校验通过：简历文件、项目简介和匿名扫描均符合要求。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
