import os
import sqlite3
import json

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "treatments.db")

def init_treatment_db():
    """Initializes the treatments table in the SQLite database and seeds it if empty."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create treatments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_name TEXT NOT NULL,
            disease_name TEXT NOT NULL,
            disease_type TEXT,
            organic_treatment_json TEXT,
            chemical_treatment_name TEXT,
            active_ingredient TEXT,
            purpose TEXT,
            example_brand_names TEXT,
            application_method TEXT,
            mixing_quantity TEXT,
            water_quantity TEXT,
            spray_tank_size TEXT,
            mixing_steps_json TEXT,
            spray_timing TEXT,
            spray_interval TEXT,
            number_of_applications INTEGER,
            where_to_spray_json TEXT,
            precautions_json TEXT,
            ppe_required TEXT,
            waiting_period_before_harvest TEXT,
            cost_estimate_medicine REAL,
            cost_estimate_labour REAL,
            cost_estimate_total REAL,
            alternative_organic_solutions TEXT,
            government_advisory_source TEXT,
            last_updated_date TEXT
        )
    """)
    
    # Check if we already have records
    cursor.execute("SELECT COUNT(*) FROM treatments")
    count = cursor.fetchone()[0]
    
    if count < 11:
        # Clear existing data if incomplete to force re-seeding
        cursor.execute("DELETE FROM treatments")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='treatments'")
        conn.commit()

        # Seed treatment data for 11 crop-disease combinations
        seed_data = [
            # 1. Tomato Late Blight
            (
                "Tomato",
                "Late Blight",
                "Fungal",
                json.dumps([
                    "Remove infected leaves and stems.",
                    "Dispose infected leaves away from the field.",
                    "Improve air circulation and spacing.",
                    "Apply copper-based organic biofungicide.",
                    "Inspect plants every 3 days for spread."
                ]),
                "Mancozeb 75% WP",
                "Mancozeb",
                "Inhibit fungal spore germination",
                "Dithane M-45, Indofil M-45",
                "Foliar Spray",
                "30 g",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Fill tank halfway with clean water.",
                    "Add 30g of Mancozeb powder.",
                    "Mix thoroughly until dissolved.",
                    "Fill remaining water up to 15L.",
                    "Shake well before spraying."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "7 Days",
                3,
                json.dumps([
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem",
                    "Around infected area"
                ]),
                json.dumps([
                    "Do not overuse chemical fungicide.",
                    "Do not mix with calcium-based compounds.",
                    "Do not spray before rainfall.",
                    "Do not exceed recommended dosage."
                ]),
                "Mask, Gloves, Long sleeves",
                "14 Days",
                250.0,
                150.0,
                400.0,
                "Neem oil spray, Baking soda solution",
                "Indian Council of Agricultural Research (ICAR) Advisory No. 2024-03",
                "2026-07-12"
            ),
            # 2. Tomato Early Blight
            (
                "Tomato",
                "Early Blight",
                "Fungal",
                json.dumps([
                    "Prune lower leaves to prevent splash infection.",
                    "Dispose infected leaves away from the field.",
                    "Apply organic mulch around the base.",
                    "Spray copper fungicide or compost tea.",
                    "Monitor plants regularly for new spots."
                ]),
                "Chlorothalonil 75% WP",
                "Chlorothalonil",
                "Preventive and curative fungal cell disruption",
                "Daconil 2787, Kavach",
                "Foliar Spray",
                "40 g",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Fill tank halfway with clean water.",
                    "Add 40g of Chlorothalonil.",
                    "Agitate the mixture thoroughly.",
                    "Top up with clean water to 15L.",
                    "Shake well before application."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "10 Days",
                4,
                json.dumps([
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem"
                ]),
                json.dumps([
                    "Avoid inhalation of spray mist.",
                    "Do not mix with horticultural oils.",
                    "Do not spray during peak sun.",
                    "Adhere strictly to label directions."
                ]),
                "Mask, Gloves, Long sleeves",
                "7 Days",
                300.0,
                150.0,
                450.0,
                "Bordeaux mixture, Bacillus subtilis bio-pesticide",
                "USDA Agricultural Research Service (ARS) Early Blight Guide",
                "2026-07-12"
            ),
            # 3. Rice Blast
            (
                "Rice",
                "Blast",
                "Fungal",
                json.dumps([
                    "Destroy diseased crop residues completely.",
                    "Avoid excessive nitrogen fertilizer application.",
                    "Maintain water level in the field.",
                    "Apply bio-control agents like Pseudomonas fluorescens.",
                    "Clean farm tools after field work."
                ]),
                "Tricyclazole 75% WP",
                "Tricyclazole",
                "Systemic fungicide to prevent melanin biosynthesis in fungus",
                "Beam, Blastin, Sivic",
                "Foliar Spray",
                "15 g",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Pour 7-8 litres of clean water in the tank.",
                    "Add 15g of Tricyclazole powder.",
                    "Stir well to form a uniform suspension.",
                    "Add remaining water to reach 15L.",
                    "Shake tank before spraying."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "12 Days",
                2,
                json.dumps([
                    "Upper surface of leaves",
                    "Stem",
                    "Around infected area"
                ]),
                json.dumps([
                    "Do not apply when temperature exceeds 35°C.",
                    "Do not mix with alkaline chemicals.",
                    "Wait for dew to dry before morning spray.",
                    "Use correct spray nozzle size."
                ]),
                "Mask, Gloves, Long sleeves",
                "30 Days",
                350.0,
                200.0,
                550.0,
                "Trichoderma-based spray, Garlic extract",
                "International Rice Research Institute (IRRI) Pest Advisory",
                "2026-07-12"
            ),
            # 4. Rice Brown Spot
            (
                "Rice",
                "Brown Spot",
                "Fungal",
                json.dumps([
                    "Ensure balanced soil nutrition (NPK + Silicon).",
                    "Remove weed hosts around the paddy.",
                    "Improve soil drainage and aeration.",
                    "Apply organic farmyard manure.",
                    "Seed treatment with hot water or bioagents."
                ]),
                "Propiconazole 25% EC",
                "Propiconazole",
                "Curative systemic ergosterol biosynthesis inhibitor",
                "Tilt, Radar, Result",
                "Foliar Spray",
                "20 ml",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Fill spray tank with 7 litres of clean water.",
                    "Add 20ml of Propiconazole liquid concentrate.",
                    "Mix thoroughly until emulsified.",
                    "Add water to complete 15L volume.",
                    "Shake well to ensure even distribution."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "14 Days",
                2,
                json.dumps([
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem"
                ]),
                json.dumps([
                    "Toxic to aquatic life; avoid runoff.",
                    "Do not spray near water bodies directly.",
                    "Avoid spraying if rain is expected in 3 hours.",
                    "Do not exceed maximum recommended concentration."
                ]),
                "Mask, Gloves, Long sleeves",
                "28 Days",
                280.0,
                200.0,
                480.0,
                "Neem seed kernel extract, Pseudomonads spray",
                "State Department of Agriculture Paddy Management Circular",
                "2026-07-12"
            ),
            # 5. Potato Late Blight
            (
                "Potato",
                "Late Blight",
                "Fungal",
                json.dumps([
                    "Prune and burn infected potato vines.",
                    "Avoid overhead irrigation to keep foliage dry.",
                    "Harvest only on sunny, dry days.",
                    "Apply sulfur-based biofungicide spray.",
                    "Ensure good soil hilling to protect tubers."
                ]),
                "Metalaxyl 8% + Mancozeb 64% WP",
                "Metalaxyl and Mancozeb",
                "Dual-action systemic and contact protection",
                "Ridomil Gold, Krilaxyl",
                "Foliar Spray",
                "40 g",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Fill half spray tank with fresh water.",
                    "Weigh and add 40g of Ridomil Gold powder.",
                    "Agitate until fully dispersed.",
                    "Top up tank to 15L line.",
                    "Shake thoroughly before spraying."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "7 Days",
                3,
                json.dumps([
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem",
                    "Around infected area"
                ]),
                json.dumps([
                    "Wear respirator mask during mixing.",
                    "Do not spray on wet leaves.",
                    "Avoid drift to non-target crops.",
                    "Do not spray during high winds."
                ]),
                "Mask, Gloves, Long sleeves",
                "14 Days",
                450.0,
                150.0,
                600.0,
                "Copper octanoate spray, Horsetail herb decoction",
                "CIP (International Potato Center) Late Blight Alert System",
                "2026-07-12"
            ),
            # 6. Wheat Rust
            (
                "Wheat",
                "Rust",
                "Fungal",
                json.dumps([
                    "Plant rust-resistant wheat varieties.",
                    "Eradicate barberry bushes (alternate hosts).",
                    "Avoid excessive dense planting density.",
                    "Apply organic bio-agent sprays.",
                    "Harvest early if infection is severe."
                ]),
                "Tebuconazole 250 EC",
                "Tebuconazole",
                "Broad-spectrum systemic triazole fungicide",
                "Folicur, Orius",
                "Foliar Spray",
                "15 ml",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Fill tank with 8 litres of clean water.",
                    "Measure and add 15ml of Folicur.",
                    "Stir the mixture gently to blend.",
                    "Fill the tank completely with water to 15L.",
                    "Shake tank vigorously before use."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "14 Days",
                2,
                json.dumps([
                    "Upper surface of leaves",
                    "Stem"
                ]),
                json.dumps([
                    "Avoid skin contact; wash immediately if exposed.",
                    "Keep livestock away from treated fields for 14 days.",
                    "Do not mix with unknown herbicides.",
                    "Do not apply if wind speed is above 10 km/h."
                ]),
                "Mask, Gloves, Long sleeves",
                "30 Days",
                500.0,
                250.0,
                750.0,
                "Fermented nettle liquid, Sulfur dust",
                "FAO Global Rust Reference Center Advisory",
                "2026-07-12"
            ),
            # 7. Maize Leaf Blight
            (
                "Maize",
                "Leaf Blight",
                "Fungal",
                json.dumps([
                    "Rotate crop with non-cereal crops.",
                    "Incorporate old crop residue deep into soil.",
                    "Ensure proper nitrogen and potassium balance.",
                    "Apply biological control (Bacillus subtilis).",
                    "Maintain optimal plant population density."
                ]),
                "Azoxystrobin 18.2% + Difenoconazole 11.4% SC",
                "Azoxystrobin and Difenoconazole",
                "Preventative and curative systemic action",
                "Amistar Top, Custodia",
                "Foliar Spray",
                "15 ml",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Pour 7-8 litres of clean water into the sprayer.",
                    "Add 15ml of Amistar Top suspension concentrate.",
                    "Stir thoroughly using a clean stick.",
                    "Fill the remaining volume with water to 15L.",
                    "Lock the sprayer and shake well."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "10 Days",
                2,
                json.dumps([
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Around infected area"
                ]),
                json.dumps([
                    "Toxic to apple trees; avoid spray drift to orchards.",
                    "Wash equipment immediately after application.",
                    "Do not spray under bright, hot sun.",
                    "Do not mix with oils or wetting agents."
                ]),
                "Mask, Gloves, Long sleeves",
                "21 Days",
                600.0,
                250.0,
                850.0,
                "Compost extract, Neem seed powder solution",
                "CIMMYT Maize Diseases Field Guide",
                "2026-07-12"
            ),
            # 8. Apple Scab
            (
                "Apple",
                "Scab",
                "Fungal",
                json.dumps([
                    "Rake and destroy fallen leaves in autumn.",
                    "Prune orchard trees to improve air flow.",
                    "Apply lime-sulfur spray in early spring.",
                    "Spray compost tea to increase foliar microbes.",
                    "Use scab-resistant cultivars."
                ]),
                "Captan 50% WP",
                "Captan",
                "Multi-site protective organic fungicide",
                "Captec, Orthocide",
                "Foliar Spray",
                "40 g",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Fill spray tank half full with clean water.",
                    "Add 40g of Captan wettable powder.",
                    "Mix thoroughly until free of lumps.",
                    "Add remaining water to make 15L.",
                    "Keep mixture agitated during spray."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "7 Days",
                5,
                json.dumps([
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Stem",
                    "Around infected area"
                ]),
                json.dumps([
                    "Do not apply within 10 days of oil sprays.",
                    "Wear protective eye goggles to avoid irritation.",
                    "Avoid spray drift to surrounding areas.",
                    "Do not contaminate water sources."
                ]),
                "Mask, Gloves, Long sleeves",
                "14 Days",
                400.0,
                300.0,
                700.0,
                "Potassium bicarbonate spray, Horsetail extract",
                "Agricultural Extension Service Fruit Spray Guide",
                "2026-07-12"
            ),
            # 9. Tomato Blossom End Rot
            (
                "Tomato",
                "Blossom End Rot",
                "Physiological",
                json.dumps([
                    "Remove affected fruits to redirect calcium to healthy ones.",
                    "Ensure a highly consistent soil watering schedule.",
                    "Apply organic straw mulch to retain soil moisture.",
                    "Avoid high-nitrogen fertilizers during fruiting.",
                    "Incorporate gypsum or bone meal in soil next season."
                ]),
                "Calcium Chloride 30% SL",
                "Calcium Chloride",
                "Address localized calcium deficiency in fruit cells",
                "Rot-Stop, Cal-Max",
                "Foliar Spray",
                "45 ml",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Fill sprayer halfway with clean water.",
                    "Add 45ml of Rot-Stop concentrate.",
                    "Mix thoroughly until blended.",
                    "Fill remaining tank with water to 15L.",
                    "Shake tank well before spraying."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "7 Days",
                3,
                json.dumps([
                    "Upper surface of leaves",
                    "Lower surface of leaves",
                    "Around infected area"
                ]),
                json.dumps([
                    "Do not apply in temperatures exceeding 30°C to avoid foliage burn.",
                    "Do not exceed recommended dilution rate.",
                    "Ensure thorough coverage of developing green fruits.",
                    "Keep chemical away from children."
                ]),
                "Mask, Gloves, Long sleeves",
                "0 Days",
                150.0,
                100.0,
                250.0,
                "Lime water spray, Fermented eggshell tea",
                "Cornell Cooperative Extension Vegetable Production Guide",
                "2026-07-12"
            ),
            # 10. Potato Common Scab
            (
                "Potato",
                "Common Scab",
                "Bacterial",
                json.dumps([
                    "Maintain soil pH below 5.2 using soil sulfur.",
                    "Ensure high soil moisture during tuber initiation.",
                    "Rotate crops with alfalfa, rye, or clover.",
                    "Avoid using fresh animal manure.",
                    "Plant scab-resistant cultivars."
                ]),
                "Streptomycin Sulfate 9% WP",
                "Streptomycin",
                "Control Streptomyces scabies bacteria in soil",
                "Agrimycin-100, Streptomax",
                "Soil Drench",
                "15 g",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Fill tank with 8 litres of clean water.",
                    "Add 15g of Agrimycin powder.",
                    "Stir thoroughly until completely dissolved.",
                    "Top up tank with clean water to 15L.",
                    "Agitate sprayer before application."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "14 Days",
                2,
                json.dumps([
                    "Stem",
                    "Around infected area"
                ]),
                json.dumps([
                    "Do not apply within 21 days of harvest.",
                    "Avoid inhalation of wettable powder dust.",
                    "Do not use on waterlogged soils.",
                    "Do not exceed specified application limit."
                ]),
                "Mask, Gloves, Long sleeves",
                "21 Days",
                380.0,
                150.0,
                530.0,
                "Vinegar soil acidifier, Bio-shield bacillus drench",
                "USDA Agricultural Extension Potato Management Circular",
                "2026-07-12"
            ),
            # 11. Corn Ear Rot
            (
                "Corn",
                "Ear Rot",
                "Fungal",
                json.dumps([
                    "Harvest corn early once grain moisture drops below 25%.",
                    "Dry harvested corn grains rapidly below 15% moisture.",
                    "Clean and sanitize grain storage bins.",
                    "Control ear-damaging insects like corn earworm.",
                    "Deep plow residues after fall harvest."
                ]),
                "Propiconazole 25% EC",
                "Propiconazole",
                "Inhibit fungal growth and aflatoxin development",
                "Tilt, Radar",
                "Foliar Spray",
                "20 ml",
                "15 Litres",
                "15 L",
                json.dumps([
                    "Add 7-8 litres of clean water to the sprayer tank.",
                    "Pour in 20ml of Tilt liquid concentrate.",
                    "Stir well to emulsify the solution.",
                    "Fill the remaining tank up to 15L.",
                    "Shake sprayer thoroughly before use."
                ]),
                "Morning (6 AM - 9 AM) or Evening (4 PM - 6 PM)",
                "10 Days",
                2,
                json.dumps([
                    "Upper surface of leaves",
                    "Around infected area"
                ]),
                json.dumps([
                    "Wear safety goggles during mixing to avoid eye damage.",
                    "Do not apply within 30 days of harvest.",
                    "Do not graze livestock on treated crop residues.",
                    "Highly toxic to fish; avoid spray drift to ponds."
                ]),
                "Mask, Gloves, Long sleeves",
                "30 Days",
                320.0,
                200.0,
                520.0,
                "Essential oil (Thyme/Cinnamon) grain sprays, Garlic water",
                "Iowa State University Crop Extension Ear Rot Guide",
                "2026-07-12"
            )
        ]
        
        cursor.executemany("""
            INSERT INTO treatments (
                crop_name, disease_name, disease_type, organic_treatment_json,
                chemical_treatment_name, active_ingredient, purpose, example_brand_names,
                application_method, mixing_quantity, water_quantity, spray_tank_size,
                mixing_steps_json, spray_timing, spray_interval, number_of_applications,
                where_to_spray_json, precautions_json, ppe_required, waiting_period_before_harvest,
                cost_estimate_medicine, cost_estimate_labour, cost_estimate_total,
                alternative_organic_solutions, government_advisory_source, last_updated_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_data)
        
        conn.commit()
    
    conn.close()

def get_treatment_guidance(crop_name, disease_name):
    """Retrieves verified treatment guidance using case-insensitive fuzzy matching."""
    if not crop_name or not disease_name:
        return None
        
    crop = crop_name.lower().strip()
    disease = disease_name.lower().strip()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM treatments")
    rows = cursor.fetchall()
    conn.close()
    
    # Simple substring containment matching
    for row in rows:
        db_crop = row["crop_name"].lower().strip()
        db_disease = row["disease_name"].lower().strip()
        
        # Match crop: also handle Corn and Maize synonyms
        is_maize_corn_match = ("maize" in crop or "corn" in crop) and ("maize" in db_crop or "corn" in db_crop)
        crop_match = (db_crop in crop) or (crop in db_crop) or is_maize_corn_match
        
        # Match disease
        disease_match = (db_disease in disease) or (disease in db_disease)
        
        if crop_match and disease_match:
            res = dict(row)
            # Safely parse JSON strings to python lists
            try:
                res["organic_treatment"] = json.loads(res["organic_treatment_json"])
            except Exception:
                res["organic_treatment"] = []
                
            try:
                res["mixing_steps"] = json.loads(res["mixing_steps_json"])
            except Exception:
                res["mixing_steps"] = []
                
            try:
                res["where_to_spray"] = json.loads(res["where_to_spray_json"])
            except Exception:
                res["where_to_spray"] = []
                
            try:
                res["precautions"] = json.loads(res["precautions_json"])
            except Exception:
                res["precautions"] = []
                
            return res
            
    return None
