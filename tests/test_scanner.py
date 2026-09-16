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


if __name__ == "__main__":
    unittest.main()
