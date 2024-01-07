import unittest
from unittest.mock import MagicMock
from db import DB

class TestDB(unittest.TestCase):
    def setUp(self):
        # Create a mock MongoClient
        mock_client = MagicMock()
        # Inject the mock client into the DB instance
        self.db = DB(client=mock_client)

    # Test for register function
    def test_register_success(self):
        self.db.register("testuser", "testpass")
        self.db.db.accounts.insert_one.assert_called_with({"username": "testuser", "password": "testpass"})

    def test_register_failure(self):
        self.db.db.accounts.insert_one.side_effect = Exception("Failed to insert")
        with self.assertRaises(Exception):
            self.db.register("testuser", "testpass")

    # Test for is_account_exist function
    def test_is_account_exist_true(self):
        self.db.db.accounts.count_documents.return_value = 1
        self.assertTrue(self.db.is_account_exist("existinguser"))

    def test_is_account_exist_false(self):
        self.db.db.accounts.count_documents.return_value = 0
        self.assertFalse(self.db.is_account_exist("nonexistinguser"))

    # Test for get_password function
    def test_get_password_found(self):
        self.db.db.accounts.find_one.return_value = {"username": "user", "password": "pass"}
        self.assertEqual(self.db.get_password("user"), "pass")

    def test_get_password_not_found(self):
        self.db.db.accounts.find_one.return_value = None
        with self.assertRaises(TypeError):
            self.db.get_password("user")

    # ... (Continue writing tests for other methods)

if __name__ == '__main__':
    unittest.main()
