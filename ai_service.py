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


def analyze_crop_disease(image_path, treatment_preference="pesticides", language="en"):
    """Analyze crop image using Gemini AI."""

    api_key = _get_api_key()
    genai.configure(api_key=api_key)

    lang_map = {
        "en": "English", "te": "Telugu", "hi": "Hindi", "ta": "Tamil",
        "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi", "bn": "Bengali",
        "gu": "Gujarati", "pa": "Punjabi", "or": "Odia"
    }
    lang_name = lang_map.get(language, "English")

    if treatment_preference == "organic":
        preference_instruction = "The user prefers ORGANIC treatments. The suggested 'treatment' list, advice, and recommendations MUST be 100% organic, biological, natural, and cultural. DO NOT suggest, name, or mention any synthetic chemicals, medicines, pesticides, fungicides, or commercial chemical sprays."
    else:
        preference_instruction = "The user prefers PESTICIDE/CHEMICAL treatments. The suggested 'treatment' list, advice, and recommendations MUST focus completely on chemical pesticides, fungicides, active ingredients, and synthetic formulations. DO NOT suggest, name, or mention any organic solutions, home remedies, plant extracts (like neem oil), or natural cultural methods."

    prompt = f"""
You are an expert agricultural scientist.

Analyze the uploaded crop image carefully.
{preference_instruction}

IMPORTANT LANGUAGE & TRANSLATION DIRECTIVE:
You MUST generate the report values in the language: {lang_name}.
Specifically, translate the values of these fields into {lang_name}:
- crop_name (Where appropriate, display: Local-language name + Scientific/English name. Example: 'మొక్కజొన్న (Corn (Maize))')
- disease_name (Where appropriate, display: Local-language name + Scientific/English name. Example: 'ఆకు మచ్చ తెగులు (Leaf Spot)')
- symptoms (list of 3-5 points in {lang_name})
- possible_causes (list of 3-5 points in {lang_name})
- prevention (list of 3-5 points in {lang_name})
- treatment (list of 3-5 points in {lang_name})
- fertilizer_recommendation (in {lang_name})
- watering_advice (in {lang_name})
- additional_notes (in {lang_name})

Keep the JSON keys exactly in English as defined below.
Do NOT translate enum values for "confidence" (must be "High", "Medium", or "Low" in English) and "severity" (must be "Healthy", "Mild", "Moderate", or "Severe" in English).

AI SAFETY & QUANTITY PRESERVATION RULES:
1. Do NOT translate or modify any medicine/chemical names, active ingredients, formulations, application rates, numbers, quantities, units, or waiting periods incorrectly.
2. Keep all numerical values and units (e.g., '10 ml', '5 litres', '15 days', '25°C', '78%') exactly as they are in their standard forms. The surrounding text descriptions can be in {lang_name}, but keep the values like '10 ml' or '5 kg' exactly as is.

Return ONLY valid JSON.

{{
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
}}

Rules:
1. Return ONLY valid JSON.
2. No markdown.
3. Confidence: High, Medium or Low.
4. Severity: Healthy, Mild, Moderate or Severe.
5. Each list must contain 3-5 points.
6. First, assess the image quality. If the image is blurry, out of focus, has improper lighting, does not clearly show a crop/leaf/plant, or is otherwise of poor clarity, set "is_clear" to false, "crop_name" to "Unknown", "disease_name" to "Improper Image", and write a request in "additional_notes" asking the user to upload a clear, high-quality, focused close-up image of the affected crop leaf in {lang_name}. Leave all other fields empty.
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
            ],
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
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


def generate_treatment_guidance_ai(crop_name, disease_name, language="en"):
    """Generates complete treatment guidance for a crop-disease combination using Gemini."""
    try:
        api_key = _get_api_key()
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Gemini API key setup failed: {e}")
        return None
        
    lang_map = {
        "en": "English", "te": "Telugu", "hi": "Hindi", "ta": "Tamil",
        "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi", "bn": "Bengali",
        "gu": "Gujarati", "pa": "Punjabi", "or": "Odia"
    }
    lang_name = lang_map.get(language, "English")
    
    prompt = f"""
