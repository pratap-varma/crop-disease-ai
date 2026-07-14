import os
import json

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/treatments.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "treatments.db")
def get_db_client():
    try:
        from firebase_admin import firestore
        return firestore.client()
    except Exception as e:
        print(f"Failed to get Firestore client: {e}")
        return None


def init_treatment_db():
    # If a local SQLite database file exists, clean it up to prevent layout confusion
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
            
    db = get_db_client()
    if not db:
        print("Firestore not initialized yet; seeding postponed.")
        return
        
    try:
        # Check if collection has records
        docs = db.collection("treatments").get()
        if len(docs) > 0:
            print("Firestore treatments collection already has data; skipping seed.")
            return
            
        print("Seeding Firestore treatments collection...")
        # Define seed data array
        seed_items = [
            # 1. Tomato Late Blight
            {
                "crop_name": "Tomato",
                "disease_name": "Late Blight",
                "disease_type": "Fungal",
                "organic_treatment": [
                    "Remove infected leaves",
                    "Prune and destroy infected foliage.",
                    "Ensure adequate plant spacing for ventilation.",
                    "Apply copper-based organic fungicides."
                ],
                "chemical_treatment_name": "Mancozeb 75% WP",
                "active_ingredient": "Mancozeb",
                "purpose": "Broad-spectrum contact fungicide to inhibit spore germination",
                "example_brand_names": "Dithane M-45, Indofil M-45",
                "application_method": "Foliar Spray",
                "mixing_quantity": "30 g",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Fill the spray tank with 7-8 litres of clean water.",
                    "Weigh 30g of Mancozeb powder and add to the tank.",
                    "Stir the mixture thoroughly to form a uniform suspension.",
                    "Add more water to reach the 15L mark.",
                    "Shake the sprayer well before starting the application."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "7 Days",
                "number_of_applications": 3,
                "where_to_spray": [
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem"
                ],
                "precautions": [
                    "Avoid spraying when rainfall is expected within 3 hours.",
                    "Do not apply when temperatures exceed 35°C.",
                    "Highly toxic to fish; prevent drift to water bodies.",
                    "Always wear PPE including long sleeves and face mask."
                ],
                "ppe_required": "Mask, Gloves, Protective Eyewear",
                "waiting_period_before_harvest": "14 Days",
                "cost_estimate_medicine": 200.0,
                "cost_estimate_labour": 150.0,
                "cost_estimate_total": 350.0,
                "alternative_organic_solutions": "Neem oil spray (1%), Baking soda spray",
                "government_advisory_source": "ICAR Tomato Protection Bulletin",
                "last_updated_date": "2026-07-12"
            },
            # 2. Tomato Early Blight
            {
                "crop_name": "Tomato",
                "disease_name": "Early Blight",
                "disease_type": "Fungal",
                "organic_treatment": [
                    "Apply organic mulch to prevent soil splashing.",
                    "Remove bottom leaves up to 12 inches high.",
                    "Apply bio-fungicides like Bacillus subtilis."
                ],
                "chemical_treatment_name": "Chlorothalonil 75% WP",
                "active_ingredient": "Chlorothalonil",
                "purpose": "Contact fungicide protecting healthy foliage",
                "example_brand_names": "Daconil, Kavach",
                "application_method": "Foliar Spray",
                "mixing_quantity": "25 g",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Fill the spray tank with 7-8 litres of clean water.",
                    "Weigh 25g of Chlorothalonil and add to the tank.",
                    "Stir the mixture thoroughly.",
                    "Fill up the tank to 15L with water.",
                    "Shake thoroughly before spraying."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "10 Days",
                "number_of_applications": 3,
                "where_to_spray": [
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem"
                ],
                "precautions": [
                    "Avoid spraying when rainfall is expected within 3 hours.",
                    "Do not apply when temperatures exceed 35°C.",
                    "Do not exceed maximum recommended concentration.",
                    "Avoid contact with eyes and skin."
                ],
                "ppe_required": "Mask, Gloves, Goggles",
                "waiting_period_before_harvest": "7 Days",
                "cost_estimate_medicine": 220.0,
                "cost_estimate_labour": 150.0,
                "cost_estimate_total": 370.0,
                "alternative_organic_solutions": "Bordeaux mixture, Bacillus subtilis bio-pesticide",
                "government_advisory_source": "USDA Agricultural Research Service (ARS) Early Blight Guide",
                "last_updated_date": "2026-07-12"
            },
            # 3. Rice Blast
            {
                "crop_name": "Rice",
                "disease_name": "Blast",
                "disease_type": "Fungal",
                "organic_treatment": [
                    "Destroy diseased crop residues completely.",
                    "Avoid excessive nitrogen fertilizer application.",
                    "Maintain water level in the field.",
                    "Apply bio-control agents like Pseudomonas fluorescens.",
                    "Clean farm tools after field work."
                ],
                "chemical_treatment_name": "Tricyclazole 75% WP",
                "active_ingredient": "Tricyclazole",
                "purpose": "Systemic fungicide to prevent melanin biosynthesis in fungus",
                "example_brand_names": "Beam, Blastin, Sivic",
                "application_method": "Foliar Spray",
                "mixing_quantity": "15 g",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Pour 7-8 litres of clean water in the tank.",
                    "Add 15g of Tricyclazole powder.",
                    "Stir well to form a uniform suspension.",
                    "Add remaining water to reach 15L.",
                    "Shake tank before spraying."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "12 Days",
                "number_of_applications": 2,
                "where_to_spray": [
                    "Upper surface of leaves",
                    "Stem",
                    "Around infected area"
                ],
                "precautions": [
                    "Do not apply when temperature exceeds 35°C.",
                    "Do not mix with alkaline chemicals.",
                    "Wait for dew to dry before morning spray.",
                    "Use correct spray nozzle size."
                ],
                "ppe_required": "Mask, Gloves, Long sleeves",
                "waiting_period_before_harvest": "30 Days",
                "cost_estimate_medicine": 350.0,
                "cost_estimate_labour": 200.0,
                "cost_estimate_total": 550.0,
                "alternative_organic_solutions": "Trichoderma-based spray, Garlic extract",
                "government_advisory_source": "IRRI Rice Protection Handbook",
                "last_updated_date": "2026-07-12"
            },
            # 4. Rice Brown Spot
            {
                "crop_name": "Rice",
                "disease_name": "Brown Spot",
                "disease_type": "Fungal",
                "organic_treatment": [
                    "Use disease-free certified seeds.",
                    "Ensure proper soil nutrient balance (especially potassium).",
                    "Seed treatment with Agrosan or biofungicide."
                ],
                "chemical_treatment_name": "Edifenphos 50% EC",
                "active_ingredient": "Edifenphos",
                "purpose": "Organophosphorus contact fungicide targeting cell membrane permeability",
                "example_brand_names": "Hinosan",
                "application_method": "Foliar Spray",
                "mixing_quantity": "15 ml",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Fill sprayer tank with 7-8 litres of clean water.",
                    "Add 15ml of Edifenphos liquid concentrate.",
                    "Mix well to emulsify.",
                    "Top up tank to 15L limit.",
                    "Agitate before and during application."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "14 Days",
                "number_of_applications": 2,
                "where_to_spray": [
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem"
                ],
                "precautions": [
                    "Toxic to aquatic life; avoid runoff.",
                    "Do not spray near water bodies directly.",
                    "Avoid spraying if rain is expected in 3 hours.",
                    "Do not exceed maximum recommended concentration."
                ],
                "ppe_required": "Mask, Gloves, Long sleeves",
                "waiting_period_before_harvest": "28 Days",
                "cost_estimate_medicine": 280.0,
                "cost_estimate_labour": 200.0,
                "cost_estimate_total": 480.0,
                "alternative_organic_solutions": "Neem seed kernel extract, Pseudomonads spray",
                "government_advisory_source": "State Department of Agriculture Paddy Management Circular",
                "last_updated_date": "2026-07-12"
            },
            # 5. Potato Late Blight
            {
                "crop_name": "Potato",
                "disease_name": "Late Blight",
                "disease_type": "Fungal",
                "organic_treatment": [
                    "Prune and burn infected potato vines.",
                    "Avoid overhead irrigation to keep foliage dry.",
                    "Harvest only on sunny, dry days.",
                    "Apply sulfur-based biofungicide spray.",
                    "Ensure good soil hilling to protect tubers."
                ],
                "chemical_treatment_name": "Metalaxyl 8% + Mancozeb 64% WP",
                "active_ingredient": "Metalaxyl and Mancozeb",
                "purpose": "Dual-action systemic and contact protection",
                "example_brand_names": "Ridomil Gold, Krilaxyl",
                "application_method": "Foliar Spray",
                "mixing_quantity": "40 g",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Fill half spray tank with fresh water.",
                    "Weigh and add 40g of Ridomil Gold powder.",
                    "Agitate until fully dispersed.",
                    "Top up tank to 15L line.",
                    "Shake thoroughly before spraying."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "7 Days",
                "number_of_applications": 3,
                "where_to_spray": [
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem",
                    "Around infected area"
                ],
                "precautions": [
                    "Wear protective goggles during mixing.",
                    "Ensure zero spray drift to non-target areas.",
                    "Do not apply in high-wind conditions.",
                    "Apply before heavy blight outbreak."
                ],
                "ppe_required": "Mask, Gloves, Protective Eye Goggles",
                "waiting_period_before_harvest": "21 Days",
                "cost_estimate_medicine": 320.0,
                "cost_estimate_labour": 150.0,
                "cost_estimate_total": 470.0,
                "alternative_organic_solutions": "Copper hydroxide solution, Trichoderma drench",
                "government_advisory_source": "CPRI Potato Disease Control Circular",
                "last_updated_date": "2026-07-12"
            },
            # 6. Potato Early Blight
            {
                "crop_name": "Potato",
                "disease_name": "Early Blight",
                "disease_type": "Fungal",
                "organic_treatment": [
                    "Implement a 3-year crop rotation.",
                    "Remove crop debris after harvest.",
                    "Irrigate early in the day."
                ],
                "chemical_treatment_name": "Mancozeb 75% WP",
                "active_ingredient": "Mancozeb",
                "purpose": "Protectant contact fungicide to inhibit fungal respiration",
                "example_brand_names": "Dithane M-45",
                "application_method": "Foliar Spray",
                "mixing_quantity": "30 g",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Fill spray tank with 7-8 litres of clean water.",
                    "Add 30g of Mancozeb powder.",
                    "Stir thoroughly to form uniform suspension.",
                    "Fill remaining tank to 15L.",
                    "Shake before starting."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "10 Days",
                "number_of_applications": 3,
                "where_to_spray": [
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem"
                ],
                "precautions": [
                    "Toxic to aquatic life; avoid runoff.",
                    "Wear protective goggles during mixing.",
                    "Do not apply when temperatures exceed 35°C."
                ],
                "ppe_required": "Mask, Gloves, Goggles",
                "waiting_period_before_harvest": "14 Days",
                "cost_estimate_medicine": 200.0,
                "cost_estimate_labour": 150.0,
                "cost_estimate_total": 350.0,
                "alternative_organic_solutions": "Compost tea spray, Copper sulfate solution",
                "government_advisory_source": "State Agriculture University Potato Extension Bulletin",
                "last_updated_date": "2026-07-12"
            },
            # 7. Potato Common Scab
            {
                "crop_name": "Potato",
                "disease_name": "Common Scab",
                "disease_type": "Bacterial",
                "organic_treatment": [
                    "Maintain high soil moisture during tuber initiation (first 4-6 weeks).",
                    "Maintain soil pH below 5.2 by applying sulfur.",
                    "Use scab-resistant seed cultivars."
                ],
                "chemical_treatment_name": "Streptomycin Sulfate 9% WP",
                "active_ingredient": "Streptomycin and Tetracycline",
                "purpose": "Systemic bactericide to suppress streptomyces growth in soil/tubers",
                "example_brand_names": "Streptocycline",
                "application_method": "Seed Treatment / Soil Drench",
                "mixing_quantity": "6 g",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Dissolve 6g of Streptocycline powder in 1 litre of warm water first.",
                    "Stir until completely dissolved.",
                    "Pour this concentrated solution into the spray tank.",
                    "Add remaining water to make up to 15L.",
                    "Agitate thoroughly."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "14 Days",
                "number_of_applications": 2,
                "where_to_spray": [
                    "Stem",
                    "Around infected area"
                ],
                "precautions": [
                    "Avoid continuous use to prevent antibiotic resistance.",
                    "Wear gloves and mask to avoid breathing spray mist.",
                    "Store in dry and cool place."
                ],
                "ppe_required": "Mask, Gloves, Long sleeves",
                "waiting_period_before_harvest": "45 Days",
                "cost_estimate_medicine": 120.0,
                "cost_estimate_labour": 150.0,
                "cost_estimate_total": 270.0,
                "alternative_organic_solutions": "Green manure application, Bacillus subtilis soil treat",
                "government_advisory_source": "USDA Agricultural Extension Potato Management Circular",
                "last_updated_date": "2026-07-12"
            },
            # 8. Apple Scab
            {
                "crop_name": "Apple",
                "disease_name": "Scab",
                "disease_type": "Fungal",
                "organic_treatment": [
                    "Rake and burn fallen leaves to prevent overwintering spores.",
                    "Prune tree canopy to maximize sunshine penetration.",
                    "Apply sulfur or neem oil sprays at green tip stage."
                ],
                "chemical_treatment_name": "Captan 50% WP",
                "active_ingredient": "Captan",
                "purpose": "Non-systemic contact fungicide to block enzyme activity of fungi",
                "example_brand_names": "Captaf, Capgold",
                "application_method": "Foliar Spray",
                "mixing_quantity": "30 g",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Fill spray tank with 7-8 litres of clean water.",
                    "Add 30g of Captan powder to the water.",
                    "Stir thoroughly to form a uniform slurry.",
                    "Add more water to reach 15L.",
                    "Shake sprayer well before use."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "7 Days",
                "number_of_applications": 5,
                "where_to_spray": [
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem",
                    "Around infected area"
                ],
                "precautions": [
                    "Do not apply within 10 days of oil sprays.",
                    "Wear protective eye goggles to avoid irritation.",
                    "Avoid spray drift to surrounding areas.",
                    "Do not contaminate water sources."
                ],
                "ppe_required": "Mask, Gloves, Long sleeves",
                "waiting_period_before_harvest": "14 Days",
                "cost_estimate_medicine": 400.0,
                "cost_estimate_labour": 300.0,
                "cost_estimate_total": 700.0,
                "alternative_organic_solutions": "Potassium bicarbonate spray, Horsetail extract",
                "government_advisory_source": "Agricultural Extension Service Fruit Spray Guide",
                "last_updated_date": "2026-07-12"
            },
            # 9. Tomato Blossom End Rot
            {
                "crop_name": "Tomato",
                "disease_name": "Blossom End Rot",
                "disease_type": "Physiological",
                "organic_treatment": [
                    "Remove affected fruits to redirect calcium to healthy ones.",
                    "Ensure a highly consistent soil watering schedule.",
                    "Apply organic straw mulch to retain soil moisture.",
                    "Avoid high-nitrogen fertilizers during fruiting.",
                    "Incorporate gypsum or bone meal in soil next season."
                ],
                "chemical_treatment_name": "Calcium Chloride 30% SL",
                "active_ingredient": "Calcium Chloride",
                "purpose": "Direct foliar calcium supplementation to resolve physiological deficiency",
                "example_brand_names": "Cal-Max, Rot-Stop",
                "application_method": "Foliar Spray",
                "mixing_quantity": "45 ml",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Fill spray tank with 10 litres of fresh water.",
                    "Measure and pour 45ml of Calcium Chloride liquid concentrate.",
                    "Stir completely to dilute.",
                    "Top up tank to 15L mark.",
                    "Agitate sprayer well."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "7 Days",
                "number_of_applications": 2,
                "where_to_spray": [
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem"
                ],
                "precautions": [
                    "Do not apply during hot afternoon sun (could cause leaf burn).",
                    "Ensure soil is damp before foliar application.",
                    "Do not mix with phosphorus or sulfur-containing products."
                ],
                "ppe_required": "Mask, Gloves",
                "waiting_period_before_harvest": "0 Days",
                "cost_estimate_medicine": 180.0,
                "cost_estimate_labour": 150.0,
                "cost_estimate_total": 330.0,
                "alternative_organic_solutions": "Foliar eggshell tea spray, Liquid seaweed extract",
                "government_advisory_source": "State University Cooperative Extension Horticulture Guide",
                "last_updated_date": "2026-07-12"
            },
            # 10. Potato Scab
            {
                "crop_name": "Potato",
                "disease_name": "Scab",
                "disease_type": "Bacterial",
                "organic_treatment": [
                    "Maintain high soil moisture during tuber initiation (first 4-6 weeks).",
                    "Maintain soil pH below 5.2 by applying sulfur.",
                    "Use scab-resistant seed cultivars."
                ],
                "chemical_treatment_name": "Streptomycin Sulfate 9% WP",
                "active_ingredient": "Streptomycin and Tetracycline",
                "purpose": "Systemic bactericide to suppress streptomyces growth in soil/tubers",
                "example_brand_names": "Streptocycline",
                "application_method": "Seed Treatment / Soil Drench",
                "mixing_quantity": "6 g",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Dissolve 6g of Streptocycline powder in 1 litre of warm water first.",
                    "Stir until completely dissolved.",
                    "Pour this concentrated solution into the spray tank.",
                    "Add remaining water to make up to 15L.",
                    "Agitate thoroughly."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "14 Days",
                "number_of_applications": 2,
                "where_to_spray": [
                    "Stem",
                    "Around infected area"
                ],
                "precautions": [
                    "Avoid continuous use to prevent antibiotic resistance.",
                    "Wear gloves and mask to avoid breathing spray mist.",
                    "Store in dry and cool place."
                ],
                "ppe_required": "Mask, Gloves, Long sleeves",
                "waiting_period_before_harvest": "45 Days",
                "cost_estimate_medicine": 120.0,
                "cost_estimate_labour": 150.0,
                "cost_estimate_total": 270.0,
                "alternative_organic_solutions": "Vinegar soil acidifier, Bio-shield bacillus drench",
                "government_advisory_source": "USDA Agricultural Extension Potato Management Circular",
                "last_updated_date": "2026-07-12"
            },
            # 11. Corn Ear Rot
            {
                "crop_name": "Corn",
                "disease_name": "Ear Rot",
                "disease_type": "Fungal",
                "organic_treatment": [
                    "Harvest corn early once grain moisture drops below 25%.",
                    "Dry harvested corn grains rapidly below 15% moisture.",
                    "Clean and sanitize grain storage bins.",
                    "Control ear-damaging insects like corn earworm.",
                    "Deep plow residues after fall harvest."
                ],
                "chemical_treatment_name": "Propiconazole 25% EC",
                "active_ingredient": "Propiconazole",
                "purpose": "Inhibit fungal growth and aflatoxin development",
                "example_brand_names": "Tilt, Radar",
                "application_method": "Foliar Spray",
                "mixing_quantity": "20 ml",
                "water_quantity": "15 Litres",
                "spray_tank_size": "15 L",
                "mixing_steps": [
                    "Add 7-8 litres of clean water to the sprayer tank.",
                    "Pour in 20ml of Tilt liquid concentrate.",
                    "Stir well to emulsify the solution.",
                    "Fill the remaining tank up to 15L.",
                    "Shake sprayer thoroughly before use."
                ],
                "spray_timing": "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "spray_interval": "10 Days",
                "number_of_applications": 2,
                "where_to_spray": [
                    "Upper surface of leaves",
                    "Around infected area"
                ],
                "precautions": [
                    "Wear safety goggles during mixing to avoid eye damage.",
                    "Do not apply within 30 days of harvest.",
                    "Do not graze livestock on treated crop residues.",
                    "Highly toxic to fish; avoid spray drift to ponds."
                ],
                "ppe_required": "Mask, Gloves, Long sleeves",
                "waiting_period_before_harvest": "30 Days",
                "cost_estimate_medicine": 320.0,
                "cost_estimate_labour": 200.0,
                "cost_estimate_total": 520.0,
                "alternative_organic_solutions": "Essential oil (Thyme/Cinnamon) grain sprays, Garlic water",
                "government_advisory_source": "Iowa State University Crop Extension Ear Rot Guide",
                "last_updated_date": "2026-07-12"
            }
        ]
        
        for item in seed_items:
            save_treatment_record(item)
            
        print("Firestore treatments seeding completed successfully!")
    except Exception as e:
        print(f"Error during Firestore seeding: {e}")


