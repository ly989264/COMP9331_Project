import os
import sys
import time
from socket import *
import threading

start_time = time.time()
MSS = 300
central_udp_server_status = 1

class UDP_Server_Thread(threading.Thread):
    # already: respond to a ping request
    # already: respond to a file transfer udp process
    # improve: robust, try to make the program robust, really important
    def __init__(self, port_num):
        threading.Thread.__init__(self)
        self.port_num = int(port_num)
        self.serverSocket = socket(AF_INET, SOCK_DGRAM)
        self.serverSocket.bind(('', self.port_num))

    def ping_message_modification(self, ping_request_message):
        from_port_num = int(ping_request_message.split(" ")[2])
        print(f"A ping request message was received from Peer {from_port_num-50000}.")
        response_message = "PING RESPONSE " + str(self.port_num)
        global predecessor_port
        # mechanism of updating the predecessor:
        # predecessor is a dictionary, with at most two pairs
        if len(predecessor_port) < 2:
            # predecessor_port.append([from_port_num, 1])
            predecessor_port[from_port_num] = 1  # no matter from_port_num already exists or not
            if len(predecessor_port) == 2:
                # predecessor_port[0][1]=0
                # predecessor_port.sort(key=lambda x: x[0])
                for each_key in predecessor_port.keys():
                    if each_key != from_port_num:
                        predecessor_port[each_key] = 0
        else:  # already two in the predecessor_port
            # if the from_port_num already in the predecessor_port
            if from_port_num in predecessor_port.keys():
                # then set the value of it to 1 and the other to 0
                predecessor_port[from_port_num] = 1
                for each_key in predecessor_port.keys():
                    if each_key != from_port_num:
                        predecessor_port[each_key] = 0
            else:  # the from_port_num not in the predecessor_port
                # delete the pair with the value of 0 in the predecessor_port
                # set the value of the pair with the value of 1 to 0
                # add the from_port_num in the predecessor_port with the value of 1
                to_del_key = None
                for each_key in predecessor_port.keys():
                    if predecessor_port[each_key] == 0:
                        to_del_key = each_key
                    elif predecessor_port[each_key] == 1:
                        predecessor_port[each_key] = 0
                    else:
                        # this should not happen, set this for debug use
                        print("Error 1354, for debug use.")
                if not to_del_key:
                    # this should no happen, set this for debug use
                    print("Error 1355, for debug use.")
                    sys.exit()
                del predecessor_port[to_del_key]
                predecessor_port[from_port_num] = 1
        return response_message

    def run(self):#need to modify
        global central_udp_server_status
        total = b""
        temp = None
        data = None
        seq = 1
        file_finish_flag = 0
        # print("UDP_Server_Thread open.")
        while True:
            if not central_udp_server_status:  # if the central_udp_server_status changed to 0, quit the thread
                break
            if file_finish_flag:
                with open("receive.pdf","wb") as f:
                    f.write(total)
                file_finish_flag = 0
                total = b""#modified, new added
                # new added print statement for the finish of the file transfer receive
                print("The file is received.")
            message, clientAddress = self.serverSocket.recvfrom(4000)
            current_time = time.time()
            try:
                temp = message[0:32].decode()
                # what if the message is None
                if temp.startswith("PING REQUEST"):  # if the message received is ping request
                    modified_message = self.ping_message_modification(temp)
                    self.serverSocket.sendto(modified_message.encode(), clientAddress)
                elif temp.startswith("END"):
                    file_finish_flag = 1
                    seq = 1# modified, new added
                    continue
                elif temp.startswith("000"):
                    print(f"rcv {current_time-start_time} {int(message[0:32].decode())} {len(message[64:])} 0")
                    temp = int(message[0:32].decode())
                    current_time = time.time()
                    if temp==seq:
                        total += message[64:]
                        seq+=len(message[64:])
                        response_message = "SUCCESS "+str(seq)
                        print(f"snd {current_time-start_time} 0 {len(message[64:])} {seq}")
                    else:
                        response_message = "SUCCESS "+str(seq)
                        print(f"snd {current_time-start_time} 0 {len(message[64:])} {seq}")
                    self.serverSocket.sendto(response_message.encode(), clientAddress)
                else:
                    continue
            except Exception:
                if message[0:32].decode().startswith("000"):
                    temp = int(message[0:32].decode())
                    if temp == seq:
                        total += message[64:]
                        seq += len(message[64:])
                        response_message = "SUCCESS " + str(seq)
                        print(f"snd {current_time-start_time} 0 {len(message[64:])} {seq}")
                    else:
                        response_message = "SUCCESS " + str(seq)
                        print(f"snd {current_time-start_time} 0 {len(message[64:])} {seq}")
                    self.serverSocket.sendto(response_message.encode(), clientAddress)
        # self.serverSocket.shutdown(SHUT_RDWR)# modified, new added
        self.serverSocket.close()#modified, new added
receiver = UDP_Server_Thread(50003)
receiver.start()
