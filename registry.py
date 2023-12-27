from socket import *
import threading
import select
import logging
import db
import os

# This class is used to process the peer messages sent to registry
# for each peer connected to registry, a new client thread is created
class ClientThread(threading.Thread):
    # initializations for client thread
    def __init__(self, ip, port, tcpClientSocket):
        threading.Thread.__init__(self)
        # ip of the connected peer
        self.ip = ip
        # port number of the connected peer
        self.port = port
        # socket of the peer
        self.tcpClientSocket = tcpClientSocket
        # username, online status and udp server initializations
        self.username = None
        self.isOnline = True
        self.udpServer = None
        ### print("New thread started for " + ip + ":" + str(port))

    # main of the thread
    def run(self):
        # locks for thread which will be used for thread synchronization
        self.lock = threading.Lock()
        print(format["BGREEN"] + "Connection from:" + format["END"])
        print("IP address: " + format["BBLUE"] + self.ip + format["END"])
        print("Port number: " + format["BBLUE"] + str(self.port) + format["END"])
        print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")
        
        while True:
            try:
                # waits for incoming messages from peers
                message = self.tcpClientSocket.recv(1024).decode().split()
                logging.info("Received from " + self.ip + ":" + str(self.port) + " -> " + " ".join(message))            
                
                #   JOIN    #
                if message[0] == "JOIN":
                    # join-exist is sent to peer,
                    # if an account with this username already exists
                    if db.is_account_exist(message[1]):
                        response = "join-exist"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)  
                        self.tcpClientSocket.send(response.encode())
                    # join-success is sent to peer,
                    # if an account with this username is not exist, and the account is created
                    else:
                        db.register(message[1], message[2])
                        print(format["BGREEN"] + "Account created:" + format["END"])
                        print("IP address: " + format["BBLUE"] + self.ip + format["END"])
                        print("Port number: " + format["BBLUE"] + str(self.port) + format["END"])
                        print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")
                        response = "join-success"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                
                
                #   LOGIN    #
                elif message[0] == "LOGIN":
                    # login-account-not-exist is sent to peer,
                    # if an account with the username does not exist
                    if not db.is_account_exist(message[1]):
                        response = "login-account-not-exist"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                    # login-online is sent to peer,
                    # if an account with the username already online
                    elif db.is_account_online(message[1]):
                        response = "login-online"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                    # login-success is sent to peer,
                    # if an account with the username exists and not online
                    else:
                        # retrieves the account's password, and checks if the one entered by the user is correct
                        retrievedPass = db.get_password(message[1])
                        # if password is correct, then peer's thread is added to threads list
                        # peer is added to db with its username, port number, and ip address
                        if retrievedPass == message[2]:
                            self.username = message[1]
                            self.lock.acquire()
                            try:
                                tcpThreads[self.username] = self
                            finally:
                                self.lock.release()
                            db.user_login(message[1], self.ip, message[3])
                            print(format["BGREEN"] + "Account logged in:" + format["END"])
                            print("IP address: " + format["BBLUE"] + self.ip + format["END"])
                            print("Port number: " + format["BBLUE"] + str(self.port) + format["END"])
                            print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")
                            # login-success is sent to peer,
                            # and a udp server thread is created for this peer, and thread is started
                            # timer thread of the udp server is started
                            response = "login-success"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                            self.udpServer = UDPServer(self.username, self.tcpClientSocket, self.ip, self.port)
                            self.udpServer.start()
                            self.udpServer.timer.start()
                        # if password not matches and then login-wrong-password response is sent
                        else:
                            response = "login-wrong-password"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                
                
                #   LOGOUT  #
                elif message[0] == "LOGOUT":
                    # if user is online,
                    # removes the user from onlinePeers list
                    # and removes the thread for this user from tcpThreads
                    # socket is closed and timer thread of the udp for this
                    # user is cancelled
                    if len(message) > 1 and message[1] is not None and db.is_account_online(message[1]):
                        db.user_logout(message[1])
                        self.lock.acquire()
                        try:
                            if message[1] in tcpThreads:
                                del tcpThreads[message[1]]
                        finally:
                            self.lock.release()
                        self.udpServer.timer.cancel()
                        print(format["BRED"] + "Account logged out:" + format["END"])
                        print("IP address: " + format["BBLUE"] + self.ip + format["END"])
                        print("Port number: " + format["BBLUE"] + str(self.port) + format["END"])
                        print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")
                    else:
                        self.tcpClientSocket.close()
                        print(format["BRED"] + "Connection end:" + format["END"])
                        print("IP address: " + format["BBLUE"] + self.ip + format["END"])
                        print("Port number: " + format["BBLUE"] + str(self.port) + format["END"])
                        print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")
                        break
                
                
                #   SEARCH  #
                elif message[0] == "SEARCH":
                    # checks if an account with the username exists
                    if db.is_account_exist(message[1]):
                        # checks if the account is online
                        # and sends the related response to peer
                        if db.is_account_online(message[1]):
                            peer_info = db.search_user(message[1])
                            response = "search-success " + peer_info[0] + ":" + peer_info[1]
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                        else:
                            response = "search-user-not-online"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                    # enters if username does not exist 
                    else:
                        response = "search-user-not-found"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                
                
                #   ONLINE PEERS   #
                elif message[0] == "ONLINE":
                    onlineUsers=db.search_all_online_accounts()
                    # checks if an account with the username exists
                    if len(onlineUsers)!=0:
                        # checks if the account is online
                        # and sends the related response to peer
                            response="Online-success"
                            for i in onlineUsers:
                              response += ":"+ i  
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                    else:
                            response = "no-user-online"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                
                
                #   DELETE    #
                elif message[0] == "DELETE":
                    # delete-account-not-exist is sent to peer,
                    # if an account with the username does not exist
                    if not db.is_account_exist(message[1]):
                        response = "delete-account-not-exist"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                    # delete-online is sent to peer,
                    # if an account with the username already online
                    elif db.is_account_online(message[1]):
                        response = "delete-online"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                    # delete-success is sent to peer,
                    # if an account with the username exists and not online
                    else:
                        # retrieves the account's password, and checks if the one entered by the user is correct
                        retrievedPass = db.get_password(message[1])
                        # if password is correct, then peer's thread is added to threads list
                        # peer is removed from db
                        if retrievedPass == message[2]:
                            self.username = message[1]
                            self.lock.acquire()
                            try:
                                tcpThreads[self.username] = self
                            finally:
                                self.lock.release()

                            db.delete_account(message[1])
                            print(format["BRED"] + "Account deleted:" + format["END"])
                            print("IP address: " + format["BBLUE"] + self.ip + format["END"])
                            print("Port number: " + format["BBLUE"] + str(self.port) + format["END"])
                            print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")
                            # delete-success is sent to peer
                            response = "delete-success"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                        # if password not matches and then delete-wrong-password response is sent
                        else:
                            response = "delete-wrong-password"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                
                
                #   CREATE ROOM   #
                elif message[0] == "CREATEROOM":
                    # if room exist
                    if db.is_room_exist(message[1]):
                        response = "room-exist"
                    # if room created
                    else:
                        db.create_room(message[1], message[2], self.username)
                        print(format["BGREEN"] + "Room created:" + format["END"])
                        print("IP address: " + format["BBLUE"] + self.ip + format["END"])
                        print("Port number: " + format["BBLUE"] + str(self.port) + format["END"])
                        print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")
                        response = "room-created"
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                    self.tcpClientSocket.send(response.encode())
                
                
                #   JOIN ROOM   #
                elif message[0] == "JOINROOM":
                    # if room doesn't exist
                    if not db.is_room_exist(message[1]): 
                        response = "room-not-exist"
                    # if room exist
                    else:
                        roomdetails = db.get_room_details(message[1])
                        if roomdetails["password"] == message[2]:
                            db.join_room(message[1],self.username)
                            print(format["BGREEN"] + "Room joined:" + format["END"])
                            print("IP address: " + format["BBLUE"] + self.ip + format["END"])
                            print("Port number: " + format["BBLUE"] + str(self.port) + format["END"])
                            print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")
                            response = "room-joined"
                        # if password not matches and then login-wrong-password response is sent
                        else:
                            response = "room-wrong-password"
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                    self.tcpClientSocket.send(response.encode())


                #   ENTER ROOM   #
                elif message[0] == "ENTERROOM":
                    # if room doesn't exist
                    if not db.is_room_exist(message[1]): 
                        response = "room-not-exist"
                    # if room exist
                    else:
                        isMember = db.is_user_in_room(message[1], self.username)
                        if isMember:
                            db.enter_room(message[1] , self.username)
                            response = "valid-room"
                        else:
                            response = "invalid-room"
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                    self.tcpClientSocket.send(response.encode())
                
                
                #   EXIT ROOM   #
                elif message[0] == "EXITROOM":
                    db.exit_room(message[1], self.username)
                
                
                #   SHOW ROOMS   #
                elif message[0] == "SHOWROOMS":
                    myRooms = db.show_rooms(self.username)
                    if myRooms:
                        response = str(myRooms)  # Convert the list to a string
                    else:
                        response = "no-rooms"
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                    self.tcpClientSocket.send(response.encode())
                
                
                
                #   SEARCH ROOM MEMBERS   #
                elif message[0] == "SEARCHROOM":
                    roomMembers = db.get_users_in_room(message[1], self.username)
                    if roomMembers:
                        response = str(roomMembers)  # Convert the list to a string
                    else:
                        response = "room-empty"
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                    self.tcpClientSocket.send(response.encode())
                
                
                #   SEARCH ONLINE ROOM MEMBERS   #
                elif message[0] == "SEARCHROOMONLINE":
                    roomMembers = db.get_users_entered_room(message[1], self.username)
                    if roomMembers:
                        response = str(roomMembers)  # Convert the list to a string
                    else:
                        response = "room-empty"
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                    self.tcpClientSocket.send(response.encode())
                
                
                #   LEAVE ROOM   #
                elif message[0] == "LEAVEROOM":
                    # if room doesn't exist
                    if not db.is_room_exist(message[1]): 
                        response = "room-not-exist"
                    # if room exist
                    else:
                        isMember = db.is_user_in_room(message[1], self.username)
                        if isMember:
                            db.leave_room(message[1], self.username)
                            response = "room-leaved"
                        else:
                            response = "not-member"
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                    self.tcpClientSocket.send(response.encode())
                
                
                #   DELETE ROOM   #
                elif message[0] == "DELETEROOM":
                    # if room doesn't exist
                    if not db.is_room_exist(message[1]): 
                        response = "room-not-exist"
                    # if room exist
                    else:
                        roomdetails = db.get_room_details(message[1])
                        if roomdetails["password"] == message[2]:
                            if roomdetails["creator"] == self.username:
                                db.delete_room(message[1],self.username)
                                print(format["BRED"] + "Room deleted:" + format["END"])
                                print("IP address: " + format["BBLUE"] + self.ip + format["END"])
                                print("Port number: " + format["BBLUE"] + str(self.port) + format["END"])
                                print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")
                                response = "room-deleted"
                            else:
                                response = "not-creator"
                        # if password not matches and then login-wrong-password response is sent
                        else:
                            response = "room-wrong-password"
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                    self.tcpClientSocket.send(response.encode())
            
            
            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr))
                break




    # function for resettin the timeout for the udp timer thread
    def resetTimeout(self):
        self.udpServer.resetTimer()

                            
