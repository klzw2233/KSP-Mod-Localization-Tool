import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from localizer import parse_parts


SIMPLE_PART = """
PART
{
    name = testEngine
    title = Test Engine
    manufacturer = Test Company
    description = Very powerful engine.
    tags = engine rocket
}
"""

TWO_PARTS = """
PART
{
    name = engineA
    title = Engine A
    description = First
    manufacturer = Co
    tags = a
}
PART
{
    name = engineB
    title = Engine B
    description = Second
    manufacturer = Co
    tags = b
}
"""

NESTED_MODULE = """
PART
{
    name = testEngine
    title = Test Engine
    manufacturer = Test Company
    description = Very powerful engine.
    tags = engine rocket
    MODULE
    {
        name = TestModule
        title = Internal Module Name
    }
}
"""


class ParsePartsTests(unittest.TestCase):
    def test_simple_part_extracts_four_safe_fields(self):
        parts = parse_parts(SIMPLE_PART)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].name, "testEngine")
        self.assertEqual(
            parts[0].fields,
            {
                "title": "Test Engine",
                "description": "Very powerful engine.",
                "manufacturer": "Test Company",
                "tags": "engine rocket",
            },
        )

    def test_multiple_parts_are_independent(self):
        parts = parse_parts(TWO_PARTS)
        self.assertEqual([p.name for p in parts], ["engineA", "engineB"])
        self.assertEqual(parts[0].fields["title"], "Engine A")
        self.assertEqual(parts[1].fields["title"], "Engine B")
        self.assertEqual(parts[0].fields["description"], "First")
        self.assertEqual(parts[1].fields["description"], "Second")

    def test_nested_module_title_is_not_extracted(self):
        parts = parse_parts(NESTED_MODULE)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].fields["title"], "Test Engine")
        self.assertNotIn("Internal Module Name", parts[0].fields.values())

    def test_hash_prefixed_values_are_skipped(self):
        text = """
PART
{
    name = alreadyLocalized
    title = #LOC_OLD_alreadyLocalized_title
    description = #autoLOC_12345
    manufacturer = #SomethingElse
    tags = leftover tags
}
"""
        parts = parse_parts(text)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].name, "alreadyLocalized")
        self.assertNotIn("title", parts[0].fields)
        self.assertNotIn("description", parts[0].fields)
        self.assertNotIn("manufacturer", parts[0].fields)
        self.assertEqual(parts[0].fields["tags"], "leftover tags")

    def test_empty_and_whitespace_values_are_skipped(self):
        text = """
PART
{
    name = blankEngine
    title =
    description =
    manufacturer = Super Co
    tags = \t
}
"""
        parts = parse_parts(text)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].name, "blankEngine")
        self.assertNotIn("title", parts[0].fields)
        self.assertNotIn("description", parts[0].fields)
        self.assertNotIn("tags", parts[0].fields)
        self.assertEqual(parts[0].fields["manufacturer"], "Super Co")

    def test_trailing_comment_is_not_part_of_value(self):
        text = """
PART
{
    name = commentedEngine
    title = Super Engine // shown in VAB
    description = Very powerful engine.
    manufacturer = Test Company
    tags = engine rocket
}
"""
        parts = parse_parts(text)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].fields["title"], "Super Engine")
        self.assertNotIn("//", parts[0].fields["title"])
        self.assertEqual(parts[0].fields["description"], "Very powerful engine.")

    def test_hash_after_leading_space_is_skipped(self):
        text = """
PART
{
    name = spacedHash
    title =  #LOC_OLD_spacedHash_title
    description = Normal text
}
"""
        parts = parse_parts(text)
        self.assertEqual(len(parts), 1)
        self.assertNotIn("title", parts[0].fields)
        self.assertEqual(parts[0].fields["description"], "Normal text")


if __name__ == "__main__":
    unittest.main()
