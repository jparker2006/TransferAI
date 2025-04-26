import unittest
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_formatter import (
    render_logic_str,
    is_honors_required,
)


class TestRenderLogicStr(unittest.TestCase):
    def test_honors_requirement_note(self):
        """Test that honors requirement is displayed when only honors courses satisfy."""
        # Create a metadata object with only honors courses
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 22H", "honors": True}
                        ]
                    },
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 2BH", "honors": True}
                        ]
                    }
                ]
            }
        }
        
        # Render the logic
        rendered = render_logic_str(metadata)
        
        # Verify it contains the honors requirement warning
        self.assertIn("Only honors courses will satisfy this requirement", rendered)
        
    def test_mixed_honors_note(self):
        """Test that honors requirement is not displayed when non-honors options exist."""
        # Create a metadata object with both honors and non-honors courses
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 22H", "honors": True}
                        ]
                    },
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 22", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Render the logic
        rendered = render_logic_str(metadata)
        
        # Verify it does NOT contain the honors requirement warning
        self.assertNotIn("Only honors courses will satisfy this requirement", rendered)
        
        # But it should still list the honors courses
        self.assertIn("Honors courses accepted: MATH 22H", rendered)
        self.assertIn("Non-honors courses also accepted: MATH 22", rendered)
        
    def test_no_articulation(self):
        """Test that proper message is shown when there's no articulation."""
        metadata = {
            "no_articulation": True
        }
        
        rendered = render_logic_str(metadata)
        self.assertEqual(rendered, "❌ This course must be completed at UCSD.")
        
        # Also test with no_articulation in the logic_block
        metadata = {
            "logic_block": {
                "no_articulation": True
            }
        }
        
        rendered = render_logic_str(metadata)
        self.assertEqual(rendered, "❌ This course must be completed at UCSD.")
        
    def test_empty_logic_block(self):
        """Test that proper message is shown when the logic block is empty."""
        metadata = {
            "logic_block": {}
        }
        
        rendered = render_logic_str(metadata)
        self.assertEqual(rendered, "❌ This course must be completed at UCSD.")


if __name__ == "__main__":
    unittest.main() 