# implementation of the udp server thread for clients
class UDPServer(threading.Thread):


    # udp server thread initializations
    def __init__(self, username, clientSocket, ip, port):
        threading.Thread.__init__(self)
        self.username = username
        self.ip = ip
        self.port = port
        # timer thread for the udp server is initialized
        self.timer = threading.Timer(3, self.waitHelloMessage)
        self.tcpClientSocket = clientSocket
    

    # if hello message is not received before timeout
    # then peer is disconnected
    def waitHelloMessage(self):
        if self.username is not None:
            db.user_logout(self.username)
            if self.username in tcpThreads:
                del tcpThreads[self.username]
        self.tcpClientSocket.close()
        print(format["BRED"] + "Connection lost:" + format["END"])
        print("IP address: " + format["BBLUE"] + self.ip + format["END"])
        print("Port number: " + format["BBLUE"] + str(self.port) + format["END"])
        print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")



    # resets the timer for udp server
    def resetTimer(self):
        self.timer.cancel()
        self.timer = threading.Timer(3, self.waitHelloMessage)
        self.timer.start()


# enables ansi escape characters in terminal
os.system("")  
format = {
    "RED": "\033[31m",
    "BRED": "\033[31;1m",
    "BACKRED": "\033[41;1m",
    
    "GREEN": "\033[32m",
    "BGREEN": "\033[32;1m",
    
    "YELLOW": "\033[33m",
    
    "BLUE": "\033[34m",
    "BBLUE": "\033[34;1m",
    
    "BOLD": "\033[1m",
    "END": "\033[0m",
}