You are a senior agronomist and crop protection scientist.
Generate a comprehensive, scientifically-accurate agricultural treatment plan for the following:
Crop: {crop_name}
Disease: {disease_name}

IMPORTANT LANGUAGE REQUIREMENT:
You MUST generate the description strings and list values of the JSON in: {lang_name}.
Specifically:
- organic_treatment (list of steps in {lang_name})
- alternative_organic_solutions (in {lang_name})
- purpose (in {lang_name})
- mixing_steps (list of steps in {lang_name})
- application_method (in {lang_name})
- where_to_spray (list of areas in {lang_name})
- spray_timing (in {lang_name})
- precautions (list of precautions in {lang_name})

Keep the JSON keys exactly in English as defined below.

AI SAFETY & QUANTITY PRESERVATION RULES:
1. Do NOT translate or modify any medicine/chemical names, active ingredients, brand names, formulations, numbers, quantities, units, application rates, spray intervals, costs, or waiting periods incorrectly.
2. Keep all chemical active ingredients (e.g. 'Propiconazole 25% EC'), brand name examples (e.g. 'Tilt'), mixing quantities (e.g. '20 ml', '30 g'), water quantities (e.g. '15 Litres'), tank sizes (e.g. '15 L'), spray intervals (e.g. '10 Days', '7 Days'), and harvest waiting periods (e.g. '30 Days', '14 Days') exactly as they are in English/Standard forms.
3. Keep safety gear / PPE (e.g. 'Mask, Gloves, Goggles') and numeric costs (e.g. 300.0) in standard English.

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
2. The treatment plan MUST tell completely to the user WHAT TO DO (exact remedies/medicines), HOW TO DO IT (dilution steps, mixing instructions, and application methods), and WHEN TO DO IT (best time of day, weather conditions, spray intervals, and application limits).
3. The mixing steps must contain 3-5 clear instructions.
4. Every field must be populated with realistic, standard values.
"""
    try:
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            tools=[genai.protos.Tool(google_search={})]
        )
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
        )
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


def translate_treatment_info(treatment_info, language="en"):
    """Translates only description texts inside verified treatment_info dictionary into target language using Gemini."""
    if not treatment_info or language == "en":
        return treatment_info
        
    try:
        api_key = _get_api_key()
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Gemini API key setup failed for translation: {e}")
        return treatment_info
    
    lang_map = {
        "en": "English", "te": "Telugu", "hi": "Hindi", "ta": "Tamil",
        "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi", "bn": "Bengali",
        "gu": "Gujarati", "pa": "Punjabi", "or": "Odia"
    }
    lang_name = lang_map.get(language, "English")
    
    prompt = f"""
You are a translation assistant for a professional agricultural app.
Translate the following treatment guidance dictionary into: {lang_name}.

AI SAFETY & QUANTITY PRESERVATION RULES:
1. Do NOT translate or modify any medicine/chemical names, active ingredients, formulations, numbers, quantities, units, application rates, spray intervals, costs, or waiting periods incorrectly.
2. Keep all numerical values and units (e.g., '10 ml', '5 litres', '15 days', '25°C', '78%', '300.0') exactly as they are in the original English.
3. Keep the keys of the JSON dictionary exactly the same in English.
4. Translate ONLY the descriptive strings and list instructions (like elements inside "organic_treatment", "mixing_steps", "precautions", "application_method", "where_to_spray", "spray_timing", "purpose").

Original JSON to translate:
{json.dumps(treatment_info, default=str)}

Return ONLY valid JSON.
"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
        )
        result_text = response.text.strip()
        if result_text.startswith("```"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        translated_data = json.loads(result_text)
        
        # Merge back to keep fields like id or other non-translatable fields
        for k, v in translated_data.items():
            if k in treatment_info:
                treatment_info[k] = v
                
        return treatment_info
    except Exception as e:
        print(f"Failed to translate treatment info via AI: {e}")
        return treatment_info