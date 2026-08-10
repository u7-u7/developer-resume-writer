#!/usr/bin/env python3
"""Validate an anonymized CodeCV resume without echoing source material."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path


TEMPLATE_URL = "https://www.codecvcv.com/jianlimoban/15simple_versatile"
SECTION_ORDER = ("教育经历", "实习经历/工作经历", "项目经历", "专业技能", "奖项/校园经历", "待确认", "CodeCV 设置")
SECTIONS = set(SECTION_ORDER)
REQUIRED_LAYERS = {"入口", "核心流程", "数据模型", "异常或权限边界", "测试或运行验证"}
INTAKE_KEYS = {
    "source_kind",
    "authorized",
    "read_only",
    "history_used",
    "credentials_used",
    "submodules_used",
    "execution_used",
    "temporary_cleanup",
}
ANON_PROJECT_ID = re.compile(r"^p-[a-z0-9-]{1,20}$")
ANON_EVIDENCE_ID = re.compile(r"^e-[a-z0-9-]{1,20}$")
BULLET = re.compile(r"^- \*\*(?P<title>[^*\n｜]{1,16})\*\*｜(?P<body>\S.*)$")
PROJECT_TITLE = re.compile(r"^### \*\*某[^*\n]{0,30}\*\*(?: - .+)?$")
URL = re.compile(r"(?:https?://|www\.)[^\s)>]+", re.IGNORECASE)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
DATE = re.compile(r"(?:19|20)\d{2}(?:[./-]|年)")
ACCOUNT = re.compile(r"(?<!\w)@[A-Za-z0-9_]{2,}")
PATH = re.compile(r"(?<!:)\/(?:[\w.-]+\/){1,}[\w.-]+")
FORBIDDEN = re.compile(r"零丢失|100%|百分之百|完全|绝对|必然")
METRIC = re.compile(r"\d+(?:\.\d+)?(?:%|ms|毫秒|秒|分钟|小时|倍|万|千|人|GB|MB|QPS|TPS)", re.IGNORECASE)
LEAD = re.compile(r"^(基于|通过|围绕|采用|使用|构建|设计|优化|实现|改造|排查|拆分)")
PROJECT_INTRO = re.compile(r"^\*\*项目简介\*\*：(?P<body>\S.*)$")
INTRO_FORBIDDEN = re.compile(r"主导|独立|负责|完成|从\s*0\s*到\s*1|提升|降低|缩短|保障|显著")


@dataclass(frozen=True)
class EvidenceEntry:
    levels: frozenset[str]
    evidence_ids: frozenset[str]
    project_id: str
    fact_kind: str


@dataclass(frozen=True)
class IntakeEntry:
    source_kind: str
    authorized: bool
    read_only: bool
    history_used: bool
    credentials_used: bool
    submodules_used: bool
    execution_used: bool
    temporary_cleanup: str


def grapheme_count(text: str) -> int:
    count = 0
    previous_was_joiner = False
    for char in text:
        if unicodedata.combining(char) or 0xFE00 <= ord(char) <= 0xFE0F:
            continue
        if previous_was_joiner:
            previous_was_joiner = char == "\u200d"
            continue
        count += 1
        previous_was_joiner = char == "\u200d"
    return count


def visible_text(line: str) -> str:
    return re.sub(r"[*`_~]", "", line)


def read_text(target: str) -> str:
    return sys.stdin.read() if target == "-" else Path(target).read_text(encoding="utf-8")


def load_json(raw: str, label: str) -> dict[str, object]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label}必须是 JSON 对象") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{label}必须是 JSON 对象")
    return data


def load_evidence(raw: str) -> dict[int, EvidenceEntry]:
    entries: dict[int, EvidenceEntry] = {}
    for line, value in load_json(raw, "成果账本").items():
        if not isinstance(value, dict):
            raise ValueError("成果账本每项必须是对象")
        levels = frozenset(str(item) for item in value.get("levels", []))
        evidence_ids = frozenset(str(item) for item in value.get("evidence_ids", []))
        project_id = str(value.get("project_id", ""))
        fact_kind = str(value.get("fact_kind", ""))
        if not levels <= {"E1", "E2", "E3"} or not project_id or not evidence_ids:
            raise ValueError("成果账本缺少有效等级、匿名证据编号或项目编号")
        entries[int(line)] = EvidenceEntry(levels, evidence_ids, project_id, fact_kind)
    return entries


def load_source_evidence(raw: str) -> dict[str, dict[str, str]]:
    projects: dict[str, dict[str, str]] = {}
    for project_id, value in load_json(raw, "项目证据清单").items():
        if not ANON_PROJECT_ID.match(str(project_id)) or not isinstance(value, dict) or not isinstance(value.get("evidence"), list):
            raise ValueError("项目证据清单每个项目必须包含 evidence 列表")
        records: dict[str, str] = {}
        for record in value["evidence"]:
            if not isinstance(record, dict):
                raise ValueError("项目证据项必须是对象")
            evidence_id = str(record.get("id", ""))
            layer = str(record.get("layer", ""))
            if not ANON_EVIDENCE_ID.match(evidence_id) or layer not in REQUIRED_LAYERS:
                raise ValueError("项目证据项缺少有效匿名编号或层级")
            records[evidence_id] = layer
        projects[str(project_id)] = records
    return projects


def load_intake(raw: str) -> dict[str, IntakeEntry]:
    entries: dict[str, IntakeEntry] = {}
    for project_id, value in load_json(raw, "项目接入账本").items():
        if not ANON_PROJECT_ID.match(str(project_id)) or not isinstance(value, dict):
            raise ValueError("项目接入账本必须使用匿名项目编号和固定字段")
        if set(value) - INTAKE_KEYS:
            raise ValueError("项目接入账本包含不允许的来源字段")
        source_kind = str(value.get("source_kind", ""))
        if source_kind not in {"remote_clone", "local_directory"}:
            raise ValueError("项目接入账本缺少有效来源类型")
        entries[str(project_id)] = IntakeEntry(
            source_kind=source_kind,
            authorized=value.get("authorized") is True,
            read_only=value.get("read_only") is True,
            history_used=value.get("history_used") is True,
            credentials_used=value.get("credentials_used") is True,
            submodules_used=value.get("submodules_used") is True,
            execution_used=value.get("execution_used") is True,
            temporary_cleanup=str(value.get("temporary_cleanup", "")),
        )
    return entries


def load_banned_terms(path: Path) -> tuple[str, ...]:
    try:
        return tuple(term.strip() for term in path.read_text(encoding="utf-8").splitlines() if term.strip())
    except OSError as exc:
        raise ValueError("无法读取临时敏感词表") from exc


def validate_project_evidence(projects: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for project_id, records in projects.items():
        if len(records) < 5 or not REQUIRED_LAYERS <= set(records.values()):
            errors.append(f"项目 {project_id} 未满足五类源码证据门槛")
    return errors


def validate_intake(projects: dict[str, dict[str, str]], intakes: dict[str, IntakeEntry]) -> list[str]:
    errors: list[str] = []
    for project_id in projects:
        intake = intakes.get(project_id)
        if intake is None:
            errors.append(f"项目 {project_id} 缺少项目接入账本")
            continue
        if not intake.authorized or not intake.read_only:
            errors.append(f"项目 {project_id} 未满足访问授权或只读要求")
        if any((intake.history_used, intake.credentials_used, intake.submodules_used, intake.execution_used)):
            errors.append(f"项目 {project_id} 使用了不允许的访问方式")
        if intake.source_kind == "remote_clone" and intake.temporary_cleanup != "complete":
            errors.append(f"项目 {project_id} 的远程临时目录未清理")
    return errors


def validate(text: str, evidence: dict[int, EvidenceEntry], projects: dict[str, dict[str, str]], intakes: dict[str, IntakeEntry], banned_terms: tuple[str, ...]) -> list[str]:
    errors = validate_project_evidence(projects) + validate_intake(projects, intakes)
    lines = text.splitlines()
    markers = [line.strip() for line in lines if line.strip().startswith(":::")]
    if markers.count("::: headStart") != 1 or markers.count("::: headEnd") != 1:
        errors.append("头部区块必须各有一个 headStart 和 headEnd")
    elif markers.index("::: headStart") > markers.index("::: headEnd"):
        errors.append("头部区块顺序错误")
    if markers.count("::: start") != markers.count("::: end") or not markers.count("::: start"):
        errors.append("start 与 end 区块必须成对且至少各一个")

    seen_sections: list[str] = []
    current_section = ""
    current_project = ""
    pending_questions = 0
    project_headers = 0
    bullet_count = 0
    titles: set[str] = set()
    leads_by_project: dict[str, set[str]] = {}
    evidence_project_by_header: dict[str, str] = {}
    project_intro_by_header: set[str] = set()
    for number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if not line:
            continue
        urls = URL.findall(line)
        if urls and any(url != TEMPLATE_URL for url in urls):
            errors.append(f"第 {number} 行包含非模板链接")
        privacy_line = line.replace(TEMPLATE_URL, "")
        if EMAIL.search(privacy_line) or PHONE.search(privacy_line) or DATE.search(privacy_line) or ACCOUNT.search(privacy_line) or PATH.search(privacy_line):
            errors.append(f"第 {number} 行包含可能的身份或路径信息")
        if any(term in privacy_line for term in banned_terms):
            errors.append(f"第 {number} 行包含来源中的敏感实体")
        if "![" in line or "icon:" in line or re.search(r"<[^>]+>", line):
            errors.append(f"第 {number} 行包含不允许的图片、图标或 HTML")
        if FORBIDDEN.search(line):
            errors.append(f"第 {number} 行包含绝对或夸大表述")
        if line.startswith("## "):
            section = line[3:].strip()
            if section in SECTIONS:
                seen_sections.append(section)
                current_section = section
            elif not ("::: headStart" in "\n".join(lines[:number]) and "::: headEnd" not in "\n".join(lines[:number])):
                errors.append(f"第 {number} 行包含不在合同内的章节")
        if line.startswith("### "):
            if current_section != "项目经历" or not PROJECT_TITLE.match(line):
                errors.append(f"第 {number} 行不是泛化项目标题")
            else:
                project_headers += 1
                current_project = f"项目{project_headers}"
        intro_match = PROJECT_INTRO.match(line)
        if intro_match:
            if current_section != "项目经历" or not current_project:
                errors.append(f"第 {number} 行的项目简介不在项目经历中")
            else:
                intro = intro_match.group("body")
                intro_length = grapheme_count(visible_text(intro))
                if not 80 <= intro_length <= 120:
                    errors.append(f"第 {number} 行的项目简介应为 80–120 个字符")
                if METRIC.search(intro) or INTRO_FORBIDDEN.search(intro):
                    errors.append(f"第 {number} 行的项目简介包含个人归因或结果断言")
                project_intro_by_header.add(current_project)
        if not line.startswith("- "):
            continue
        if current_section == "CodeCV 设置":
            if not re.match(r"^- (?:模板|主色)：", line):
                errors.append(f"第 {number} 行不是允许的 CodeCV 设置")
            continue
        if current_section == "待确认":
            pending_questions += 1
            if not line.startswith("- 待确认："):
                errors.append(f"第 {number} 行不是匿名待确认问题")
            if grapheme_count(visible_text(line)) > 200:
                errors.append(f"第 {number} 行超过 200 个字符")
            continue
        match = BULLET.match(line)
        if not match:
            errors.append(f"第 {number} 行未使用“小标题｜简介”格式")
            continue
        bullet_count += 1
        title = match.group("title")
        if title in titles:
            errors.append(f"第 {number} 行的小标题重复")
        titles.add(title)
        if grapheme_count(visible_text(line)) > 200:
            errors.append(f"第 {number} 行超过 200 个字符")
        entry = evidence.get(number)
        if entry is None:
            errors.append(f"第 {number} 行缺少成果账本")
            continue
        if current_project:
            bound_project = evidence_project_by_header.setdefault(current_project, entry.project_id)
            if bound_project != entry.project_id:
                errors.append(f"第 {number} 行与同一项目标题关联了不同证据项目")
        if not {"E1", "E2"} <= entry.levels or entry.fact_kind != "可写入":
            errors.append(f"第 {number} 行未满足 E1、E2 与可写入成果门槛")
        if METRIC.search(line) and "E3" not in entry.levels:
            errors.append(f"第 {number} 行含量化指标但缺少 E3")
        project_records = projects.get(entry.project_id)
        if project_records is None or not entry.evidence_ids <= set(project_records):
            errors.append(f"第 {number} 行未关联有效项目源码证据")
        lead_match = LEAD.match(match.group("body"))
        if current_project and lead_match:
            leads = leads_by_project.setdefault(current_project, set())
            if lead_match.group(1) in leads:
                errors.append(f"第 {number} 行与同项目条目句式重复")
            leads.add(lead_match.group(1))
    if "项目经历" not in seen_sections or not project_headers or not bullet_count:
        errors.append("简历必须至少包含一个项目经历、泛化项目标题和成果条目")
    if len(evidence_project_by_header) != project_headers:
        errors.append("每个项目标题必须至少关联一条成果与一组源码证据")
    if len(project_intro_by_header) != project_headers:
        errors.append("每个项目标题必须包含一条合规的项目简介")
    if pending_questions > 5:
        errors.append("待确认问题不得超过五条")
    if seen_sections != sorted(seen_sections, key=SECTION_ORDER.index):
        errors.append("章节顺序不符合输出合同")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验匿名 CodeCV 简历，不回显简历内容")
    parser.add_argument("resume", help="简历 Markdown 文件路径，或 - 代表标准输入")
    parser.add_argument("--evidence-json", required=True, help="成果账本：行号到匿名证据对象的 JSON")
    parser.add_argument("--source-evidence-json", required=True, help="项目源码证据清单 JSON")
    parser.add_argument("--intake-json", required=True, help="项目接入账本：只含匿名编号与安全状态的 JSON")
    parser.add_argument("--banned-terms-file", type=Path, required=True, help="受限临时敏感词表；校验后立即删除")
    args = parser.parse_args()
    try:
        errors = validate(read_text(args.resume), load_evidence(args.evidence_json), load_source_evidence(args.source_evidence_json), load_intake(args.intake_json), load_banned_terms(args.banned_terms_file))
    except (OSError, ValueError) as exc:
        print(f"校验失败：{exc}")
        return 2
    if errors:
        print("校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1
    print("校验通过：结构、正文、证据、格式、字数和基础隐私规则均符合要求。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
