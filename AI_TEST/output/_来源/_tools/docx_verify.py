#!/usr/bin/env python3
"""校对 解析.md 是否逐块覆盖 docx 原文（去空白后逐段包含性检查）。"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx_extract import W, cell_text, para_text  # noqa: E402


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def main(docx_path: str, md_path: str) -> int:
    z = zipfile.ZipFile(docx_path)
    doc = ET.fromstring(z.read("word/document.xml"))
    body = doc.find(W + "body")
    assert body is not None
    md = norm(Path(md_path).read_text(encoding="utf-8"))
    missing: list[tuple[str, str]] = []
    total = 0
    for child in body:
        if child.tag == W + "p":
            t = para_text(child).strip()
            if t:
                total += 1
                if norm(t) not in md:
                    missing.append(("p", t))
        elif child.tag == W + "tbl":
            for tr in child.findall(W + "tr"):
                for tc in tr.findall(W + "tc"):
                    t = cell_text(tc).strip()
                    if t:
                        total += 1
                        if norm(t) not in md:
                            missing.append(("tbl", t))
    print(f"[docx_verify] 原文块数: {total} 缺失块数: {len(missing)}")
    for kind, text in missing:
        print(f"  [缺失-{kind}] {text}")
    print("结果: " + ("通过" if not missing else "未通过"))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
