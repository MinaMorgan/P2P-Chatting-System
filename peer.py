from socket import *
import hashlib
import threading
import time
import select
import logging
import os
import ast

# Server side of peer
class PeerServer(threading.Thread):


    # Peer server initialization
    # initialized in login
    def __init__(self, username, peerServerPort):
        threading.Thread.__init__(self)
        # keeps the username of the peer
        self.username = username
        # tcp socket for peer server
        self.tcpServerSocket = socket(AF_INET, SOCK_STREAM)
        # port number of the peer server
        self.peerServerPort = peerServerPort
        # if 1, then user is already chatting with someone
        # if 0, then user is not chatting with anyone
        self.isChatRequested = 0
        self.isRoomRequested = 0
        # keeps the socket for the peer that is connected to this peer
        self.connectedPeerSocket = None
        # keeps the ip of the peer that is connected to this peer's server
        self.connectedPeerIP = None
        # keeps the port number of the peer that is connected to this peer's server
        self.connectedPeerPort = None
        # online status of the peer
        self.isOnline = True
        # keeps the username of the peer that this peer is chatting with
        self.chattingClientName = None
    

    # main method of the peer server thread
    def run(self):

        ###print("Peer server started...")    

        # gets the ip address of this peer
        # first checks to get it for windows devices
        # if the device that runs this application is not windows
        # it checks to get it for macos devices
        hostname=gethostname()
        try:
            self.peerServerHostname=gethostbyname(hostname)
        except gaierror:
            import netifaces as ni
            self.peerServerHostname = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']

        # ip address of this peer
        #self.peerServerHostname = 'localhost'
        # socket initializations for the server of the peer
        self.tcpServerSocket.bind((self.peerServerHostname, self.peerServerPort))
        self.tcpServerSocket.listen(4)
        # inputs sockets that should be listened
        inputs = [self.tcpServerSocket]
        # server listens as long as there is a socket to listen in the inputs list and the user is online
        while inputs and self.isOnline:
            # monitors for the incoming connections
            try:
                readable, writable, exceptional = select.select(inputs, [], [])
                # If a server waits to be connected enters here
                for s in readable:
                    # if the socket that is receiving the connection is 
                    # the tcp socket of the peer's server, enters here
                    if s is self.tcpServerSocket:
                        # accepts the connection, and adds its connection socket to the inputs list
                        # so that we can monitor that socket as well
                        connected, addr = s.accept()
                        connected.setblocking(0)
                        inputs.append(connected)
                        # if the user is not chatting, then the ip and the socket of
                        # this peer is assigned to server variables
                        if self.isChatRequested == 0:     
                            # print(self.username + " is connected from " + str(addr))
                            self.connectedPeerSocket = connected
                            self.connectedPeerIP = addr[0]
                    # if the socket that receives the data is the one that
                    # is used to communicate with a connected peer, then enters here
                    else:
                        # message is received from connected peer
                        messageReceived = s.recv(1024).decode()
                        # logs the received message
                        logging.info("Received from " + str(self.connectedPeerIP) + " -> " + str(messageReceived))
                        # if message is a request message it means that this is the receiver side peer server
                        # so evaluate the chat request
                        if len(messageReceived) > 11 and messageReceived[:12] == "CHAT-REQUEST" and not self.isRoomRequested:
                            # text for proper input choices is printed however OK or REJECT is taken as input in main process of the peer
                            # if the socket that we received the data belongs to the peer that we are chatting with,
                            # enters here
                            if s is self.connectedPeerSocket:
                                # parses the message
                                messageReceived = messageReceived.split()
                                # gets the port of the peer that sends the chat request message
                                self.connectedPeerPort = int(messageReceived[1])
                                # gets the username of the peer sends the chat request message
                                self.chattingClientName = messageReceived[2]
                                # prints prompt for the incoming chat request
                                print("Incoming chat request from " + self.chattingClientName + " >> ")
                                print("Enter OK to accept or REJECT to reject:  ")
                                # makes isChatRequested = 1 which means that peer is chatting with someone
                                self.isChatRequested = 1
                            # if the socket that we received the data does not belong to the peer that we are chatting with
                            # and if the user is already chatting with someone else(isChatRequested = 1), then enters here
                            elif s is not self.connectedPeerSocket and self.isChatRequested == 1:
                                # sends a busy message to the peer that sends a chat request when this peer is 
                                # already chatting with someone else
                                message = "BUSY"
                                s.send(message.encode())
                                # remove the peer from the inputs list so that it will not monitor this socket
                                inputs.remove(s)
                        # if an OK message is received then ischatrequested is made 1 and then next messages will be shown to the peer of this server
                        elif messageReceived == "OK" and not self.isRoomRequested:
                            self.isChatRequested = 1
                        # if an REJECT message is received then ischatrequested is made 0 so that it can receive any other chat requests
                        elif messageReceived == "REJECT" and not self.isRoomRequested:
                            self.isChatRequested = 0
                            inputs.remove(s)
                        # if a message is received, and if this is not a quit message ':q' and 
                        # if it is not an empty message, show this message to the user
                        elif messageReceived[:2] != ":q" and len(messageReceived)!= 0 and not self.isRoomRequested:
                            print(self.chattingClientName + ": " + messageReceived)
                        # if the message received is a quit message ':q',
                        # makes ischatrequested 1 to receive new incoming request messages
                        # removes the socket of the connected peer from the inputs list
                        elif messageReceived[:2] == ":q" and not self.isRoomRequested:
                            self.isChatRequested = 0
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
                            # connected peer ended the chat
                            if len(messageReceived) == 2:
                                print("User you're chatting with ended the chat")
                                print("Press enter to quit the chat: ")
                        # if the message is an empty one, then it means that the
                        # connected user suddenly ended the chat(an error occurred)
                        elif len(messageReceived) == 0 and not self.isRoomRequested:
                            self.isChatRequested = 0
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
                            print("User you're chatting with suddenly ended the chat")
                            print("Press enter to quit the chat: ")
                        elif self.isRoomRequested and not self.isChatRequested and not(messageReceived[:12] == "CHAT-REQUEST"):
                            message = messageReceived.split()
                            # gets the username of the peer sends the chat request message
                            self.chattingClientName = message[0]
                            messageReceived = " ".join(message[1:])
                            if messageReceived == ":q":
                                print("\n" + format["BRED"] + self.chattingClientName + " quit\n" + format["END"])
                            else:
                                print(self.chattingClientName + ": " + messageReceived)
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
            # handles the exceptions, and logs them
            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr))
            except ValueError as vErr:
                logging.error("ValueError: {0}".format(vErr))
            

