import json
import mimetypes

from PIL import Image
import google.generativeai as genai

from config import Config


def _get_api_key():
    api_key = (Config.GEMINI_API_KEY or "").strip()
    if not api_key:
        raise RuntimeError(
            "Gemini API key is not configured. Set GEMINI_API_KEY in the environment."
        )
    return api_key


def analyze_crop_disease(image_path):
    """Analyze crop image using Gemini AI."""

    api_key = _get_api_key()
    genai.configure(api_key=api_key)

    prompt = """
You are an expert agricultural scientist.

Analyze the uploaded crop image carefully.

Return ONLY valid JSON.

{
    "crop_name":"",
    "disease_name":"",
    "confidence":"",
    "severity":"",
    "symptoms":[],
    "possible_causes":[],
    "prevention":[],
    "treatment":[],
    "fertilizer_recommendation":"",
    "watering_advice":"",
    "additional_notes":""
}

Rules:
1. Return ONLY valid JSON.
2. No markdown.
3. Confidence: High, Medium or Low.
4. Severity: Healthy, Mild, Moderate or Severe.
5. Each list must contain 3-5 points.
"""

    try:
        with Image.open(image_path) as img:
            img.verify()

        model = genai.GenerativeModel("gemini-2.5-flash")

        mime_type = mimetypes.guess_type(image_path)[0] or "image/png"

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        response = model.generate_content(
            [
                prompt,
                {
                    "mime_type": mime_type,
                    "data": image_bytes,
                },
            ]
        )

        result_text = response.text.strip()

        if result_text.startswith("```"):
            result_text = (
                result_text.replace("```json", "")
                .replace("```", "")
                .strip()
            )

        return json.loads(result_text)

    except json.JSONDecodeError:
        return {
            "crop_name": "Unknown",
            "disease_name": "Unable to Detect",
            "confidence": "Low",
            "severity": "Unknown",
            "symptoms": [],
            "possible_causes": [],
            "prevention": [],
            "treatment": [],
            "fertilizer_recommendation": "",
            "watering_advice": "",
            "additional_notes": "Gemini returned invalid JSON."
        }

    except Exception as e:
        return {
            "crop_name": "Unknown",
            "disease_name": "Error",
            "confidence": "Low",
            "severity": "Unknown",
            "symptoms": [],
            "possible_causes": [],
            "prevention": [],
            "treatment": [],
            "fertilizer_recommendation": "",
            "watering_advice": "",
            "additional_notes": str(e)
        }