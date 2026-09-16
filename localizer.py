#!/usr/bin/env python3

import argparse
import csv
import re
from pathlib import Path

LOCALIZABLE_FIELDS = [
    "title",
    "description",
    "manufacturer",
    "tags",
]


class PartInfo:
    def __init__(self, name):
        self.name = name
        self.fields = {}


def parse_parts(text):
    """
    提取 PART 块
    """

    parts = []

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

        block = text[brace_start:i]

        part = extract_part(block)

        if part:
            parts.append(part)

        pos = i

    return parts


def extract_part(block):
    """
    只读取 PART 第一层字段
    """

    lines = block.splitlines()

    depth = 0

    part_name = None
    fields = {}

    for raw in lines:

        line = raw.strip()

        if not line or line.startswith("//"):
            continue

        depth += line.count("{")
        depth -= line.count("}")

        if depth != 1:
            continue

        if "=" not in line:
            continue

        key, value = map(str.strip, line.split("=", 1))

        if key == "name":
            part_name = value

        if key in LOCALIZABLE_FIELDS:
            fields[key] = value

    if not part_name:
        return None

    part = PartInfo(part_name)
    part.fields = fields

    return part


def scan_mod(mod_dir):
    parts = []

    for cfg in Path(mod_dir).rglob("*.cfg"):

        try:
            text = cfg.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except:
            continue

        parts.extend(parse_parts(text))

    return parts


def build_loc_key(prefix, part_name, field):
    return f"#LOC_{prefix}_{part_name}_{field}"


def write_localization(parts, out_dir, prefix):

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

            key = build_loc_key(
                prefix,
                part.name,
                field
            )

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
    # ponytail: unused until ticket 04/05 backup+logs; keep so tests can inject it
    if tool_root is None:
        tool_root = Path(__file__).resolve().parent

    parts = scan_mod(mod)

    print(f"Found {len(parts)} PARTs")

    keys = []
    for part in parts:
        for field in part.fields:
            keys.append(build_loc_key(prefix, part.name, field))
    if keys:
        print("Keys:")
        for key in keys:
            print(key)

    if dry_run:
        return

    loc_dir = Path(mod) / "Localization"
    write_localization(parts, loc_dir, prefix)
    print(f"Generated: {loc_dir}")


def main(argv=None):
    args = parse_args(argv)
    run(args.mod, args.prefix, args.dry_run)


if __name__ == "__main__":
    main()