# Client side of peer
class PeerClient(threading.Thread):
    # variable initializations for the client side of the peer
    def __init__(self, ipToConnect, portToConnect, username, peerServer, responseReceived):
        threading.Thread.__init__(self)
        # keeps the ip address of the peer that this will connect
        self.ipToConnect = ipToConnect
        # keeps the username of the peer
        self.username = username
        # keeps the port number that this client should connect
        self.portToConnect = portToConnect
        # client side tcp socket initialization
        self.tcpClientSocket = socket(AF_INET, SOCK_STREAM)
        # keeps the server of this client
        self.peerServer = peerServer
        # keeps the phrase that is used when creating the client
        # if the client is created with a phrase, it means this one received the request
        # this phrase should be none if this is the client of the requester peer
        self.responseReceived = responseReceived
        # keeps if this client is ending the chat or not
        self.isEndingChat = False


    # main method of the peer client thread
    def run(self):
        print("Peer client started...")
        # connects to the server of other peer
        self.tcpClientSocket.connect((self.ipToConnect, self.portToConnect))
        # if the server of this peer is not connected by someone else and if this is the requester side peer client then enters here
        if self.peerServer.isChatRequested == 0 and self.responseReceived is None:
            # composes a request message and this is sent to server and then this waits a response message from the server this client connects
            requestMessage = "CHAT-REQUEST " + str(self.peerServer.peerServerPort)+ " " + self.username
            # logs the chat request sent to other peer
            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + requestMessage)
            # sends the chat request
            self.tcpClientSocket.send(requestMessage.encode())
            print("Request message " + requestMessage + " is sent...")
            # received a response from the peer which the request message is sent to
            self.responseReceived = self.tcpClientSocket.recv(1024).decode()
            # logs the received message
            logging.info("Received from " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + self.responseReceived)
            print("Response is " + self.responseReceived)
            # parses the response for the chat request
            self.responseReceived = self.responseReceived.split()
            # if response is ok then incoming messages will be evaluated as client messages and will be sent to the connected server
            if self.responseReceived[0] == "OK":
                # changes the status of this client's server to chatting
                self.peerServer.isChatRequested = 1
                # sets the server variable with the username of the peer that this one is chatting
                self.peerServer.chattingClientName = self.responseReceived[1]
                # as long as the server status is chatting, this client can send messages
                while self.peerServer.isChatRequested == 1:
                    # message input prompt
                    messageSent = input("- ")
                    # sends the message to the connected peer, and logs it
                    self.tcpClientSocket.send(messageSent.encode())
                    logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + messageSent)
                    # if the quit message is sent, then the server status is changed to not chatting
                    # and this is the side that is ending the chat
                    if messageSent == ":q":
                        self.peerServer.isChatRequested = 0
                        self.isEndingChat = True
                        break
                # if peer is not chatting, checks if this is not the ending side
                if self.peerServer.isChatRequested == 0:
                    if not self.isEndingChat:
                        # tries to send a quit message to the connected peer
                        # logs the message and handles the exception
                        try:
                            self.tcpClientSocket.send(":q ending-side".encode())
                            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> :q")
                        except BrokenPipeError as bpErr:
                            logging.error("BrokenPipeError: {0}".format(bpErr))
                    # closes the socket
                    self.responseReceived = None
                    self.tcpClientSocket.close()
            # if the request is rejected, then changes the server status, sends a reject message to the connected peer's server
            # logs the message and then the socket is closed       
            elif self.responseReceived[0] == "REJECT":
                self.peerServer.isChatRequested = 0
                print("client of requester is closing...")
                self.tcpClientSocket.send("REJECT".encode())
                logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> REJECT")
                self.tcpClientSocket.close()
            # if a busy response is received, closes the socket
            elif self.responseReceived[0] == "BUSY":
                print("Receiver peer is busy")
                self.tcpClientSocket.close()
        # if the client is created with OK message it means that this is the client of receiver side peer
        # so it sends an OK message to the requesting side peer server that it connects and then waits for the user inputs.
        elif self.responseReceived == "OK":
            # server status is changed
            self.peerServer.isChatRequested = 1
            # ok response is sent to the requester side
            okMessage = "OK"
            self.tcpClientSocket.send(okMessage.encode())
            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + okMessage)
            print("Client with OK message is created... and sending messages")
            # client can send messsages as long as the server status is chatting
            while self.peerServer.isChatRequested == 1:
                # input prompt for user to enter message
                messageSent = input("- ")
                self.tcpClientSocket.send(messageSent.encode())
                logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + messageSent)
                # if a quit message is sent, server status is changed
                if messageSent == ":q":
                    self.peerServer.isChatRequested = 0
                    self.isEndingChat = True
                    break
            # if server is not chatting, and if this is not the ending side
            # sends a quitting message to the server of the other peer
            # then closes the socket
            if self.peerServer.isChatRequested == 0:
                if not self.isEndingChat:
                    self.tcpClientSocket.send(":q ending-side".encode())
                    logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> :q")
                self.responseReceived = None
                self.tcpClientSocket.close()
                

