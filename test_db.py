import unittest
from unittest.mock import MagicMock
from db import DB

class TestDB(unittest.TestCase):

    def setUp(self):
        self.db = DB()
        self.db.db = MagicMock()  # Mock the database connection

    def test_register(self):
        # Setup
        username = "testuser"
        password = "testpass"
        
        # Execute
        self.db.register(username, password)

        # Verify
        self.db.db.accounts.insert_one.assert_called_with({"username": username, "password": password})

    def test_is_account_exist(self):
        # Setup
        username = "existinguser"
        self.db.db.accounts.count_documents.return_value = 1

        # Execute and Verify
        self.assertTrue(self.db.is_account_exist(username))

    def test_user_login(self):
        # Setup
        username = "onlineuser"
        ip = "127.0.0.1"
        port = "8080"
        
        # Execute
        self.db.user_login(username, ip, port)

        # Verify
        self.db.db.online_peers.insert_one.assert_called_with({"username": username, "ip": ip, "port": port})

if __name__ == '__main__':
    unittest.main()
