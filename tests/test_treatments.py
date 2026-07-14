import unittest
from unittest.mock import patch
import json
import sqlite3
import os

# Import the shared mock database to prevent test configuration leakage
from tests.test_app import mock_db

# Start patchers before importing app so globals resolve cleanly
admin_patcher = patch("firebase_admin.initialize_app")
client_patcher = patch("firebase_admin.firestore.client", return_value=mock_db)
admin_patcher.start()
client_patcher.start()

import app as app_module
from treatment_db import (
    get_treatment_guidance, 
    save_treatment_record, 
    delete_treatment_record,
    get_all_treatments_raw,
    calculate_dosage,
    parse_dosage,
    DB_PATH
)

class TreatmentFeatureTests(unittest.TestCase):
    def setUp(self):
        # Ensure app uses mock db
        app_module.db = mock_db
        mock_db.data["treatments"] = {}
        self.client = app_module.app.test_client()
        # Seed test treatment directly in SQLite
        self.test_data = {
            "crop_name": "Wheat",
            "disease_name": "Rust",
            "disease_type": "Fungal",
            "verified": 1,
            "disabled": 0,
            "organic_treatment_json": json.dumps(["Remove rust leaves", "Destroy debris"]),
            "chemical_treatment_name": "Propiconazole 25% EC",
            "active_ingredient": "Propiconazole",
            "purpose": "Disrupt cell wall",
            "example_brand_names": "Tilt",
            "mixing_quantity": "2 ml",
            "water_quantity": "1 Litre",
            "spray_tank_size": "15 L",
            "mixing_steps_json": json.dumps(["Add 30ml to 15L water", "Stir"]),
            "application_method": "Foliar Spray",
            "where_to_spray_json": json.dumps(["Foliar leaves"]),
            "spray_timing": "Morning",
            "spray_interval": "10 Days",
            "number_of_applications": 2,
            "precautions_json": json.dumps(["Toxic to fish"]),
            "ppe_required": "Mask, Gloves",
            "waiting_period_before_harvest": "30 Days",
            "cost_estimate_medicine": 100.0,
            "cost_estimate_labour": 50.0,
            "cost_estimate_total": 150.0,
            "alternative_organic_solutions": "Neem oil",
            "government_advisory_source": "ICAR 2026",
            "country": "India",
            "state_or_region": "Punjab"
        }
        # Add to DB
        ok, res = save_treatment_record(self.test_data)
        self.assertTrue(ok)
        self.inserted_id = res

    def tearDown(self):
        # Delete inserted test record
        delete_treatment_record(self.inserted_id)

    def test_exact_crop_disease_matching(self):
        guidance = get_treatment_guidance("Wheat", "Rust")
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance["crop_name"], "Wheat")
        self.assertEqual(guidance["disease_name"], "Rust")

    def test_synonym_normalization(self):
        # Corn/Maize synonym matching test
        corn_data = self.test_data.copy()
        corn_data["crop_name"] = "Corn"
        corn_data["disease_name"] = "Smut"
        ok, cid = save_treatment_record(corn_data)
        
        # Verify searching "Maize" matches "Corn"
        guidance = get_treatment_guidance("Maize", "Smut")
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance["crop_name"], "Corn")
        
        # Delete corn record
        delete_treatment_record(cid)

    def test_missing_treatment_records_return_none(self):
        guidance = get_treatment_guidance("NonexistentCrop", "UnknownDisease")
        self.assertIsNone(guidance)

    def test_unverified_record_rejection(self):
        # Seed an unverified record
        unverified_data = self.test_data.copy()
        unverified_data["crop_name"] = "Tomato"
        unverified_data["disease_name"] = "Spider Mites"
        unverified_data["disabled"] = 1 # disabled acts as unverified/disabled rejection
        ok, uid = save_treatment_record(unverified_data)
        
        # Searching should not return disabled record
        guidance = get_treatment_guidance("Tomato", "Spider Mites")
        self.assertIsNone(guidance)
        
        # Clean up
        delete_treatment_record(uid)

    def test_admin_authorization(self):
        # Attempt to access admin routes without logging in
        response = self.client.get("/admin/treatments")
        self.assertEqual(response.status_code, 302) # Redirect to login
        
        response = self.client.post("/admin/treatments/save", data={})
        self.assertEqual(response.status_code, 302)
        
        # Log in as non-admin
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "john_doe"
            
        response = self.client.get("/admin/treatments")
        self.assertEqual(response.status_code, 302) # Still redirect to login/home
        
        # Log in as admin
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "admin"
            
        response = self.client.get("/admin/treatments")
        self.assertEqual(response.status_code, 200)

    def test_dosage_calculations_and_conversions(self):
        # Test 1 acre calculation, knapsack tank 15 L, mix quantity 30 g per 15 L water
        calc = calculate_dosage(
            land_size=1.0,
            land_unit="acres",
            tank_capacity=15,
            mixing_quantity="30 g",
            base_water_volume_str="15 Litres"
        )
        self.assertEqual(calc["total_water_volume"], 200) # 200 L per acre
        self.assertEqual(calc["total_tanks"], 14)        # 200 / 15 ceil
        self.assertEqual(calc["total_medicine"], "400.0 g") # 200 * (30/15)
        self.assertEqual(calc["per_tank_medicine"], "30.0 g")

        # Test 1 hectare calculation, tractor tank 400 L, mix quantity 30 g per 15 L water
        calc = calculate_dosage(
            land_size=1.0,
            land_unit="hectares",
            tank_capacity=400,
            mixing_quantity="30 g",
            base_water_volume_str="15 Litres"
        )
        self.assertEqual(calc["total_water_volume"], 500) # 500 L per hectare
        self.assertEqual(calc["total_tanks"], 2)         # 500 / 400 ceil
        self.assertEqual(calc["total_medicine"], "1000.0 g")
        self.assertEqual(calc["per_tank_medicine"], "800.0 g")

    def test_invalid_input_and_missing_formulation(self):
        # Invalid inputs should throw ValueError
        with self.assertRaises(ValueError):
            calculate_dosage(-1.0, "acres", 15, "30 g")
        with self.assertRaises(ValueError):
            calculate_dosage(1.0, "acres", -15, "30 g")

        # Missing or invalid formulation formats should return None for medicine calculations
        calc = calculate_dosage(1.0, "acres", 15, "invalid dosage")
        self.assertIsNone(calc["total_medicine"])
        self.assertIsNone(calc["per_tank_medicine"])

        # Check unit parser returns None for bad values
        self.assertIsNone(parse_dosage(""))
        self.assertIsNone(parse_dosage("no number here"))

    @patch("ai_service.genai.GenerativeModel")
    @patch("app.analyze_crop_disease")
    def test_predict_route_triggers_ai_generation_on_missing_guidance(self, mock_analyze, mock_model_class):
        from unittest.mock import MagicMock
        # 1. Setup mock disease detection
        mock_analyze.return_value = {
            "crop_name": "Orange",
            "disease_name": "Citrus Canker",
            "confidence": "High",
            "severity": "Mild",
            "symptoms": ["Yellow halos"],
            "possible_causes": ["Bacteria"],
            "prevention": ["Pruning"],
            "treatment": ["Copper spray"],
            "fertilizer_recommendation": "None",
            "watering_advice": "Drip irrigation",
            "additional_notes": "None"
        }

        # 2. Setup mock Gemini response for treatment generation
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "disease_type": "Bacterial",
            "organic_treatment": ["Remove infected twigs"],
            "alternative_organic_solutions": "Neem spray",
            "chemical_treatment_name": "Copper Hydroxide 50% WP",
            "active_ingredient": "Copper Hydroxide",
            "purpose": "Kill bacteria",
            "example_brand_names": "Kocide",
            "mixing_quantity": "25 g",
            "water_quantity": "15 Litres",
            "spray_tank_size": "15 L",
            "mixing_steps": ["Add to tank", "Stir"],
            "application_method": "Foliar Spray",
            "where_to_spray": ["Upper leaves"],
            "spray_timing": "Morning",
            "spray_interval": "7 Days",
            "number_of_applications": 3,
            "precautions": ["Wear gloves"],
            "ppe_required": "Mask, Gloves",
            "waiting_period_before_harvest": "14 Days",
            "cost_estimate_medicine": 150.0,
            "cost_estimate_labour": 100.0,
            "cost_estimate_total": 250.0,
            "government_advisory_source": "Advisory Source",
            "country": "India",
            "state_or_region": "All"
        })
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        # Ensure database is clean of Orange Citrus Canker
        mock_db.data["treatments"] = {}

        # 3. Trigger predict request
        import io
        response = self.client.post(
            "/predict",
            data={"image": (io.BytesIO(b"dummy image data"), "test.jpg")},
            content_type="multipart/form-data"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode("utf-8"))
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["treatment_guidance"])
        self.assertEqual(data["treatment_guidance"]["chemical_treatment_name"], "Copper Hydroxide 50% WP")

        # 4. Verify saved in database
        guidance = get_treatment_guidance("Orange", "Citrus Canker")
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance["chemical_treatment_name"], "Copper Hydroxide 50% WP")

if __name__ == "__main__":
    unittest.main()
