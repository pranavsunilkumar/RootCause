"""
API-level tests, as opposed to test_logic.py's internal-logic tests --
these go through FastAPI's TestClient, so they exercise routing,
pydantic validation, status codes and the full request/response cycle.

Needs FastAPI/SQLAlchemy installed (the full requirements.txt), unlike
test_logic.py's offline-safe subset. Uses an isolated temp sqlite DB so
it never touches your real rootcause.db.

Run with:
    cd backend
    ROOTCAUSE_DB=/tmp/rootcause_test.db python -m unittest tests.test_api -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from fastapi.testclient import TestClient

    HAS_FASTAPI = True
except ImportError as e:
    HAS_FASTAPI = False
    _IMPORT_ERROR = e


@unittest.skipUnless(HAS_FASTAPI, f"needs FastAPI/SQLAlchemy installed ({_IMPORT_ERROR if not HAS_FASTAPI else ''})")
class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp_db = tempfile.mktemp(suffix=".db")
        os.environ["DATABASE_URL"] = f"sqlite:///{cls._tmp_db}"
        os.environ["JWT_SECRET"] = "test-secret"
        from app.main import app  # imported after env vars are set, on purpose

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        from app.db import engine

        engine.dispose()  # release sqlite file handles before deleting it (required on Windows)
        if os.path.exists(cls._tmp_db):
            os.remove(cls._tmp_db)

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.json()["concepts_loaded"], 15)

    def test_list_concepts_shape(self):
        r = self.client.get("/api/concepts")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsInstance(body, list)
        self.assertIn("id", body[0])
        self.assertIn("prereqs", body[0])

    def test_unknown_concept_404s(self):
        r = self.client.get("/api/concepts/not-a-real-concept/chain")
        self.assertEqual(r.status_code, 404)

    def test_register_then_login(self):
        r = self.client.post("/api/auth/register", json={"username": "apitest_alice", "password": "correcthorsebattery"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("access_token", r.json())

        r2 = self.client.post("/api/auth/login", data={"username": "apitest_alice", "password": "correcthorsebattery"})
        self.assertEqual(r2.status_code, 200, r2.text)

    def test_register_duplicate_username_conflicts(self):
        self.client.post("/api/auth/register", json={"username": "apitest_dupe", "password": "correcthorsebattery"})
        r = self.client.post("/api/auth/register", json={"username": "apitest_dupe", "password": "anotherpassword"})
        self.assertEqual(r.status_code, 409)

    def test_register_rejects_short_password(self):
        r = self.client.post("/api/auth/register", json={"username": "apitest_bob", "password": "short"})
        self.assertEqual(r.status_code, 422)  # pydantic validation: min_length=8

    def test_login_wrong_password_401s(self):
        self.client.post("/api/auth/register", json={"username": "apitest_carol", "password": "correcthorsebattery"})
        r = self.client.post("/api/auth/login", data={"username": "apitest_carol", "password": "wrongpassword"})
        self.assertEqual(r.status_code, 401)

    def test_me_requires_auth(self):
        r = self.client.get("/api/auth/me")
        self.assertEqual(r.status_code, 401)

    def test_me_with_valid_token(self):
        reg = self.client.post("/api/auth/register", json={"username": "apitest_dave", "password": "correcthorsebattery"})
        token = reg.json()["access_token"]
        r = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["username"], "apitest_dave")

    def test_anonymous_diagnose_check_still_works(self):
        """Back-compat: no Authorization header, free-text user_id still works."""
        r = self.client.post(
            "/api/diagnose/check",
            json={"user_id": "anon-test-user", "target_concept": "vectors", "concept_id": "vectors", "answer": "a list of numbers with direction, added component by component"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("grade", r.json())

    def test_logged_in_user_cannot_spoof_a_different_user_id(self):
        """Authenticated requests use the token's identity, ignoring any
        user_id the client tries to pass in the body."""
        reg = self.client.post("/api/auth/register", json={"username": "apitest_erin", "password": "correcthorsebattery"})
        token = reg.json()["access_token"]

        self.client.post(
            "/api/diagnose/check",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "someone-else-entirely", "target_concept": "vectors", "concept_id": "vectors", "answer": "a list of numbers, added component by component"},
        )
        progress = self.client.get("/api/progress/apitest_erin").json()
        touched = {e["concept_id"]: e["status"] for e in progress["entries"]}
        self.assertEqual(touched["vectors"], "mastered")

        spoofed = self.client.get("/api/progress/someone-else-entirely").json()
        spoofed_touched = {e["concept_id"]: e["status"] for e in spoofed["entries"]}
        self.assertEqual(spoofed_touched["vectors"], "unseen")  # the spoof attempt did NOT land here

    def test_bughunt_full_cycle(self):
        snippet = self.client.get("/api/bughunt/gradient-descent")
        self.assertEqual(snippet.status_code, 200)
        self.assertNotIn("bug_line", snippet.json())  # the answer must not leak

        guess = self.client.post("/api/bughunt/guess", json={"user_id": "apitest_bugger", "concept_id": "gradient-descent", "guessed_line": 1})
        self.assertEqual(guess.status_code, 200)
        self.assertIn("correct_line", guess.json())

    def test_search_requires_query_param(self):
        r = self.client.get("/api/search")
        self.assertEqual(r.status_code, 422)

    def test_search_returns_results_for_relevant_query(self):
        r = self.client.get("/api/search", params={"q": "softmax numerical stability"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(len(r.json()) > 0)

    def test_leaderboard_is_a_list(self):
        r = self.client.get("/api/leaderboard")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_zz_rate_limit_eventually_kicks_in_on_auth(self):
        """Hammer a cheap, deterministically-failing auth call past the
        20/60s limit and confirm the limiter actually engages.

        Named to sort alphabetically last: the rate limiter's bucket is
        keyed by (client IP, exact path), and TestClient always presents
        the same fake IP, so saturating /api/auth/login here would 429
        any other test that logs in afterward in the same test run.
        """
        last_status = None
        for _ in range(25):
            resp = self.client.post("/api/auth/login", data={"username": "rl-test", "password": "nope"})
            last_status = resp.status_code
        self.assertEqual(last_status, 429)


if __name__ == "__main__":
    unittest.main()
