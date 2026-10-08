#!/usr/bin/env python3
"""docx 结构提取：按正文顺序输出段落/表格/图片/超链接/run 格式，用于完整转录核对。"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def para_text(p: ET.Element) -> str:
    parts: list[str] = []
    for node in p.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag == W + "tab":
            parts.append("\t")
        elif node.tag == W + "br":
            parts.append("\n")
    return "".join(parts)


def para_style(p: ET.Element) -> str | None:
    ppr = p.find(W + "pPr")
    if ppr is None:
        return None
    st = ppr.find(W + "pStyle")
    return st.get(W + "val") if st is not None else None


def para_num(p: ET.Element) -> dict | None:
    ppr = p.find(W + "pPr")
    if ppr is None:
        return None
    num = ppr.find(W + "numPr")
    if num is None:
        return None
    ilvl = num.find(W + "ilvl")
    numid = num.find(W + "numId")
    return {
        "ilvl": ilvl.get(W + "val") if ilvl is not None else None,
        "numId": numid.get(W + "val") if numid is not None else None,
    }


def para_images(p: ET.Element, rels: dict[str, str]) -> list[dict]:
    out: list[dict] = []
    for blip in p.iter(A + "blip"):
        rid = blip.get(R + "embed")
        if rid:
            out.append({"rid": rid, "target": rels.get(rid)})
    return out


def run_props(r: ET.Element) -> dict:
    rpr = r.find(W + "rPr")
    bold = False
    italic = False
    if rpr is not None:
        b = rpr.find(W + "b")
        i = rpr.find(W + "i")
        bold = b is not None and b.get(W + "val") not in ("0", "false")
        italic = i is not None and i.get(W + "val") not in ("0", "false")
    return {"b": bold, "i": italic}


def para_runs(p: ET.Element) -> list[dict]:
    out: list[dict] = []
    for r in p.findall(W + "r"):
        text = "".join((t.text or "") for t in r.findall(W + "t"))
        props = run_props(r)
        if text:
            out.append({"t": text, "b": props["b"], "i": props["i"]})
    return out


def para_hyperlinks(p: ET.Element, rels: dict[str, str]) -> list[dict]:
    out: list[dict] = []
    for link in p.findall(W + "hyperlink"):
        rid = link.get(R + "id")
        text = "".join((t.text or "") for t in link.iter(W + "t"))
        out.append({"rid": rid, "target": rels.get(rid or ""), "text": text})
    return out


def cell_text(tc: ET.Element) -> str:
    texts = [para_text(p).strip() for p in tc.findall(W + "p")]
    return "\n".join(t for t in texts if t)


def main(path: str, out_path: str | None = None) -> None:
    z = zipfile.ZipFile(path)
    doc = ET.fromstring(z.read("word/document.xml"))
    rels: dict[str, str] = {}
    rl = ET.fromstring(z.read("word/_rels/document.xml.rels"))
    for rel in rl:
        rels[rel.get("Id", "")] = rel.get("Target", "")
    body = doc.find(W + "body")
    assert body is not None
    lines: list[str] = []
    idx = 0
    for child in body:
        if child.tag == W + "p":
            idx += 1
            lines.append(
                json.dumps(
                    {
                        "i": idx,
                        "type": "p",
                        "style": para_style(child),
                        "num": para_num(child),
                        "images": para_images(child, rels),
                        "links": para_hyperlinks(child, rels),
                        "runs": para_runs(child),
                        "text": para_text(child),
                    },
                    ensure_ascii=False,
                )
            )
        elif child.tag == W + "tbl":
            idx += 1
            rows = [
                [cell_text(tc) for tc in tr.findall(W + "tc")]
                for tr in child.findall(W + "tr")
            ]
            lines.append(json.dumps({"i": idx, "type": "tbl", "rows": rows}, ensure_ascii=False))
        else:
            lines.append(json.dumps({"i": idx, "type": "other", "tag": child.tag}, ensure_ascii=False))
    text = "\n".join(lines)
    if out_path:
        Path(out_path).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