import re
import math

def parse_dosage(quantity_str):
    if not quantity_str:
        return None
    m = re.match(r"([0-9.]+)\s*([a-zA-Z%]+)", quantity_str.strip())
    if not m:
        return None
    try:
        val = float(m.group(1))
        unit = m.group(2)
        return {"val": val, "unit": unit}
    except Exception:
        return None


def calculate_dosage(land_size, land_unit, tank_capacity, mixing_quantity, base_water_volume_str="15 Litres"):
    if land_size <= 0 or tank_capacity <= 0:
        raise ValueError("Invalid input values")
        
    water_per_unit = 200.0 if land_unit == "acres" else 500.0
    total_water_volume = int(round(land_size * water_per_unit))
    
    total_tanks = int(math.ceil(total_water_volume / tank_capacity))
    
    base_dosage = parse_dosage(mixing_quantity)
    base_water = parse_dosage(base_water_volume_str)
    
    if not base_dosage or not base_water or base_water["val"] <= 0:
        return {
            "total_water_volume": total_water_volume,
            "total_tanks": total_tanks,
            "total_medicine": None,
            "per_tank_medicine": None
        }
        
    concentration = base_dosage["val"] / base_water["val"]
    
    total_med = round(total_water_volume * concentration, 1)
    per_tank_med = round(tank_capacity * concentration, 1)
    
    return {
        "total_water_volume": total_water_volume,
        "total_tanks": total_tanks,
        "total_medicine": f"{total_med} {base_dosage['unit']}",
        "per_tank_medicine": f"{per_tank_med} {base_dosage['unit']}"
    }


