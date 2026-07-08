import os
import tempfile
import unittest
from unittest.mock import patch

import requests
from PIL import Image

from ai_service import analyze_crop_disease


class AIServiceTests(unittest.TestCase):
    def test_returns_structured_fallback_when_gemini_fails(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image_path = tmp.name

        try:
            Image.new("RGB", (80, 80), color="green").save(image_path)

            with patch("ai_service._get_api_key", return_value="dummy-key"), patch(
                "google.generativeai.GenerativeModel.generate_content", side_effect=Exception("Gemini error: boom")
            ):
                result = analyze_crop_disease(image_path)

            self.assertEqual(result["crop_name"], "Unknown")
            self.assertEqual(result["disease_name"], "Error")
            self.assertEqual(result["confidence"], "Low")
            self.assertIn("Gemini", result["additional_notes"])
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)


if __name__ == "__main__":
    unittest.main()
