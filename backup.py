import os
from socket import *
import sys
import re
import datetime
import time
# from multiprocessing import Pool
# from multiprocessing.dummy import Pool as ThreadPool
# from _thread import *
import threading

# design:
# ping request message format: PING REQUEST FROM_PORT
# ping response message format: PING RESPONSE FROM_PORT

ServerName = '127.0.0.1'
PingTimeOut = 0.1  # s (need to modify whether this is suitable)
PingTimeInterval = 5  # s (need to modify whether this is suitable)

predecessor_identity = []  # the first is smaller than the second


def hash_function(string):
    # In this case, the filename is an integer in [0,9999]
    int_value = int(string)
    return int_value % 256


def get_command_argument():
    if len(sys.argv) < 6:
        print("No enough command arguments.")
        sys.exit()
    return int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])


class UDP_Server_Thread(threading.Thread):
    def __init__(self, port_num):
        threading.Thread.__init__(self)
        self.port_num = int(port_num)
        self.serverSocket = socket(AF_INET, SOCK_DGRAM)
        self.serverSocket.bind(('', self.port_num))

    def ping_message_modification(self, ping_request_message):
        from_port_num = int(ping_request_message.split(" ")[2])
        print(f"A ping request message was received from Peer {from_port_num}.")
        response_message = "PING RESPONSE " + str(self.port_num)
        # mechanism of updating the predecessor:
        # predecessor_identity is consist of two lists, each with the format [port_num, flag]
        # in which the port with the flag value 1 is the latest added
        # and the port with the flag value 0 is added earlier
        # each time when get a new port, first check whether the port is already in the list
        # if so, then set the flag of that port to 1 and another to 0
        # if not, then delete the port with the flag 0,
        #   change the other one's flag to 0 and append it to the list with flag 1
        # then sort the list
        if len(predecessor_identity) < 2:
            predecessor_identity.append([from_port_num, 1])
            if len(predecessor_identity) == 2:
                predecessor_identity[0][1] = 0
            predecessor_identity.sort(key=lambda x: x[0])
        else:
            for each_pair in predecessor_identity:
                if each_pair[1] == 0:
                    each_pair[0] = from_port_num
                    each_pair[1] = 1
                else:
                    each_pair[1] = 0
            predecessor_identity.sort(key=lambda x: x[0])
        return response_message

    def run(self):  # need to modify
        while True:
            message, clientAddress = self.serverSocket.recvfrom(1024)
            message = message.decode()
            if message.startswith("PING REQUEST"):  # if the message received is ping request
                modified_message = self.ping_message_modification(message)
            # note that there are many other kinds of messages
            self.serverSocket.sendto(modified_message.encode(), clientAddress)


class UDP_Client_Thread(threading.Thread):  # used to send ping messages
    def __init__(self, from_port_num, target_port_num):
        threading.Thread.__init__(self)
        self.from_port_num = int(from_port_num)
        self.target_port_num = int(target_port_num)
        self.clientSocket = socket(AF_INET, SOCK_DGRAM)
        self.time_interval = PingTimeInterval

    def generate_ping_request_message(self):  # design the message format myself
        ping_request_message = 'PING REQUEST ' + str(self.from_port_num)
        return ping_request_message

    def ping(self):
        self.clientSocket.settimeout(PingTimeOut)
        request_message = self.generate_ping_request_message()
        try:
            self.clientSocket.sendto(request_message.encode(), (ServerName, self.target_port_num))
            response_message, serverAddress = self.clientSocket.recvfrom(2048)  # check the size of buffer
            response_message = response_message.decode()
            if int(response_message.split(" ")[2]) != self.target_port_num:  # this situation should not occur
                print("Something wrong with the ping response.")
                sys.exit()
            # print the result to the output
            print(f"A ping response message was received from Peer {self.target_port_num}.")
            self.clientSocket.close()
            return 1
        except:
            print(f"Time out, no ping response from Peer {self.target_port_num}.")
            self.clientSocket.close()
            return 0
        return

    def run(self):
        status = self.ping()
        return status


class TCP_Server_Thread(threading.Thread):
    def __init__(self, port_num):
        threading.Thread.__init__(self)
        self.serverSocket = socket(AF_INET, SOCK_STREAM)
        self.serverSocket.bind(('', port_num))

    def run(self):  # need to modify
        self.serverSocket.listen(1)
        while True:
            connectionSocket, addr = self.serverSocket.accept()
            print(f"Get TCP connection from {addr}.")
            message = connectionSocket.recv(1024).decode()
            modified_message = message.upper()
            connectionSocket.send(modified_message.encode())
            connectionSocket.close()


class DHT:
    def __init__(self, a, b, c, d, e):
        self.self_identity = a
        self.successor_identity = [b, c]
        self.MSS = d
        self.drop_rate = e
        self.self_port = 50000 + self.self_identity
        self.successor_port = [50000 + self.successor_identity[0], 50000 + self.successor_identity[1]]

    def ping_successors(self):
        PingServer = UDP_Client_Thread(self.self_port, self.successor_port[0])
        PingServer.start()




