import base64
import json
import mimetypes
from PIL import Image
import requests

from config import Config


def _get_api_key():
    api_key = (Config.GEMINI_API_KEY or "").strip()
    if not api_key:
        raise RuntimeError(
            "Gemini API key is not configured. Set GEMINI_API_KEY in the environment."
        )

    return api_key


def _build_payload(prompt, image_path):
    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/png"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        }
                    },
                ],
            }
        ]
    }


def analyze_crop_disease(image_path):
    """Analyze a crop image using Gemini AI and return structured JSON."""

    api_key = _get_api_key()

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
1. Return ONLY JSON.
2. Do not use markdown.
3. Confidence should be High, Medium, or Low.
4. Severity should be Mild, Moderate, Severe, or Healthy.
5. Symptoms, causes, prevention, and treatment should each contain 3 to 5 points.
6. If the crop is healthy:
   - disease_name = "Healthy"
   - severity = "Healthy"
"""

    try:
        with Image.open(image_path) as image:
            image.verify()

        payload = _build_payload(prompt, image_path)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
           f"models/gemini-1.5-flash:generateContent?key={api_key}"
        )

        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise RuntimeError(data["error"].get("message", "Gemini API error"))

        result_text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            result_text = " ".join(
                part.get("text", "") for part in parts if part.get("text")
            ).strip()

        if not result_text:
            raise ValueError("Gemini returned an empty response.")

        if result_text.startswith("```"):
            result_text = (
                result_text
                .replace("```json", "")
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
            "additional_notes": "Gemini returned an invalid response."
        }

    except Exception as e:

        error_message = str(e)
        if "401" in error_message or "Unauthorized" in error_message:
            error_message = (
                "Gemini authentication failed. Please replace the API key in the .env file "
                "with a valid Google AI Studio API key."
            )

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
            "additional_notes": error_message
        }