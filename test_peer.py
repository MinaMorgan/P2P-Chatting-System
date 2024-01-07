import unittest
from unittest.mock import patch, MagicMock
import socket
from peer import PeerServer

class MockDB:
    def __init__(self):
        # Mock the methods of DB that are used in PeerServer
        self.register = MagicMock()
        self.delete_account = MagicMock()
        self.is_account_exist = MagicMock()
        self.get_password = MagicMock()
        self.user_login = MagicMock()
        self.user_logout = MagicMock()
        self.is_account_online = MagicMock()
        self.search_all_online_accounts = MagicMock()
        self.search_user = MagicMock()
        self.create_room = MagicMock()
        self.delete_room = MagicMock()
        self.is_room_exist = MagicMock()
        self.get_room_details = MagicMock()
        self.join_room = MagicMock()
        self.leave_room = MagicMock()
        self.show_rooms = MagicMock()
        self.get_users_in_room = MagicMock()
        self.is_user_in_room = MagicMock()
        self.enter_room = MagicMock()
        self.exit_room = MagicMock()
        self.get_users_entered_room = MagicMock()
        # Add other mocked methods as needed

class TestPeerServer(unittest.TestCase):

    def setUp(self):
        self.username = "test_user"
        self.port = 12345
        self.mock_db = MockDB()
        self.server = PeerServer(self.username, self.port, self.mock_db)

    def test_initialization(self):
        self.assertEqual(self.server.username, "test_user")
        self.assertEqual(self.server.peerServerPort, 12345)

    def test_format_hyperlink(self):
        url = "example.com"
        expected = '\033]8;;https://example.com\ahttps://example.com\033]8;;\a'
        self.assertEqual(self.server.format_hyperlink(url), expected)

        url_with_http = "http://example.com"
        expected = '\033]8;;http://example.com\ahttp://example.com\033]8;;\a'
        self.assertEqual(self.server.format_hyperlink(url_with_http), expected)

    @patch('socket.socket')
    def test_run_socket_initialization(self, mock_socket):
        self.server.run()
        mock_socket.assert_called_with(socket.AF_INET, socket.SOCK_STREAM)

    @patch.object(PeerServer, 'handle_message')
    def test_run_message_handling(self, mock_handle_message):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b'Some message'
        mock_socket.fileno.return_value = 1

        with patch('select.select', return_value=([mock_socket], [], [])):
            self.server.isOnline = False 
            self.server.run()

        mock_handle_message.assert_called_with(b'Some message', mock_socket)

class TestPeerServerRun(unittest.TestCase):

    def setUp(self):
        self.username = "test_user"
        self.port = 12345
        self.mock_db = MockDB()
        self.server = PeerServer(self.username, self.port, self.mock_db)
        self.server.isOnline = True

    @patch('socket.socket')
    @patch('select.select')
    def test_run_basic_flow(self, mock_select, mock_socket):
        mock_server_socket = MagicMock()
        mock_server_socket.accept.return_value = (MagicMock(), ('127.0.0.1', 1234))
        mock_socket.return_value = mock_server_socket

        mock_select.return_value = ([mock_server_socket], [], [])

        mock_client_socket = MagicMock()
        mock_client_socket.recv.return_value = b'Hello'
        mock_server_socket.accept.return_value = (mock_client_socket, ('127.0.0.1', 1234))

        from threading import Thread
        server_thread = Thread(target=self.server.run)
        server_thread.start()

        import time
        time.sleep(1)
        self.server.isOnline = False
        server_thread.join()

        mock_socket.assert_called_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_server_socket.bind.assert_called_with(('localhost', 12345))
        mock_server_socket.listen.assert_called_with(4)

        mock_server_socket.accept.assert_called()

        mock_client_socket.recv.assert_called_with(1024)

if __name__ == '__main__':
    unittest.main()
