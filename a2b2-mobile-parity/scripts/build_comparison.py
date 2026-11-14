#!/usr/bin/env python3
"""Build a local left-Portal/right-iOS evidence board without editing screenshots."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re

SOURCES = {"实拍", "当前组件 fixture", "用户提供截图", "设计示意", "缺证据"}
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def esc(value):
    return html.escape(str(value), quote=True)


def required_text(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Required nonempty text: {key}")
    return value


def validate(data, base):
    required_text(data, "title")
    required_text(data, "context")
    if not isinstance(data.get("items"), list) or not data["items"]:
        raise ValueError("items must be a nonempty list")
    seen, images = set(), {}
    for item in data["items"]:
        ident = required_text(item, "id")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", ident) or ident in seen:
            raise ValueError(f"Invalid or duplicate item id: {ident}")
        seen.add(ident)
        for key in ("title", "comparison", "status", "verification"):
            required_text(item, key)
        if not isinstance(item.get("changes"), list) or not item["changes"]:
            raise ValueError(f"{ident}: changes must be nonempty")
        for change in item["changes"]:
            for key in ("key", "target", "before", "after", "reason"):
                required_text(change, key)
        for side in ("portal", "ios"):
            shot = item[side]
            if shot.get("source") not in SOURCES:
                raise ValueError(f"{ident}/{side}: invalid source")
            required_text(shot, "context")
            if not isinstance(shot.get("boxes"), list):
                raise ValueError(f"{ident}/{side}: boxes must be a list")
            if shot["source"] == "缺证据":
                if shot.get("path") is not None or shot["boxes"]:
                    raise ValueError("Missing evidence requires null path and empty boxes")
                continue
            path = (base / required_text(shot, "path")).resolve()
            if path.suffix.lower() not in EXTENSIONS:
                raise ValueError(f"Unsupported image extension: {path}")
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            filename = digest + path.suffix.lower()
            images[filename] = content
            shot.update(path=str(path), copied_path="images/" + filename, sha256=digest)
            for box in shot["boxes"]:
                required_text(box, "label")
                values = [box.get(k) for k in ("x", "y", "w", "h")]
                if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
                    raise ValueError("Box coordinates must be finite numbers")
                x, y, w, h = values
                if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 100 or y + h > 100:
                    raise ValueError(f"{ident}/{side}: box falls outside image")
    return images


def panel(shot, side):
    label = "Portal Mobile · 左" if side == "portal" else "iOS · 右"
    heading = f'<h3>{label}<span>{esc(shot["source"])}</span></h3><p class="meta">{esc(shot["context"])}</p>'
    if shot["source"] == "缺证据":
        return f'<section class="panel">{heading}<div class="missing">缺少对应截图<br>当前状态未验证</div></section>'
    boxes = []
    for b in shot["boxes"]:
        style = f'left:{b["x"]}%;top:{b["y"]}%;width:{b["w"]}%;height:{b["h"]}%'
        boxes.append(f'<div class="box" style="{style}"><b>{esc(b["label"])}</b></div>')
    return (f'<section class="panel">{heading}<div class="shot"><img src="{esc(shot["copied_path"])}" '
            f'alt="{esc(label)} 当前证据">{"".join(boxes)}</div>'
            f'<a class="original" href="{esc(shot["copied_path"])}">查看未标注原图</a></section>')


def render(data):
    cards, links = [], []
    for item in data["items"]:
        ident = esc(item["id"])
        links.append(f'<a href="#{ident}">{ident} {esc(item["title"])}</a>')
        changes = []
        for c in item["changes"]:
            changes.append(f'<li><strong>框 {esc(c["key"])} · 修改 {esc(c["target"])}</strong>'
                           f'<p>当前：{esc(c["before"])}</p><p class="after">改成：{esc(c["after"])}</p>'
                           f'<p>依据：{esc(c["reason"])}</p></li>')
        cards.append(f'<article id="{ident}"><h2>{ident} · {esc(item["title"])}</h2>'
                     f'<p class="state">{esc(item["status"])} · {esc(item["comparison"])}</p>'
                     f'<div class="pair">{panel(item["portal"], "portal")}{panel(item["ios"], "ios")}</div>'
                     f'<ol class="changes">{"".join(changes)}</ol><p class="check">验收：{esc(item["verification"])}</p></article>')
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>''' + esc(data["title"]) + '''</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef0f3;color:#202332;font:17px/1.6 system-ui,sans-serif}
main{width:1100px;max-width:none;margin:28px auto;padding:0 24px}header{margin-bottom:24px}
h1{font-size:30px}h2{margin:0;font-size:25px}h3{margin:0;font-size:20px}h3 span{float:right;font-size:14px;background:#edf0f4;padding:2px 8px;border-radius:5px}
nav{display:flex;gap:16px;flex-wrap:wrap}a{color:#234e96}article{background:white;padding:24px;border:1px solid #dce0e7;border-radius:16px;margin:24px 0;scroll-margin:20px}
.state,.meta{color:#525c6a}.state{margin:7px 0 18px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:start}.panel{min-width:0}.meta{font-size:14px;min-height:46px;margin:6px 0 10px;overflow-wrap:anywhere}
.shot{position:relative;width:100%;border:1px solid #dce0e7}.shot img{width:100%;height:auto;display:block}.box{position:absolute;border:3px solid #dc2626;pointer-events:none}
.box b{position:absolute;left:-3px;top:0;max-width:100%;background:#b91c1c;color:white;font-size:13px;line-height:1.35;padding:2px 5px;overflow-wrap:anywhere}
.original{font-size:14px;display:inline-block;margin-top:7px}.missing{min-height:420px;background:#f4f5f7;display:grid;place-content:center;text-align:center;border:2px dashed #8892a1}
.changes{padding-left:25px;margin:23px 0 0}.changes li{padding:12px 0;border-top:1px solid #e6e8ed}.changes p{margin:5px 0;overflow-wrap:anywhere}.after{font-weight:600}.check{background:#f4f6f9;padding:12px;border-radius:8px}
@media(max-width:1100px){main{margin:20px 0}}@media print{body{background:white}main{margin:0;padding:0;width:100%}article{break-before:page;border:0}header{break-after:page}nav{display:none}}
</style><main><header><h1>''' + esc(data["title"]) + '</h1><p>' + esc(data["context"]) + '</p><nav>' + ' '.join(links) + '</nav></header>' + ''.join(cards) + '</main></html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    images = validate(data, args.input.resolve().parent)
    if args.out.exists():
        raise ValueError("Output already exists; choose a fresh revision directory")
    args.out.mkdir(parents=True)
    (args.out / "images").mkdir()
    for filename, content in images.items():
        destination = args.out / "images" / filename
        destination.write_bytes(content)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != filename.split(".")[0]:
            raise ValueError("Image copy checksum mismatch")
    (args.out / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "review.html").write_text(render(data), encoding="utf-8")
    print(json.dumps({"review": str((args.out / "review.html").resolve()), "items": len(data["items"]), "images": len(images)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