# main process of the peer
class peerMain:

    # peer initializations
    def __init__(self):
        # ip address of the registry
        self.registryName = input(format["CYAN"] + "\nEnter IP address of registry: " + format["END"])
        #self.registryName = 'localhost'
        # port number of the registry
        self.registryPort = 15600
        # tcp socket connection to registry
        self.tcpClientSocket = socket(AF_INET, SOCK_STREAM)
        self.tcpClientSocket.connect((self.registryName,self.registryPort))
        # initializes udp socket which is used to send hello messages
        self.udpClientSocket = socket(AF_INET, SOCK_DGRAM)
        # udp port of the registry
        self.registryUDPPort = 15500
        # login info of the peer
        self.loginCredentials = (None, None)
        # online status of the peer
        self.isOnline = False
        # server port number of this peer
        self.peerServerPort = None
        # server of this peer
        self.peerServer = None
        # client of this peer
        self.peerClient = None
        # timer initialization
        self.timer = None
        
        flag = True
        # log file initialization
        logging.basicConfig(filename="peer.log", level=logging.INFO)
        # as long as the user is not logged out, asks to select an option in the menu
        while flag:
        
            # menu selection prompt
            print("_____________________________________________________")
            print("\n       Menu")
            
            if self.isOnline == False:
                print("[1] " + format["BCYAN"] + "Create account" + format["END"])
                print("[2] " + format["BCYAN"] + "Login" + format["END"])
                print("[3] " + format["BCYAN"] + "Exit program" + format["END"])
            else:
                print("[1] " + format["BCYAN"] + "Start a chat" + format["END"])
                print("[2] " + format["BCYAN"] + "Search user" + format["END"])
                print("[3] " + format["BCYAN"] + "Check online users" + format["END"])
                print("[4] " + format["BCYAN"] + "Delete account" + format["END"])
                print("[5] " + format["BCYAN"] + "Create room" + format["END"])
                print("[6] " + format["BCYAN"] + "Join room" + format["END"])
                print("[7] " + format["BCYAN"] + "Start a room chat" + format["END"])
                print("[8] " + format["BCYAN"] + "Leave room" + format["END"])
                print("[9] " + format["BCYAN"] + "Delete room" + format["END"])
                print("[10] " + format["BCYAN"] + "Logout" + format["END"])
            
            choice = input(format["CYAN"] + "\nChoice: " + format["END"])
            print()
            
            if self.isOnline == False and (choice != "1" and choice != "2" and choice != "3"):
                print(format["BACKRED"] + "Please Enter Correct number" + format["END"])
            elif self.isOnline == True and (choice != "1" and choice != "2" and choice != "3" and choice != "4" and choice != "5" and choice != "6" and choice != "7" and choice != "8" and choice != "9" and choice != "10" and choice != "OK" and choice != "REJECT"):
                print(format["BACKRED"] + "Please Enter Correct number" + format["END"])
            ###################################################################
            
            # Create Account
            if choice == "1" and not self.isOnline:
                print("Create Account")
                username = input(format["CYAN"] + "username: " + format["END"])
                password = input(format["CYAN"] + "password: " + format["END"])
                self.createAccount(username, password)
            ###################################################################
            
            # Log in
            elif choice == "2" and not self.isOnline:
                print("Log In")
                username = input(format["CYAN"] + "username: " + format["END"])
                password = input(format["CYAN"] + "password: " + format["END"])
                peerServerPort = int(input(format["CYAN"] + "Enter a port number for peer server: " + format["END"]))
                
                status = self.login(username, password, peerServerPort)
                # is user logs in successfully, peer variables are set
                if status == 1:
                    self.isOnline = True
                    self.loginCredentials = (username, password)
                    self.peerServerPort = peerServerPort
                    # creates the server thread for this peer, and runs it
                    self.peerServer = PeerServer(self.loginCredentials[0], self.peerServerPort)
                    self.peerServer.start()
                    
                    #self.roomServer = RoomServer(self.loginCredentials[0], self.peerServerPort)
                    #self.roomServer.start()
                    # hello message is sent to registry
                    self.sendHelloMessage()
            ###################################################################
            
            # Exit Program
            elif choice == "3" and not self.isOnline:
                flag = False
                self.logout(2)
                print(format["BGREEN"] + "You exit successfully" + format["END"])
            ###################################################################
            
            # Start Chat
            elif choice == "1" and self.isOnline:
                print("One to One Chat")
                username = input(format["CYAN"] + "username: " + format["END"])
                searchStatus = self.searchUser(username)
                # if searched user is found, then its ip address and port number is retrieved
                # and a client thread is created
                # main process waits for the client thread to finish its chat
                if searchStatus != None and searchStatus != 0:
                    searchStatus = searchStatus.split(":")
                    self.peerClient = PeerClient(searchStatus[0], int(searchStatus[1]) , self.loginCredentials[0], self.peerServer, None)
                    self.peerClient.start()
                    self.peerClient.join()
            ###################################################################
            
            # Search User
            elif choice == "2" and self.isOnline:
                print("Search Account")
                username = input(format["CYAN"] + "username: " + format["END"])
                searchStatus = self.searchUser(username)
                
                if searchStatus is None:
                    print(format["BRED"] + "\n" + username + " is not found" + format["END"])
                elif searchStatus == 0:
                    print(format["BRED"] + "\n" + username + " is not online..." + format["END"])
                # if user is found its ip address is shown to user
                else:
                    print(format["BGREEN"] + "\n" + username + " is found successfully..." + format["END"])
                    print("IP address of " + username + " is " + searchStatus)
            ###################################################################
            
            #Search All Online Users
            elif choice == "3"and self.isOnline:
                self.onlineUsers()
            ###################################################################
            
            # Delete Account
            elif choice == "4" and self.isOnline:
                print("Delete Account")
                username = input(format["CYAN"] + "username: " + format["END"])
                password = input(format["CYAN"] + "password: " + format["END"])
                self.delete(username, password)
            ###################################################################
            
            # Create Room
            elif choice == "5" and self.isOnline:
                print("Create Room")
                roomname = input(format["CYAN"] + "roomname: " + format["END"])
                password = input(format["CYAN"] + "password: " + format["END"])
                self.createRoom(roomname, password)
            ###################################################################
            
            # Join Room
            elif choice == "6" and self.isOnline:
                print("Join Room")
                roomname = input(format["CYAN"] + "roomname: " + format["END"])
                password = input(format["CYAN"] + "password: " + format["END"])
                self.joinRoom(roomname, password)
            ###################################################################
            
            # Enter Room
            elif choice == "7" and self.isOnline:
                status = self.showRooms()
                if status:
                    roomname = input(format["CYAN"] + "\nEnter Room Name: " + format["END"])
                    self.enterRoom(roomname)
            ###################################################################
            
            # Leave Room
            elif choice == "8" and self.isOnline:
                print("Leave Room")
                roomname = input(format["CYAN"] + "roomname: " + format["END"])
                self.leaveRoom(roomname)
            ###################################################################
            
            # Delete Room
            elif choice == "9" and self.isOnline:
                print("Delete Room")
                roomname = input(format["CYAN"] + "roomname: " + format["END"])
                password = input(format["CYAN"] + "password: " + format["END"])
                self.deleteRoom(roomname, password)
            ###################################################################
            
            # Log out
            elif choice == "10" and self.isOnline:
                self.logout(1)
                self.isOnline = False
                self.loginCredentials = (None, None)
                self.peerServer.isOnline = False
                self.peerServer.tcpServerSocket.close()
                if self.peerClient != None:
                    self.peerClient.tcpClientSocket.close()
                print(format["BGREEN"] + "Logged out successfully" + format["END"])
            ###################################################################
            
            
            
            
            
            
            
            # if this is the receiver side then it will get the prompt to accept an incoming request during the main loop
            # that's why response is evaluated in main process not the server thread even though the prompt is printed by server
            # if the response is ok then a client is created for this peer with the OK message and that's why it will directly
            # sent an OK message to the requesting side peer server and waits for the user input
            # main process waits for the client thread to finish its chat
            elif choice == "OK" and self.isOnline:
                okMessage = "OK " + self.loginCredentials[0]
                logging.info("Send to " + self.peerServer.connectedPeerIP + " -> " + okMessage)
                self.peerServer.connectedPeerSocket.send(okMessage.encode())
                self.peerClient = PeerClient(self.peerServer.connectedPeerIP, self.peerServer.connectedPeerPort , self.loginCredentials[0], self.peerServer, "OK")
                self.peerClient.start()
                self.peerClient.join()
            # if user rejects the chat request then reject message is sent to the requester side
            elif choice == "REJECT" and self.isOnline:
                self.peerServer.connectedPeerSocket.send("REJECT".encode())
                self.peerServer.isChatRequested = 0
                logging.info("Send to " + self.peerServer.connectedPeerIP + " -> REJECT")
            # if choice is cancel timer for hello message is cancelled
            elif choice == "CANCEL":
                self.timer.cancel()
                break
        # if main process is not ended with cancel selection
        # socket of the client is closed
        if choice != "CANCEL":
            self.tcpClientSocket.close()
