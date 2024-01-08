import unittest
from unittest.mock import MagicMock
from db import DB

class TestDB(unittest.TestCase):
    def setUp(self):
        # Create a mock MongoClient
        mock_client = MagicMock()
        # Inject the mock client into the DB instance
        self.db = DB(client=mock_client)
        self.db.online_peers = self.db.db.online_peers
        self.db.rooms = self.db.db.rooms
        self.db.room_peers = self.db.db.room_peers
        self.db.online_room_peers=self.db.db.online_room_peers

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
    def test_user_logout(self):
        # Test user_logout removes a user correctly
        self.db.user_logout("testuser")
        self.db.online_peers.delete_one.assert_called_with({"username": "testuser"})

    def test_is_account_online_true(self):
        # Test is_account_online returns True when the user is online
        self.db.online_peers.count_documents.return_value = 1
        self.assertTrue(self.db.is_account_online("testuser"))

    def test_is_account_online_false(self):
        # Test is_account_online returns False when the user is not online
        self.db.online_peers.count_documents.return_value = 0
        self.assertFalse(self.db.is_account_online("nonexistinguser"))

    def test_search_all_online_accounts(self):
        # Test search_all_online_accounts returns a list of online users
        self.db.online_peers.find.return_value = [{"username": "user1"}, {"username": "user2"}]
        result = self.db.search_all_online_accounts()
        self.assertEqual(result, ["user1", "user2"])

    def test_search_user(self):
        # Test search_user returns the IP and port of the user
        self.db.online_peers.find_one.return_value = {"ip": "127.0.0.1", "port": "8080"}
        ip, port = self.db.search_user("testuser")
        self.assertEqual(ip, "127.0.0.1")
        self.assertEqual(port, "8080")
    def test_create_room(self):
        # Test create_room adds a room correctly
        self.db.create_room("testroom", "password123", "creatoruser")
        self.db.rooms.insert_one.assert_called_with({"roomname": "testroom", "password": "password123", "creator": "creatoruser"})

    def test_delete_room(self):
        # Test delete_room removes a room and associated data correctly
        self.db.delete_room("testroom", "creatoruser")
        self.db.rooms.delete_one.assert_called_with({"roomname": "testroom", "creator": "creatoruser"})
        self.db.room_peers.delete_many.assert_called_with({"roomname": "testroom"})
        self.db.online_room_peers.delete_many.assert_called_with({"roomname": "testroom"})

    def test_is_room_exist_true(self):
        # Test is_room_exist returns True when the room exists
        self.db.rooms.find_one.return_value = {"roomname": "testroom"}
        self.assertTrue(self.db.is_room_exist("testroom"))

    def test_is_room_exist_false(self):
        # Test is_room_exist returns False when the room does not exist
        self.db.rooms.find_one.return_value = None
        self.assertFalse(self.db.is_room_exist("nonexistingroom"))

    def test_get_room_details(self):
        # Test get_room_details returns the correct room details
        expected_details = {"password": "password123", "creator": "creatoruser"}
        self.db.rooms.find_one.return_value = expected_details
        room_details = self.db.get_room_details("testroom")
        self.assertEqual(room_details, expected_details)
    
    def test_join_room(self):
        self.db.room_peers.find_one.return_value = None
        self.db.join_room("testroom", "testuser")
        self.db.room_peers.insert_one.assert_called_with({"roomname": "testroom", "username": "testuser"})

    def test_leave_room(self):
        self.db.leave_room("testroom", "testuser")
        self.db.room_peers.delete_one.assert_called_with({"roomname": "testroom", "username": "testuser"})

    def test_show_rooms(self):
        self.db.room_peers.find.return_value = [{"roomname": "testroom1"}, {"roomname": "testroom2"}]
        rooms = self.db.show_rooms("testuser")
        self.assertEqual(rooms, [{"roomname": "testroom1"}, {"roomname": "testroom2"}])

    def test_get_users_in_room(self):
        self.db.room_peers.find.return_value = [{"username": "user1"}, {"username": "user2"}]
        users = self.db.get_users_in_room("testroom", "currentuser")
        self.assertEqual(users, [{"username": "user1"}, {"username": "user2"}])

    def test_is_user_in_room_true(self):
        self.db.room_peers.find_one.return_value = {"roomname": "testroom", "username": "testuser"}
        self.assertTrue(self.db.is_user_in_room("testroom", "testuser"))

    def test_is_user_in_room_false(self):
        self.db.room_peers.find_one.return_value = None
        self.assertFalse(self.db.is_user_in_room("testroom", "nonexistentuser"))

    def test_enter_room(self):
        # Test enter_room adds a user to a room correctly
        self.db.online_room_peers.find_one.return_value = None
        self.db.enter_room("testroom", "testuser")
        self.db.online_room_peers.insert_one.assert_called_with({"roomname": "testroom", "username": "testuser"})

    def test_exit_room(self):
        # Test exit_room removes a user from a room correctly
        self.db.exit_room("testroom", "testuser")
        self.db.online_room_peers.delete_one.assert_called_with({"roomname": "testroom", "username": "testuser"})

    def test_get_users_entered_room(self):
        # Test get_users_entered_room returns the correct list of users in a room
        self.db.online_room_peers.find.return_value = [{"username": "user1"}, {"username": "user2"}]
        users_in_room = self.db.get_users_entered_room("testroom", "currentuser")
        self.assertEqual(users_in_room, [{"username": "user1"}, {"username": "user2"}])


if __name__ == '__main__':
    unittest.main()
