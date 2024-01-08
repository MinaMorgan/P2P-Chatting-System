from pymongo import MongoClient

# Includes database operations
class DB:


    def __init__(self, client=None):
        if client is None:
            client = MongoClient('mongodb://localhost:27017/')
        self.client = client
        self.db = self.client['p2p-chat']
    

#######################################################################################################################
    # registers a user
    def register(self, username, password):
        account = {
            "username": username,
            "password": password
        }
        self.db.accounts.insert_one(account)                                    #new edit

    def delete_account(self, username):
        self.db.accounts.delete_one({"username": username})                     #new function

    # checks if an account with the username exists
    def is_account_exist(self, username):
        if self.db.accounts.count_documents({'username': username}) > 0:        #new edit
            return True
        else:
            return False

    # retrieves the password for a given username
    def get_password(self, username):
        return self.db.accounts.find_one({"username": username})["password"]    #new edit
#######################################################################################################################


#######################################################################################################################
    # logs in the user
    def user_login(self, username, ip, port):
        online_peer = {
            "username": username,
            "ip": ip,
            "port": port
        }
        self.db.online_peers.insert_one(online_peer)                            #new edit

    # logs out the user 
    def user_logout(self, username):
        self.db.online_peers.delete_one({"username": username})                 #new edit

    # checks if an account with the username online
    def is_account_online(self, username):
        if self.db.online_peers.count_documents({"username": username}) > 0:    #new edit
            return True
        else:
            return False

    def search_all_online_accounts(self):
        online_accounts_cursor = self.db.online_peers.find({}, {"_id": 0, "username": 1})
        online_accounts = [account["username"] for account in online_accounts_cursor]
        return online_accounts                                                  #new function

    # retrieves the ip address and the port number of the username
    def search_user(self, username):
        res = self.db.online_peers.find_one({"username": username})             #new edit
        return (res["ip"], res["port"])
#######################################################################################################################


#######################################################################################################################
    def create_room(self, roomname, password, username):
        room = {
            "roomname": roomname,
            "password": password,
            "creator": username
        }
        self.db.rooms.insert_one(room)                                    #new function
    
    def delete_room(self, roomname, username):
        self.db.rooms.delete_one({"roomname": roomname, "creator": username})                     #new function
        self.db.room_peers.delete_many({"roomname": roomname})
        self.db.online_room_peers.delete_many({"roomname": roomname})

    def is_room_exist(self, roomname):
        return bool(self.db.rooms.find_one({'roomname': roomname}))  # new function

    def get_room_details(self, roomname):
        return self.db.rooms.find_one({"roomname": roomname}, {"_id": 0, "password": 1, "creator": 1})
#######################################################################################################################


#######################################################################################################################
    def join_room(self, roomname, username):
        member = {
            "roomname": roomname,
            "username": username,
        }
        self.db.room_peers.insert_one(member)                                #new function

    def leave_room(self, roomname, username):
        self.db.room_peers.delete_one({"roomname": roomname, "username": username})                     #new function

    def show_rooms(self, username):
        cursor = self.db.room_peers.find({"username": username}, {"_id": 0, "roomname": 1})
        rooms = [{"roomname": doc["roomname"]} for doc in cursor]
        if rooms:
            return rooms
        else:
            return None

    def get_users_in_room(self, roomname, current_username):
        cursor = self.db.room_peers.find({"roomname": roomname, "username": {"$ne": current_username}}, {"_id": 0, "username": 1})
        users_in_room = [{"username": doc["username"]} for doc in cursor]
        if users_in_room:
            return users_in_room
        else:
            return None

    def is_user_in_room(self, roomname, username):
        user = self.db.room_peers.find_one({"roomname": roomname, "username": username})
        return user is not None
#######################################################################################################################


#######################################################################################################################
    def enter_room(self, roomname, username):
        member = {
            "roomname": roomname,
            "username": username,
        }
        self.db.online_room_peers.insert_one(member)                                #new function

    def exit_room(self, roomname, username):
        self.db.online_room_peers.delete_one({"roomname": roomname, "username": username})                     #new function

    def exit_all_rooms(self, username):
        if self.db.online_room_peers.find_one({"username": username}):            
            self.db.online_room_peers.delete_many({"username": username})

    def get_users_entered_room(self, roomname, current_username):
        cursor = self.db.online_room_peers.find({"roomname": roomname, "username": {"$ne": current_username}}, {"_id": 0, "username": 1})
        users_in_room = [{"username": doc["username"]} for doc in cursor]
        if users_in_room:
            return users_in_room
        else:
            return None