##########################################################################################################################################
    
    
    # hashing function
    def dataHashed(self, data):
        hash_object = hashlib.sha256()
        hash_object.update(data.encode())
        data_hash = hash_object.hexdigest()
        return data_hash
    ###################################################################

    # account creation function
    def createAccount(self, username, password):
        hashed_password = self.dataHashed(password)
        message = "JOIN " + username + " " + hashed_password
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "join-success":
            print(format["BGREEN"] + "\nAccount created..." + format["END"])
        elif response == "join-exist":
            print(format["BRED"] + "\nchoose another username or login..." + format["END"])
    ###################################################################
    
    
    # login function
    def login(self, username, password, peerServerPort):
        hashed_password = self.dataHashed(password)
        message = "LOGIN " + username + " " + hashed_password + " " + str(peerServerPort)
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "login-success":
            print(format["BGREEN"] + "\nLogged in successfully..." + format["END"])
            return 1
        elif response == "login-account-not-exist":
            print(format["BRED"] + "\nAccount does not exist..." + format["END"])
            return 0
        elif response == "login-online":
            print(format["BRED"] + "\nAccount is already online..." + format["END"])
            return 2
        elif response == "login-wrong-password":
            print(format["BRED"] + "\nWrong password..." + format["END"])
            return 3
    ###################################################################
    
    
    # logout function
    def logout(self, option):
        # a logout message is composed and sent to registry
        # timer is stopped
        if option == 1:
            message = "LOGOUT " + self.loginCredentials[0]
            self.timer.cancel()
        else:
            message = "LOGOUT"
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
    ###################################################################
    
    
    # function for searching an online user
    def searchUser(self, username):
        message = "SEARCH " + username
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode().split()
        logging.info("Received from " + self.registryName + " -> " + " ".join(response))
        if response[0] == "search-success":
            return response[1] # this line return ip and port number
        elif response[0] == "search-user-not-online":
            return 0
        elif response[0] == "search-user-not-found":
            return None
    ###################################################################
    
    
    # function for searching all online users
    def onlineUsers(self):
        message = "ONLINE"
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode().split(':')
        logging.info("Received from " + self.registryName + " -> " + " ".join(response))
        if response[0] == "Online-success":
            print(format["BGREEN"] + "Online Users:" + format["END"])
            for i in range (1,len(response)):
                print("- "+  response[i])  
        elif response[0] == "no-user-online":
            print(format["BRED"] + "No user is online" + format["END"])
    ###################################################################
    
    
    # account delete function
    def delete(self, username, password):
        hashed_password = self.dataHashed(password)
        message = "DELETE " + username + " " + hashed_password
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "delete-success":
            print(format["BGREEN"] + "\nAccount deleted successfully..." + format["END"])
        elif response == "delete-account-not-exist":
            print(format["BRED"] + "\nAccount does not exist..." + format["END"])
        elif response == "delete-online":
            print(format["BRED"] + "\nAccount is already online so we can't delete it now\nTry again later..." + format["END"])
        elif response == "delete-wrong-password":
            print(format["BRED"] + "\nWrong password..." + format["END"])
    ###################################################################
    
    
    # create room function
    def createRoom(self, roomname, password):
        hashed_password = self.dataHashed(password)
        message = "CREATEROOM " + roomname + " " + hashed_password
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "room-created":
            print(format["BGREEN"] + "\nRoom created..." + format["END"])
            self.joinRoom(roomname, password)
        elif response == "room-exist":
            print(format["BRED"] + "\nChoose another roomname" + format["END"])
    ###################################################################
    
    
    # join room function
    def joinRoom(self, roomname, password):
        hashed_password = self.dataHashed(password)
        message = "JOINROOM " + roomname + " " + hashed_password
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "room-joined":
            print(format["BGREEN"] + "\nRoom joined successfully..." + format["END"])
        elif response == "room-not-exist":
            print(format["BRED"] + "\nRoom does not exist..." + format["END"])
        elif response == "room-wrong-password":
            print(format["BRED"] + "\nWrong password..." + format["END"])
    ###################################################################
    
    
    # show my rooms function
    def showRooms(self):
        message = "SHOWROOMS"
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "no-rooms":
            print(format["BRED"] + "\nYou didn't join any room yet" + format["END"])
            return 0
        else:
            Rooms = ast.literal_eval(response)
            print("           Rooms")
            for index, room in enumerate(Rooms, start=1):
                print(f"[{index}] {room['roomname']}")
            return 1
    ###################################################################
    
    
    # enter room function
    def enterRoom(self, roomname):
        message = "ENTERROOM " + roomname
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "valid-room":
            members = self.roomMembers(roomname)    # retrieve room members
            if members:
                roomMembers = ast.literal_eval(members)
                print("\nRoom Members")
                for member in roomMembers:
                    print(member["username"])
            print("_____________________________________________________")
            self.sendRoomMessage(roomname)
        elif response == "invalid-room":
            print(format["BRED"] + "\nYou don't have access to this room" + format["END"])
        elif response == "room-not-exist":
            print(format["BRED"] + "\nRoom does not exist..." + format["END"])        
    ###################################################################
    
    
    # enter room function
    def exitRoom(self, roomname):
        message = "EXITROOM " + roomname
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        print(format["BRED"] + "\nYou quit" + format["END"])
    ###################################################################
    
    
    # send message function
    def sendRoomMessage(self, roomname):
        print("\n                        Chat")
        self.peerServer.isRoomRequested = 1
        while 1:
            msg = input()
            members = self.onlineRoomMembers(roomname)
            if members:
                roomMembers = ast.literal_eval(members)
                for member in roomMembers:
                    cred = self.searchUser(member["username"])
                    if cred != 0 and cred != None:
                        memberCred = cred.split(':')
                        ip = memberCred[0]
                        port = memberCred[1]
                        msgSocket = socket(AF_INET, SOCK_STREAM)
                        msgSocket.connect((ip, int(port)))
                        message = self.loginCredentials[0] + " " + msg
                        logging.info("Send to " + ip + ":" + port + " -> " + message)
                        msgSocket.send(message.encode())
                        msgSocket.close()
            if msg == ":q":
                self.exitRoom(roomname)
                self.peerServer.isRoomRequested = 0
                break
    ###################################################################
    
    
    # search room members
    def roomMembers(self, roomname):
        message = "SEARCHROOM " + roomname
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        if response == "room-empty":
            print(format["BGREEN"] + "\nRoom is empty" + format["END"])
            return 0
        else:
            return response
    ###################################################################
    
    # search room members
    def onlineRoomMembers(self, roomname):
        message = "SEARCHROOMONLINE " + roomname
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        if response == "room-empty":
            print(format["BRED"] + "\nno members online\n" + format["END"])
            return 0
        else:
            return response
    ###################################################################


    # delete room function
    def deleteRoom(self, roomname, password):
        hashed_password = self.dataHashed(password)
        message = "DELETEROOM " + roomname + " " + hashed_password
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "room-deleted":
            print(format["BGREEN"] + "\nRoom Deleted..." + format["END"])
        elif response == "room-not-exist":
            print(format["BRED"] + "\nRoom doesn't exist" + format["END"])
        elif response == "room-wrong-password":
            print(format["BRED"] + "\nIncorrect password" + format["END"])
        elif response == "not-creator":
            print(format["BRED"] + "\nYou can't delete the room because you aren't the owner" + format["END"])
    ###################################################################
    
    
    # leave room function
    def leaveRoom(self, roomname):
        message = "LEAVEROOM " + roomname
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "room-leaved":
            print(format["BGREEN"] + "\nRoom Left..." + format["END"])
        elif response == "room-not-exist":
            print(format["BRED"] + "\nRoom doesn't exist" + format["END"])
        elif response == "not-member":
            print(format["BRED"] + "\nYou can't leave the room because you didn't join" + format["END"])
    ###################################################################
    
    
    # function for sending hello message
    # a timer thread is used to send hello messages to udp socket of registry
    def sendHelloMessage(self):
        message = "HELLO " + self.loginCredentials[0]
        logging.info("Send to " + self.registryName + ":" + str(self.registryUDPPort) + " -> " + message)
        self.udpClientSocket.sendto(message.encode(), (self.registryName, self.registryUDPPort))
        self.timer = threading.Timer(1, self.sendHelloMessage)
        self.timer.start()
##########################################################################################################################################



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
    
    "CYAN": "\033[36m",
    "BCYAN": "\033[36;1m",
    
    "BOLD": "\033[1m",
    "END": "\033[0m",
}
# peer is started
main = peerMain()