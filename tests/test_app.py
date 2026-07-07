import os
import tempfile
import unittest
from unittest.mock import patch

import app as app_module


class AppRoutesTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.patcher = patch("app.DB_PATH", self.db_path)
        self.patcher.start()

        app_module.init_db()
        self.client = app_module.app.test_client()
        with self.client.session_transaction() as session:
            session["logged_in"] = False

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
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

        with app_module.get_db() as conn:
            item_id = conn.execute("SELECT id FROM predictions LIMIT 1").fetchone()[0]

        with self.client.session_transaction() as session:
            session["logged_in"] = True

        response = self.client.post(f"/history/delete/{item_id}", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/history")

        with app_module.get_db() as conn:
            remaining = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]

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
        self.assertIn(b"Registered User", response.data)

    def test_signup_creates_user_with_email(self):
        response = self.client.post(
            "/signup",
            data={"username": "newuser", "email": "newuser@example.com", "password": "password123"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/detect")

        with app_module.get_db() as conn:
            user = conn.execute("SELECT email FROM users WHERE username = ?", ("newuser",)).fetchone()
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

        with app_module.get_db() as conn:
            msg = conn.execute("SELECT * FROM contact_messages WHERE name = ?", ("Jane Doe",)).fetchone()
        self.assertIsNotNone(msg)
        self.assertEqual(msg["email"], "jane@example.com")
        self.assertEqual(msg["message"], "Hello, my crops need help!")

        mock_send_email.assert_called_once_with("Jane Doe", "jane@example.com", "Hello, my crops need help!")

    def test_login_prioritizes_email_match_on_collision(self):
        with app_module.get_db() as conn:
            conn.execute(
                "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
                ("collision@example.com", None, "pass1", "2026-06-27T00:00:00")
            )
            conn.execute(
                "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
                ("realuser", "collision@example.com", "pass2", "2026-07-06T00:00:00")
            )
            conn.commit()

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
