#!/usr/bin/env python3

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LOCALIZABLE_FIELDS = [
    "title",
    "description",
    "manufacturer",
    "tags",
]


class PartInfo:
    def __init__(self, name, source=None):
        self.name = name
        self.fields = {}
        self.source = source
        self.keys = {}


def _iter_part_blocks(text):
    pos = 0
    while True:
        part_match = re.search(r"\bPART\b", text[pos:])
        if not part_match:
            break
        start = pos + part_match.start()
        brace_start = text.find("{", start)
        if brace_start == -1:
            break
        depth = 1
        i = brace_start + 1
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        yield brace_start, i, text[brace_start:i]
        pos = i


def _iter_first_level_fields(lines):
    depth = 0
    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        depth += line.count("{")
        depth -= line.count("}")
        if depth != 1 or "=" not in line:
            continue
        key, value = map(str.strip, line.split("=", 1))
        if "//" in value:
            value = value.split("//", 1)[0].rstrip()
        if key == "name":
            yield index, key, value
        elif (
            key in LOCALIZABLE_FIELDS
            and value
            and not value.lstrip().startswith("#")
        ):
            yield index, key, value


def parse_parts(text):
    """
    提取 PART 块
    """

    parts = []
    for _, _, block in _iter_part_blocks(text):
        part = extract_part(block)
        if part:
            parts.append(part)
    return parts


def extract_part(block):
    """
    只读取 PART 第一层字段
    """

    part_name = None
    fields = {}
    for _, key, value in _iter_first_level_fields(block.splitlines()):
        if key == "name":
            part_name = value
        elif key in LOCALIZABLE_FIELDS:
            fields[key] = value

    if not part_name:
        return None

    part = PartInfo(part_name)
    part.fields = fields
    return part


def _replace_value(raw, new_value):
    if raw.endswith("\r\n"):
        body, ending = raw[:-2], "\r\n"
    elif raw.endswith("\n"):
        body, ending = raw[:-1], "\n"
    elif raw.endswith("\r"):
        body, ending = raw[:-1], "\r"
    else:
        body, ending = raw, ""
    eq = body.find("=")
    after = body[eq + 1 :]
    comment = ""
    split_at = after.find("//")
    if split_at != -1:
        comment = after[split_at:]
        after = after[:split_at]
    stripped = after.strip()
    if not stripped:
        return raw
    start = after.find(stripped)
    lead = after[:start]
    trail = after[start + len(stripped) :]
    return body[: eq + 1] + lead + new_value + trail + comment + ending


def _rewrite_block(block, part):
    if not part.keys:
        return block
    lines = block.splitlines(keepends=True)
    for index, key, _value in _iter_first_level_fields(lines):
        if key in part.keys:
            lines[index] = _replace_value(lines[index], part.keys[key])
    return "".join(lines)


def _rewrite_text(text, file_parts):
    out = []
    last = 0
    part_iter = iter(file_parts)
    for start, end, block in _iter_part_blocks(text):
        extracted = extract_part(block)
        if not extracted:
            continue
        part = next(part_iter)
        out.append(text[last:start])
        out.append(_rewrite_block(block, part))
        last = end
    out.append(text[last:])
    return "".join(out)


def _mod_id(mod):
    return hashlib.sha256(
        os.path.normcase(str(Path(mod).resolve())).encode("utf-8")
    ).hexdigest()[:12]


def _backup_dir(tool_root, mod):
    return Path(tool_root) / "data" / "backups" / _mod_id(mod)


def _load_mapping(backup_dir, mod):
    path = backup_dir / "mapping.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"mod_root": str(Path(mod).resolve()), "files": {}}


def _save_mapping(backup_dir, mapping):
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "mapping.json").write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _backup_if_needed(path, rel, backup_dir, mapping):
    if rel in mapping["files"]:
        return False
    dest = backup_dir / "files" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    mapping["files"][rel] = {
        "original": str(Path(path).resolve()),
        "backup": Path("files", rel).as_posix(),
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
    }
    return True


def _read_cfg(path):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _rewrite_cfg(path, new_text):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as handle:
        handle.write(new_text)
    os.replace(tmp, path)


