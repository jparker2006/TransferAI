import unittest
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_formatter import (
    render_logic_v2,
    is_honors_required
)


class TestRenderLogicV2(unittest.TestCase):
    def test_no_articulation_with_reason(self):
        """Test that no articulation with reason is properly displayed."""
        metadata = {
            "no_articulation": True,
            "no_articulation_reason": "Must be taken at UC"
        }
        
        rendered = render_logic_v2(metadata)
        self.assertIn("❌ This course must be completed at UCSD.", rendered)
        self.assertIn("Reason: Must be taken at UC", rendered)
        
    def test_no_articulation_default_reason(self):
        """Test that no articulation with default reason is properly displayed."""
        metadata = {
            "no_articulation": True
        }
        
        rendered = render_logic_v2(metadata)
        self.assertIn("❌ This course must be completed at UCSD.", rendered)
        self.assertIn("Reason: No articulation available", rendered)
        
    def test_options_formatting(self):
        """Test that options are properly formatted with complete labels."""
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "CIS 22A", "honors": False}
                        ]
                    },
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "CIS 36A", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        rendered = render_logic_v2(metadata)
        self.assertIn("**Option A (✅ Complete option)**", rendered)
        self.assertIn("**Option B (✅ Complete option)**", rendered)
        self.assertIn("CIS 22A", rendered)
        self.assertIn("CIS 36A", rendered)
        
    def test_honors_formatting(self):
        """Test that honors courses are properly labeled."""
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 22H", "honors": True}
                        ]
                    }
                ]
            }
        }
        
        rendered = render_logic_v2(metadata)
        self.assertIn("MATH 22H (honors)", rendered)
        self.assertIn("Honors courses accepted: MATH 22H", rendered)
        
    def test_multi_course_option(self):
        """Test that multi-course options are properly formatted."""
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "CIS 22A", "honors": False},
                            {"course_letters": "CIS 22B", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        rendered = render_logic_v2(metadata)
        self.assertIn("**Option A (✅ Complete option)**: CIS 22A, CIS 22B (complete all)", rendered)
        
    def test_honors_required_warning(self):
        """Test that honors requirement warning is shown when appropriate."""
        # Create logic block with only honors options
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 22H", "honors": True}
                    ]
                }
            ]
        }
        
        metadata = {"logic_block": logic_block}
        rendered = render_logic_v2(metadata)
        self.assertIn("Only honors courses will satisfy this requirement", rendered)


if __name__ == "__main__":
    unittest.main() 