# tcp and udp server port initializations
print("\n" + format["BGREEN"] + "Registy started:" + format["END"])
port = 15600
portUDP = 15500

# db initialization
db = db.DB()

# gets the ip address of this peer
# first checks to get it for windows devices
# if the device that runs this application is not windows
# it checks to get it for macos devices
hostname=gethostname()
try:
    host=gethostbyname(hostname)
except gaierror:
    import netifaces as ni
    host = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']


print("IP address: " + format["BBLUE"] + host + format["END"])
print("Port number: " + format["BBLUE"] + str(port) + format["END"])

# onlinePeers list for online account
onlinePeers = {}
# accounts list for accounts
accounts = {}
# tcpThreads list for online client's thread
tcpThreads = {}

#tcp and udp socket initializations
tcpSocket = socket(AF_INET, SOCK_STREAM)
udpSocket = socket(AF_INET, SOCK_DGRAM)
#binds the calls only from the same ip to the selected port number
tcpSocket.bind((host,port))
udpSocket.bind((host,portUDP))
#puts the server to listen mode
#5 means only 5 connections if there is 6 it will be refused
tcpSocket.listen(5)

# input sockets that are listened
inputs = [tcpSocket, udpSocket]

# log file initialization
logging.basicConfig(filename="registry.log", level=logging.INFO)

print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")

# as long as at least a socket exists to listen registry runs
while inputs:
    # monitors for the incoming connections
    readable, writable, exceptional = select.select(inputs, [], [])
    for s in readable:
        # if the message received comes to the tcp socket
        # the connection is accepted and a thread is created for it, and that thread is started
        if s is tcpSocket:
            tcpClientSocket, addr = tcpSocket.accept()
            newThread = ClientThread(addr[0], addr[1], tcpClientSocket)
            newThread.start()
        # if the message received comes to the udp socket
        elif s is udpSocket:
            # received the incoming udp message and parses it
            message, clientAddress = s.recvfrom(1024)
            message = message.decode().split()
            # checks if it is a hello message
            if message[0] == "HELLO":
                # checks if the account that this hello message 
                # is sent from is online
                if message[1] in tcpThreads:
                    # resets the timeout for that peer since the hello message is received
                    tcpThreads[message[1]].resetTimeout()
                    ### print("Hello is received from " + message[1])
                    ### print("\n" + format["YELLOW"] + "Listening for incoming connections..." + format["END"] + "\n")
                    logging.info("Received from " + clientAddress[0] + ":" + str(clientAddress[1]) + " -> " + " ".join(message))
                    
# registry tcp socket is closed
tcpSocket.close()