def get_all_treatments_raw():
    try:
        db = get_db_client()
        if not db:
            return []
        docs = db.collection("treatments").get()
        res_list = []
        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            
            # Ensure standard fields and formats exist
            for list_field in ["organic_treatment", "mixing_steps", "where_to_spray", "precautions"]:
                raw_val = d.get(list_field)
                if isinstance(raw_val, list):
                    d[list_field] = raw_val
                    d[list_field + "_json"] = json.dumps(raw_val)
                elif isinstance(raw_val, str):
                    try:
                        parsed = json.loads(raw_val)
                        d[list_field] = parsed
                        d[list_field + "_json"] = raw_val
                    except Exception:
                        d[list_field] = []
                        d[list_field + "_json"] = "[]"
                else:
                    d[list_field] = []
                    d[list_field + "_json"] = "[]"
                    
            res_list.append(d)
        return res_list
    except Exception as e:
        print(f"Error fetching raw treatments: {e}")
        return []


def get_treatment_guidance(crop_name, disease_name):
    """Retrieves verified treatment guidance using case-insensitive fuzzy matching."""
    if not crop_name or not disease_name:
        return None
        
    crop = crop_name.lower().strip()
    disease = disease_name.lower().strip()
    
    rows = get_all_treatments_raw()
    
    # Simple substring containment matching
    for row in rows:
        if int(row.get("disabled", 0)) == 1:
            continue
        db_crop = row["crop_name"].lower().strip()
        db_disease = row["disease_name"].lower().strip()
        
        # Match crop: also handle Corn and Maize synonyms
        is_maize_corn_match = ("maize" in crop or "corn" in crop) and ("maize" in db_crop or "corn" in db_crop)
        crop_match = (db_crop in crop) or (crop in db_crop) or is_maize_corn_match
        
        # Match disease
        disease_match = (db_disease in disease) or (disease in db_disease)
        
        if crop_match and disease_match:
            return row
            
    return None


