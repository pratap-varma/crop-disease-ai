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
    "is_clear": true,
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
6. First, assess the image quality. If the image is blurry, out of focus, has improper lighting, does not clearly show a crop/leaf/plant, or is otherwise of poor clarity, set "is_clear" to false, "crop_name" to "Unknown", "disease_name" to "Improper Image", and write a request in "additional_notes" asking the user to upload a clear, high-quality, focused close-up image of the affected crop leaf. Leave all other fields empty.
"""

    try:
        with Image.open(image_path) as img:
            img.verify()

        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            tools=[genai.protos.Tool(google_search={})]
        )

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

        res_json = json.loads(result_text)
        if "is_clear" not in res_json:
            res_json["is_clear"] = True
        return res_json

    except json.JSONDecodeError:
        return {
            "is_clear": True,
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
            "is_clear": True,
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


def generate_treatment_guidance_ai(crop_name, disease_name):
    """Generates complete treatment guidance for a crop-disease combination using Gemini."""
    try:
        api_key = _get_api_key()
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Gemini API key setup failed: {e}")
        return None
    
    prompt = f"""
You are a senior agronomist and crop protection scientist.
Generate a comprehensive, scientifically-accurate agricultural treatment plan for the following:
Crop: {crop_name}
Disease: {disease_name}

Return ONLY valid JSON with this exact structure:
{{
    "disease_type": "Fungal/Bacterial/Viral/Insect/Nutrient Deficiency/Physiological",
    "organic_treatment": ["Step 1...", "Step 2..."],
    "alternative_organic_solutions": "Comma-separated list of organic sprays or remedies",
    "chemical_treatment_name": "Standard chemical pesticide/fungicide name with formulation (e.g. Propiconazole 25% EC)",
    "active_ingredient": "Chemical active ingredient name",
    "purpose": "Brief description of how it works",
    "example_brand_names": "Comma-separated list of common commercial brands",
    "mixing_quantity": "Dosage value per 15L of water (e.g. '20 ml', '30 g')",
    "water_quantity": "15 Litres",
    "spray_tank_size": "15 L",
    "mixing_steps": ["Step 1...", "Step 2..."],
    "application_method": "Foliar Spray / Soil Drench / Seed Treatment",
    "where_to_spray": ["Upper surface of leaves", "Lower surface of leaves", "Stem", "Around infected area"],
    "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
    "spray_interval": "e.g. '10 Days', '7 Days'",
    "number_of_applications": 2,
    "precautions": ["Precaution 1...", "Precaution 2..."],
    "ppe_required": "Comma-separated list of safety gear (e.g. 'Mask, Gloves, Goggles')",
    "waiting_period_before_harvest": "e.g. '30 Days', '14 Days'",
    "cost_estimate_medicine": 300.0,
    "cost_estimate_labour": 200.0,
    "cost_estimate_total": 500.0,
    "government_advisory_source": "State University Extension Advisory",
    "country": "India",
    "state_or_region": "All"
}}

Rules:
1. Return ONLY valid JSON.
2. The mixing steps must contain 3-5 clear instructions.
3. Every field must be populated with realistic, standard values.
"""
    try:
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            tools=[genai.protos.Tool(google_search={})]
        )
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        if result_text.startswith("```"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(result_text)
        data["crop_name"] = crop_name
        data["disease_name"] = disease_name
        data["verified"] = 1
        data["disabled"] = 0
        from datetime import datetime
        data["last_updated_date"] = datetime.utcnow().strftime("%Y-%m-%d")
        return data
    except Exception as e:
        print(f"Failed to generate treatment guidance via AI: {e}")
        return None