def _rewrite_mod(mod, parts, tool_root):
    by_source = defaultdict(list)
    for part in parts:
        by_source[part.source].append(part)
    root = Path(mod)
    backup_dir = _backup_dir(tool_root, mod)
    mapping = _load_mapping(backup_dir, mod)
    for rel, file_parts in by_source.items():
        if not any(part.keys for part in file_parts):
            continue
        path = root / rel
        try:
            text = _read_cfg(path)
            new_text = _rewrite_text(text, file_parts)
            if new_text == text:
                continue
            if _backup_if_needed(path, rel, backup_dir, mapping):
                _save_mapping(backup_dir, mapping)
            _rewrite_cfg(path, new_text)
        except (OSError, UnicodeError):
            continue


def scan_mod(mod_dir):
    parts = []
    root = Path(mod_dir)

    for cfg in root.rglob("*.cfg"):

        try:
            text = cfg.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except:
            continue

        found = parse_parts(text)
        rel = cfg.relative_to(root).as_posix()
        for part in found:
            part.source = rel
        parts.extend(found)

    return parts


def build_loc_key(prefix, part_name, field, suffix=""):
    key = f"#LOC_{prefix}_{part_name}_{field}"
    if suffix:
        key += f"__{suffix}"
    return key


def _sanitize_rel(rel):
    return re.sub(r"[^A-Za-z0-9._-]", "_", rel[:-4])


def _assign_keys(parts, prefix):
    """Fill part.keys. Fallback keys emit LOC_KEY_DUPLICATE on stdout."""
    by_name_field = defaultdict(list)
    for index, part in enumerate(parts):
        for field in part.fields:
            by_name_field[(part.name, field)].append((index, part))

    for (name, field), group in by_name_field.items():
        group.sort(key=lambda item: (item[1].source or "", item[0]))
        file_seen = defaultdict(int)
        first_source = group[0][1].source
        for _, part in group:
            file_seen[part.source] += 1
            n = file_seen[part.source]
            if part.source == first_source:
                suffix = ""
            else:
                suffix = _sanitize_rel(part.source or "")
            if n > 1:
                suffix = f"{suffix}__{n}" if suffix else str(n)
            key = build_loc_key(prefix, name, field, suffix)
            part.keys[field] = key
            if suffix:
                print(f"WARNING LOC_KEY_DUPLICATE {key}")


def write_localization(parts, out_dir):

    out_dir.mkdir(parents=True, exist_ok=True)

    en_file = out_dir / "en-us.cfg"
    zh_file = out_dir / "zh-cn.cfg"

    en_lines = [
        "Localization",
        "{",
        "    en-us",
        "    {",
    ]

    zh_lines = [
        "Localization",
        "{",
        "    zh-cn",
        "    {",
    ]

    csv_rows = []

    for part in parts:

        for field, value in part.fields.items():

            key = part.keys[field]

            en_lines.append(
                f"        {key} = {value}"
            )

            zh_lines.append(
                f"        {key} = {value}"
            )

            csv_rows.append([
                key,
                value,
                ""
            ])

    en_lines += [
        "    }",
        "}",
    ]

    zh_lines += [
        "    }",
        "}",
    ]

    en_file.write_text(
        "\n".join(en_lines),
        encoding="utf-8"
    )

    zh_file.write_text(
        "\n".join(zh_lines),
        encoding="utf-8"
    )

    with open(
        out_dir / "translation.csv",
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "key",
            "en-us",
            "zh-cn"
        ])

        writer.writerows(csv_rows)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="localizer.py",
        description="Scan a KSP mod and write Localization files.",
    )
    parser.add_argument("--mod", required=True, help="Mod root directory")
    parser.add_argument("--prefix", required=True, help="LOC key prefix")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview pending keys; write nothing",
    )
    return parser.parse_args(argv)


def run(mod, prefix, dry_run=False, tool_root=None):
    if tool_root is None:
        tool_root = Path(__file__).resolve().parent

    parts = scan_mod(mod)
    _assign_keys(parts, prefix)

    print(f"Found {len(parts)} PARTs")

    keys = []
    for part in parts:
        for field in part.fields:
            keys.append(part.keys[field])
    if keys:
        print("Keys:")
        for key in keys:
            print(key)

    if dry_run:
        return

    _rewrite_mod(mod, parts, tool_root)

    loc_dir = Path(mod) / "Localization"
    write_localization(parts, loc_dir)
    print(f"Generated: {loc_dir}")


def main(argv=None):
    args = parse_args(argv)
    run(args.mod, args.prefix, args.dry_run)


if __name__ == "__main__":
    main()