def save_treatment_record(data):
    try:
        db = get_db_client()
        if not db:
            return False, "Database client not available"
            
        doc_id = data.get("id")
        
        # Prepare clean flat structure
        doc_data = {
            "crop_name": data.get("crop_name", "").strip(),
            "disease_name": data.get("disease_name", "").strip(),
            "disease_type": data.get("disease_type", "Fungal").strip(),
            "verified": int(data.get("verified", 1)),
            "disabled": int(data.get("disabled", 0)),
            "alternative_organic_solutions": data.get("alternative_organic_solutions", "").strip(),
            "chemical_treatment_name": data.get("chemical_treatment_name", "").strip(),
            "active_ingredient": data.get("active_ingredient", "").strip(),
            "purpose": data.get("purpose", "").strip(),
            "example_brand_names": data.get("example_brand_names", "").strip(),
            "mixing_quantity": data.get("mixing_quantity", "").strip(),
            "water_quantity": data.get("water_quantity", "").strip(),
            "spray_tank_size": data.get("spray_tank_size", "").strip(),
            "application_method": data.get("application_method", "Foliar Spray").strip(),
            "spray_timing": data.get("spray_timing", "").strip(),
            "spray_interval": data.get("spray_interval", "").strip(),
            "number_of_applications": int(data.get("number_of_applications") or 3),
            "ppe_required": data.get("ppe_required", "").strip(),
            "waiting_period_before_harvest": data.get("waiting_period_before_harvest", "").strip(),
            "cost_estimate_medicine": float(data.get("cost_estimate_medicine") or 0),
            "cost_estimate_labour": float(data.get("cost_estimate_labour") or 0),
            "cost_estimate_total": float(data.get("cost_estimate_total") or 0),
            "government_advisory_source": data.get("government_advisory_source", "").strip(),
            "last_updated_date": data.get("last_updated_date", "").strip(),
            "country": data.get("country", "India").strip(),
            "state_or_region": data.get("state_or_region", "All").strip()
        }
        
        # Convert lists
        for field in ["organic_treatment", "mixing_steps", "where_to_spray", "precautions"]:
            val = data.get(field)
            if val is not None:
                if isinstance(val, list):
                    doc_data[field] = val
                elif isinstance(val, str):
                    try:
                        doc_data[field] = json.loads(val)
                    except Exception:
                        doc_data[field] = [x.strip() for x in val.split(";") if x.strip()]
            else:
                # Try json suffix
                json_val = data.get(field + "_json")
                if json_val:
                    try:
                        doc_data[field] = json.loads(json_val)
                    except Exception:
                        doc_data[field] = []
                else:
                    doc_data[field] = []
                    
        # Update or Insert
        if not doc_id:
            import uuid
            doc_id = f"doc_{uuid.uuid4().hex[:8]}"
            
        db.collection("treatments").document(str(doc_id)).set(doc_data)
        return True, doc_id
    except Exception as e:
        print(f"Failed to save treatment record: {e}")
        return False, str(e)


def delete_treatment_record(treatment_id):
    try:
        db = get_db_client()
        if not db:
            return False
        db.collection("treatments").document(str(treatment_id)).delete()
        return True
    except Exception as e:
        print(f"Failed to delete treatment record {treatment_id}: {e}")
        return False
