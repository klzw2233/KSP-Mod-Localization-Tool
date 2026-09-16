#!/usr/bin/env python3

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


def main():

    mod_dir = input(
        "Mod folder path: "
    ).strip()

    prefix = input(
        "LOC Prefix (e.g. MYMOD): "
    ).strip()

    parts = scan_mod(mod_dir)

    print(
        f"Found {len(parts)} PARTs"
    )

    loc_dir = (
        Path(mod_dir)
        / "Localization"
    )

    write_localization(
        parts,
        loc_dir,
        prefix
    )

    print(
        f"Generated: {loc_dir}"
    )


if __name__ == "__main__":
    main()