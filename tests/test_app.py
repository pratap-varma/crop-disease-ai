import os
import unittest
from unittest.mock import patch, MagicMock
import json


class MockDocument:
    def __init__(self, id, data):
        self.id = id
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return self._data


class MockDocumentReference:
    def __init__(self, collection_name, doc_id, db):
        self.collection_name = collection_name
        self.doc_id = doc_id
        self.db = db

    def get(self):
        data = self.db.data[self.collection_name].get(self.doc_id)
        return MockDocument(self.doc_id, data)

    def set(self, data):
        self.db.data[self.collection_name][self.doc_id] = data

    def delete(self):
        if self.doc_id in self.db.data[self.collection_name]:
            del self.db.data[self.collection_name][self.doc_id]


class MockQuery:
    def __init__(self, results):
        self.results = results

    def get(self):
        return self.results

    def order_by(self, field, direction="ASCENDING"):
        return self


class MockCollection:
    def __init__(self, name, db):
        self.name = name
        self.db = db

    def document(self, doc_id):
        return MockDocumentReference(self.name, doc_id, self.db)

    def add(self, data):
        import uuid
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        self.db.data[self.name][doc_id] = data
        return doc_id

    def where(self, field, op, value):
        results = []
        for doc_id, doc_data in self.db.data[self.name].items():
            if op == "==" and doc_data.get(field) == value:
                results.append(MockDocument(doc_id, doc_data))
        return MockQuery(results)

    def order_by(self, field, direction="ASCENDING"):
        results = []
        for doc_id, doc_data in self.db.data[self.name].items():
            results.append(MockDocument(doc_id, doc_data))
        reverse = (direction == "DESCENDING")
        results.sort(key=lambda x: x.to_dict().get(field, ""), reverse=reverse)
        return MockQuery(results)

    def get(self):
        return [MockDocument(doc_id, doc_data) for doc_id, doc_data in self.db.data[self.name].items()]


class MockFirestore:
    def __init__(self):
        self.data = {
            "users": {},
            "predictions": {},
            "contact_messages": {}
        }

    def collection(self, name):
        return MockCollection(name, self)


# Start patchers before importing app so globals resolve cleanly
mock_db = MockFirestore()
admin_patcher = patch("firebase_admin.initialize_app")
client_patcher = patch("firebase_admin.firestore.client", return_value=mock_db)
admin_patcher.start()
client_patcher.start()

import app as app_module


class AppRoutesTests(unittest.TestCase):
    def setUp(self):
        self.mock_db = mock_db
        # Reset mock database state before each test
        self.mock_db.data = {
            "users": {},
            "predictions": {},
            "contact_messages": {}
        }
        # Re-initialize the app's db and seed default admin user
        app_module.db = self.mock_db
        app_module.init_db()

        self.client = app_module.app.test_client()
        with self.client.session_transaction() as session:
            session["logged_in"] = False

    def tearDown(self):
        pass

    def test_login_sets_session_and_redirects(self):
        response = self.client.post(
            "/login",
            data={"username_or_email": "admin", "password": "crop123"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/detect")

        with self.client.session_transaction() as session:
            self.assertTrue(session["logged_in"])

    def test_login_with_email_sets_session_and_redirects(self):
        response = self.client.post(
            "/login",
            data={"username_or_email": "admin@cropdisease.com", "password": "crop123"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/detect")

        with self.client.session_transaction() as session:
            self.assertTrue(session["logged_in"])

    def test_unauthenticated_user_is_redirected_to_login(self):
        response = self.client.get("/detect", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

    def test_delete_history_item_removes_record(self):
        app_module.save_prediction(
            "sample.jpg",
            {
                "crop_name": "Maize",
                "disease_name": "Leaf Blight",
                "confidence": "High",
                "severity": "Moderate",
                "additional_notes": "Test",
            },
        )

        item_id = list(self.mock_db.data["predictions"].keys())[0]

        with self.client.session_transaction() as session:
            session["logged_in"] = True

        response = self.client.post(f"/history/delete/{item_id}", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/history")

        remaining = len(self.mock_db.data["predictions"])
        self.assertEqual(remaining, 0)

    def test_profile_route_requires_login(self):
        response = self.client.get("/profile", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

    def test_profile_route_renders_for_logged_in_user(self):
        with self.client.session_transaction() as session:
            session["logged_in"] = True
            session["username"] = "admin"

        response = self.client.get("/profile", follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"admin", response.data)

    def test_signup_creates_user_with_email(self):
        response = self.client.post(
            "/signup",
            data={"username": "newuser", "email": "newuser@example.com", "password": "password123"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/detect")

        user = self.mock_db.data["users"].get("newuser")
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], "newuser@example.com")

    def test_signup_validates_existing_email(self):
        response = self.client.post(
            "/signup",
            data={"username": "newuser2", "email": "admin@cropdisease.com", "password": "password123"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Username or email already exists.", response.data)

    @patch("app.send_contact_email")
    def test_contact_form_submission_saves_to_db_and_calls_email(self, mock_send_email):
        with self.client.session_transaction() as session:
            session["logged_in"] = True
            session["username"] = "admin"

        mock_send_email.return_value = True

        response = self.client.post(
            "/contact",
            data={
                "name": "Jane Doe",
                "email": "jane@example.com",
                "message": "Hello, my crops need help!"
            },
            follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your message has been sent successfully.", response.data)

        # Find in mock database
        msg = None
        for data in self.mock_db.data["contact_messages"].values():
            if data["name"] == "Jane Doe":
                msg = data
                break
        self.assertIsNotNone(msg)
        self.assertEqual(msg["email"], "jane@example.com")
        self.assertEqual(msg["message"], "Hello, my crops need help!")

        mock_send_email.assert_called_once_with("Jane Doe", "jane@example.com", "Hello, my crops need help!")

    def test_login_prioritizes_email_match_on_collision(self):
        self.mock_db.data["users"]["collision@example.com"] = {
            "username": "collision@example.com",
            "email": None,
            "password": "pass1",
            "created_at": "2026-06-27T00:00:00"
        }
        self.mock_db.data["users"]["realuser"] = {
            "username": "realuser",
            "email": "collision@example.com",
            "password": "pass2",
            "created_at": "2026-07-06T00:00:00"
        }

        # Log in with collision@example.com and the email user's password (pass2)
        response = self.client.post(
            "/login",
            data={"username_or_email": "collision@example.com", "password": "pass2"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertTrue(session["logged_in"])
            self.assertEqual(session["username"], "realuser")

        # Log in with collision@example.com and the legacy user's password (pass1)
        response = self.client.post(
            "/login",
            data={"username_or_email": "collision@example.com", "password": "pass1"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertTrue(session["logged_in"])
            self.assertEqual(session["username"], "collision@example.com")


if __name__ == "__main__":
    unittest.main()
