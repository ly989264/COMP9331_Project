# Python version: 3.7

import os
from socket import *
import sys
import re
import datetime
import time
import random
# from multiprocessing import Pool
# from multiprocessing.dummy import Pool as ThreadPool
# from _thread import *
import threading

# design:
# ping request message format: PING REQUEST FROM_PORT                                                      (UDP)
# ping response message format: PING RESPONSE FROM_PORT                                                    (UDP)
# request the first successor from another peer: SUCCESSOR REQUEST FROM_PORT                               (TCP)
# response the first successor from another peer: SUCCESSOR RESPONSE FROM_PORT RESULT_PORT                 (TCP)
# request for graceful leave: LEAVE FROM_PORT FIRST_OF_MINE SECOND_OF_MINE                                 (TCP)
# response for graceful leave: BYE FROM_PORT                                                               (TCP)
# request for file format: FILE REQUEST FILENUM HASHED_FILENUM INITIAL_PORTNUM FROM_PORTNUM                (TCP)
# response for the file from the file owner to the initial requester: FILE FOUND FILENUM FROM_PORT         (TCP)

# configurations
ServerName = '127.0.0.1'
PingTimeOut = 0.1  # s (need to modify whether this is suitable)
PingTimeInterval = 15  # s (need to modify whether this is suitable)
MaxPingNoResponseNum = 4
start_time = time.time()
send_logfile = "responding_log.txt"
receive_logfile = "requesting_log.txt"
diff = 50000

# variables represent the status of this peer
# basic status
if len(sys.argv) < 6:
    print("No enough command arguments.")
    sys.exit()
self_port = diff + int(sys.argv[1])
successor_port = [diff + int(sys.argv[2]), diff + int(sys.argv[3])]
predecessor_port = {}  # key: portnum, value: status(0 or 1)
# in which the status is 1 if recently received ping from it, 0 otherwise
MSS = int(sys.argv[4])
drop_rate = float(sys.argv[5])
# special status
ping_no_response = 0  # the number of no response ping received question: do i need to remember no response ping from where?
successor_no_response = None  # 0 is the first one and 1 is the second one
new_successor_port_get = None
event = threading.Event()  # the event to handle special cases
# status to stop the thread
central_ping_status = 1  # check whether to reuse or not
central_udp_server_status = 1  # check whether to reuse or not
central_tcp_server_status = 1  # check whether to reuse or not


def hash_function(int_value):
    # In this case, the filename is an integer in [0,9999]
    return int_value % 256


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
        print(f"A ping request message was received from Peer {from_port_num-diff}.")
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
                    with open(receive_logfile, "a") as fw:
                        print(f"rcv {current_time-start_time} {int(message[0:32].decode())} {len(message[64:])} 0", file=fw)
                        temp = int(message[0:32].decode())
                        current_time = time.time()
                        if temp==seq:
                            total += message[64:]
                            seq+=len(message[64:])
                            response_message = "SUCCESS "+str(seq)
                            print(f"snd {current_time-start_time} 0 {len(message[64:])} {seq}", file=fw)
                        else:
                            response_message = "SUCCESS "+str(seq)
                            print(f"snd {current_time-start_time} 0 {len(message[64:])} {seq}", file=fw)
                        self.serverSocket.sendto(response_message.encode(), clientAddress)
                else:
                    continue
            except Exception:
                if message[0:32].decode().startswith("000"):
                    with open(receive_logfile, "a") as fw:
                        temp = int(message[0:32].decode())
                        if temp == seq:
                            total += message[64:]
                            seq += len(message[64:])
                            response_message = "SUCCESS " + str(seq)
                            print(f"snd {current_time-start_time} 0 {len(message[64:])} {seq}", file=fw)
                        else:
                            response_message = "SUCCESS " + str(seq)
                            print(f"snd {current_time-start_time} 0 {len(message[64:])} {seq}", file=fw)
                        self.serverSocket.sendto(response_message.encode(), clientAddress)
        # self.serverSocket.shutdown(SHUT_RDWR)# modified, new added
        self.serverSocket.close()#modified, new added

        # print("UDP_Server_Thread closed.")


# class ping_no_response_exception


class UDP_Client_Thread(threading.Thread):  # used to send ping messages
    # already: implement the single ping process, and set the event if there is no response for continuous four times
    # improve: find proper value of the time interval, the number of times when no response, and the timeout
    def __init__(self, from_port_num, target_port_num):
        threading.Thread.__init__(self)
        global PingTimeInterval
        self.from_port_num = int(from_port_num)
        self.target_port_num = int(target_port_num)
        self.clientSocket = socket(AF_INET, SOCK_DGRAM)
        self.time_interval = PingTimeInterval

    def generate_ping_request_message(self):  # design the message format myself
        ping_request_message = 'PING REQUEST '+str(self.from_port_num)
        return ping_request_message

    def ping(self):
        global PingTimeOut
        self.clientSocket.settimeout(PingTimeOut)
        request_message = self.generate_ping_request_message()
        try:
            self.clientSocket.sendto(request_message.encode(), (ServerName, self.target_port_num))
            response_message, serverAddress = self.clientSocket.recvfrom(2048)  # check the size of buffer
            response_message = response_message.decode()
            # what if the response_message is None
            if response_message:
                if int(response_message.split(" ")[2]) != self.target_port_num:  # this situation should not occur
                    print("Something wrong with the ping response.")
                    sys.exit()
            # print the result to the output
            print(f"A ping response message was received from Peer {self.target_port_num-diff}.")
        except timeout:
            print(f"Time out, no ping response from Peer {self.target_port_num-diff}.")
            # self.clientSocket.close()
            global ping_no_response
            global successor_no_response
            global MaxPingNoResponseNum
            ping_no_response += 1
            if ping_no_response >= MaxPingNoResponseNum:
                event.set()
                if self.target_port_num == successor_port[0]:
                    successor_no_response = 0
                elif self.target_port_num == successor_port[1]:
                    successor_no_response = 1
                else:
                    print("Something wrong with success_no_response.")
                print(f"Peer {self.target_port_num-diff} is no longer alive.")
                ping_no_response = 0
        # self.clientSocket.shutdown(SHUT_RDWR)  # modified, new added
        self.clientSocket.close()# modified, new added
        return

    def run(self):
        # print("UDP_Client_Thread open.")
        self.ping()
        # print("UDP_Client_Thread closed.")
        return

class UDP_File_Sender_Thread(threading.Thread):
    # already: send the file
    def __init__(self, port_num, target_port, filenum, filename):
        threading.Thread.__init__(self)
        self.port_num = int(port_num)
        self.target_port = int(target_port)
        self.filenum = filenum###################change at 0426
        # question: the hashed filenum?
        self.filename = filename
        self.sender_socket = socket(AF_INET, SOCK_DGRAM)
    def run(self):
        # new added print statement for file transfer
        print("We now start sending the file .........")
        with open(send_logfile, "w") as wf:
            cnt = 0
            flag = 0
            seq = 1
            current_message = None
            else_message = None
            second_else_message = None
            final_message = None
            finish_flag = 0
            self.sender_socket.settimeout(1.0)  # set timeout of 1.0 second
            with open(self.filename, "rb") as f:
                message = f.read()
                # change the cnt to seq, < to <=, and remove the finish_flag
                while seq<=len(message):
                    if not flag:
                        final_message = b""
                        else_message = f"{seq:032d}".encode()
                        second_else_message = f"{0:032d}".encode()
                        current_message = message[cnt:cnt+MSS]
                        cnt = cnt + len(current_message)#modified
                        # question: should the MSS include these 64 bits?
                        final_message += else_message
                        final_message += second_else_message
                        final_message += current_message
                    try:
                        random_num = random.uniform(0,1)#modified random to uniform
                        # question: random.random() or random.uniform(0,1)?
                        current_time = time.time()
                        if flag and random_num < drop_rate:  ########
                            print(f"RTX/Drop {current_time - start_time} {seq} {len(current_message)} 0", file=wf)  #########
                            continue  ############
                        if random_num >= drop_rate:
                            if not flag:
                                print(f"snd {current_time-start_time} {seq} {len(current_message)} 0", file=wf)
                            else:
                                print(f"RTX {current_time-start_time} {seq} {len(current_message)} 0", file=wf)
                            self.sender_socket.sendto(final_message, (ServerName, self.target_port))
                            response, receiverAddress = self.sender_socket.recvfrom(2048)
                            current_time = time.time()
                            # todo: probability and logfile
                            if not response:
                                raise Exception
                            response = response.decode()
                            if response.startswith("SUCCESS"):
                                if int(response.split(" ")[1])==(cnt+1):
                                    # fix the bug here
                                    print(f"rcv {current_time-start_time} 0 {cnt+1-seq} {response.split(' ')[1]}", file=wf)
                                    flag = 0
                                    seq += len(current_message)
                        else:
                            print(f"drop {current_time-start_time} {seq} {len(current_message)} 0", file=wf)
                            raise Exception
                    except:
                        flag = 1
                        continue
                end_message = "END"
                self.sender_socket.sendto(end_message.encode(), (ServerName, self.target_port))
        # self.sender_socket.shutdown(SHUT_RDWR)  # modified, new added
        self.sender_socket.close()# modified
        # new added print statement for the finish of the file transfer
        print("The file is sent.")


# this function is used to get the larger predecessor, but avoid the condition like 15 and 1
# new added
def get_direct_larger_predecessor():
    global predecessor_port
    global self_port
    if max(predecessor_port.keys()) > self_port:
        return min(predecessor_port.keys())
    else:
        return max(predecessor_port.keys())

class TCP_Certain_Server_Thread(threading.Thread):
    # mode: 1(SUCCESSOR RESPONSE) 2(BYE) 3(FILE REQUEST)
    # already: implement the mode 1, that is, respond to a SUCCESSOR REQUEST
    # already: implement the mode 2, that is, respond to a LEAVE request and modify the successors
    # already: implement the mode 3, that is, respond to a FILE REQUEST message
    # improve: add more modes
    def __init__(self, connectionSocket, port_num, target_port, mode, leave_port, first_succ_of_leave, sec_suc_of_leave, filenum, hashed_filenum, initial_portnum):
        threading.Thread.__init__(self)
        self.connectionSocket = connectionSocket
        self.port_num = int(port_num)
        self.target_port = int(target_port)
        self.mode = int(mode)
        if self.mode == 2:
            self.leave_port = int(leave_port)
            self.first_succ_of_leave = int(first_succ_of_leave)
            self.sec_suc_of_leave = int(sec_suc_of_leave)
        if self.mode == 3:
            self.filenum = filenum
            self.hashed_filenum = hashed_filenum
            self.initial_portnum = initial_portnum

    def run(self):
        # print("TCP_Certain_Server_Thread open.")
        global self_port
        global successor_port
        if self.mode == 1:
            response_message = "SUCCESSOR RESPONSE " + str(self.port_num) + " " + str(successor_port[0])
            self.connectionSocket.send(response_message.encode())
            self.connectionSocket.close()
        elif self.mode == 2:
            if self.leave_port == successor_port[0]:
                successor_port[0]=self.first_succ_of_leave
                successor_port[1]=self.sec_suc_of_leave
            elif self.leave_port == successor_port[1]:
                successor_port[1]=self.first_succ_of_leave
            else:
                print("Something wrong with receiving of the leave message.")
            print(f"Peer {self.leave_port-diff} will depart from the network.")
            print(f"My first successor is now peer {successor_port[0]-diff}.")
            print(f"My second successor is now peer {successor_port[1]-diff}.")
            response_message = "BYE "+str(self.port_num)
            self.connectionSocket.send(response_message.encode())
            self.connectionSocket.close()
            # need to start ping two successors, new added
            # question: testing!
            new_ping_v2 = UDP_Client_Thread(self_port, successor_port[0])
            new_ping_v2.start()
            new_ping_v2.join()
            new_ping_v2 = UDP_Client_Thread(self_port, successor_port[1])
            new_ping_v2.start()
            new_ping_v2.join()
        elif self.mode == 3:
            self.connectionSocket.close()
            # check whether the file is on my place
            # modified here, change the judge statement of the file location
            # get the largest predecessor
            largest_predecessor = get_direct_larger_predecessor()
            # question: testing for the new condition!
            if self.hashed_filenum == (self_port - diff) or ((largest_predecessor-diff) < self.hashed_filenum < (self_port - diff)) or (largest_predecessor>self_port and ((largest_predecessor-diff)<self.hashed_filenum<(self_port+256-diff))):
                # file is here
                print(f"File {self.filenum} is here.")
                # need to response to the initial peer using TCP
                file_final_response_thread = TCP_Client_Thread(self_port, self.initial_portnum, 4, self.filenum, self.initial_portnum)
                file_final_response_thread.start()
                file_final_response_thread.join()
                print(f"A response message, destined for peer {self.initial_portnum-diff}, has been sent.")
                # todo: start transferring the file
                filename = self.filenum+".pdf"###################change at 0426
                transfer_thread = UDP_File_Sender_Thread(self_port, self.initial_portnum, self.filenum, filename)
                transfer_thread.start()
            else:
                # the file is not here
                # then send the request message to the successor, greedy
                print(f"File {self.filenum} is not stored here.")
                file_passer_request_thread = TCP_Client_Thread(self_port, successor_port[0], 3, self.filenum,
                                                               self.initial_portnum)
                file_passer_request_thread.start()
                file_passer_request_thread.join()
                print(f"File request message has been forwared to my successor.")
        else:# new added
            self.connectionSocket.close()
        # print("TCP_Certain_Server_Thread closed.")


class TCP_Server_Thread(threading.Thread):
    # already: Multiple client listening, handle for successor request, handle for leave, handle for file request
    # todo: need to add methods to respond to certain modes, such as successor request and so on
    def __init__(self, port_num):
        threading.Thread.__init__(self)
        self.port_num = int(port_num)
        self.serverSocket = socket(AF_INET, SOCK_STREAM)
        self.serverSocket.bind(('', port_num))

    def run(self):# need to modify
        # print("TCP_Server_Thread open.")
        self.serverSocket.listen(5)
        global central_tcp_server_status
        while True:
            if not central_tcp_server_status:  # if central_tcp_server_status changed to 0, quit the thread
                break
            connectionSocket, addr = self.serverSocket.accept()
            try:
                message = connectionSocket.recv(1024)
                # what if message is None
                if message:
                    message = message.decode()# change the position of decode()
                    # print("Special**************", end='')
                    # print(message)
                    # target_port_num = int(message.split(" ")[2])#question here
                    if message.startswith("SUCCESSOR REQUEST"):
                        target_port_num = int(message.split(" ")[2])
                        current_working_thread = TCP_Certain_Server_Thread(connectionSocket, self.port_num, target_port_num, 1, None, None, None, None, None, None)
                        current_working_thread.start()
                        # current_working_thread.join()# new added
                    elif message.startswith("LEAVE"):
                        target_port_num = int(message.split(" ")[1])
                        first_succ = int(message.split(" ")[2])
                        sec_succ = int(message.split(" ")[3])
                        leave_port = int(message.split(" ")[1])
                        current_working_thread = TCP_Certain_Server_Thread(connectionSocket, self.port_num, target_port_num, 2, leave_port, first_succ, sec_succ, None, None, None)
                        current_working_thread.start()
                        # current_working_thread.join()# new added
                    elif message.startswith("FILE REQUEST"):
                        target_port_num = int(message.split(" ")[5])# not the initial request port
                        # FILE REQUEST FILENUM HASHED_FILENUM INITIAL_PORTNUM FROM_PORTNUM
                        filenum = message.split(" ")[2]###################change at 0426
                        hashed_filenum = int(message.split(" ")[3])
                        initial_portnum = int(message.split(" ")[4])
                        current_working_thread = TCP_Certain_Server_Thread(connectionSocket, self.port_num, target_port_num, 3, None, None, None, filenum, hashed_filenum, initial_portnum)
                        current_working_thread.start()
                        # current_working_thread.join()# new added
                    elif message.startswith("FILE FOUND"):
                        from_port_num = int(message.split(" ")[3])
                        filenum = message.split(" ")[2]###################change at 0426
                        connectionSocket.close()
                        # new added print statements
                        print(f"Received a response message from peer {from_port_num-diff}, which has the file {filenum}.")
                        print("We now start receiving the file .........")
                    else:# receive other types of message
                        # although no need to reply or operate, still need to close the socket
                        connectionSocket.close()
            except ConnectionResetError:
                print("Testing... ConnectionResetError occurs.")
                connectionSocket.close()
        # print("TCP_Server_Thread closed.")


class TCP_Client_Thread(threading.Thread):
    # already: implement one peer connecting the other peer to get its first successor and save it as new_successor_port
    # already: graceful leave request send
    # already: file request
    # already: file found reply directly to the requester
    # improve: add a mode argument and other arguments that may be used in certain mode
    # mode: 1(SUCCESSOR REQUEST), 2(LEAVE), 3(FILE REQUEST)(initial, from user), 4(FILE FOUND)
    def __init__(self, port_num, target_port_num, mode, filenum, initialport):# add a new parameter called mode, so this can deal with different modes
        threading.Thread.__init__(self)
        self.clientSocket = socket(AF_INET, SOCK_STREAM)
        self.port_num = int(port_num)# this should be the self-portnum
        self.target_port_num = int(target_port_num)
        self.mode = int(mode)
        # actually I think I can set no matter the mode
        # if self.mode == 3:
        #     self.filenum = filenum
        #     self.initialport = initialport
        # if self.mode == 4:
        #     self.filenum = filenum
        #     self.initialport = initialport
        self.filenum = filenum
        self.initialport = initialport
        return

    def generate_successor_request_message(self):
        message = "SUCCESSOR REQUEST "+str(self.port_num)
        return message

    def generate_leave_request_message(self):
        global successor_port
        message = "LEAVE "+ str(self_port) + " " + str(successor_port[0]) + " " + str(successor_port[1])
        return message

    def generate_file_request_message(self):
        # FILE REQUEST FILENUM HASHED_FILENUM INITIAL_PORTNUM FROM_PORTNUM
        ###################change at 0426
        message = "FILE REQUEST "+self.filenum+" "+str(self.hashed_filenum)+" "+str(self.initialport)+" "+str(self.port_num)#modified to self.port_num
        return message

    def run(self):
        # print("TCP_Client_Thread open.")
        if self.mode == 1:
            self.clientSocket.connect((ServerName, self.target_port_num))
            request_message = self.generate_successor_request_message()
            self.clientSocket.send(request_message.encode())
            response_message = self.clientSocket.recv(1024)
            # what if response_message is None
            if not response_message:
                print("The response message from tcp client thread is empty.")
                while not response_message:# new added, to see whether this works
                    print("Rerequesting...")
                    self.clientSocket.send(request_message.encode())
                    response_message = self.clientSocket.recv(1024)
            else:
                response_message = response_message.decode()
                result_port = int(response_message.split(" ")[3])
                global new_successor_port_get
                new_successor_port_get = result_port
        elif self.mode == 2:
            # a potential question: after one peer quit, the predecessor list of its successors does not update
            self.clientSocket.connect((ServerName, self.target_port_num))
            request_message = self.generate_leave_request_message()
            self.clientSocket.send(request_message.encode())
            # response_message = self.clientSocket.recv(1024).decode()
            # if response_message:
            #     if not response_message.startswith("BYE"):
            #         print("Response message wrong with the leave request.")
            response_message = self.clientSocket.recv(1024)
            # need to make sure that the BYE message is received, new added here
            # question: testing!!!
            while True:
                if response_message:
                    if response_message.decode().startswith("BYE"):
                        break
                self.clientSocket.send(request_message.encode())
                response_message = self.clientSocket.recv(1024)
        elif self.mode == 3:
            # safely assume the file requested is not on the peer who raises the request
            self.hashed_filenum = hash_function(int(self.filenum))###################change at 0426
            request_message = self.generate_file_request_message()
            # modify here, always contact the first successor
            global successor_port
            self.clientSocket.connect((ServerName, successor_port[0]))
            self.clientSocket.send(request_message.encode())
            # modified here, delete the print statement and move it to the main function
            # print(f"File request message for {self.filenum} has been sent to my successor.")
            # # greedy, contact the second successor if possible
            # global successor_port
            # if self.hashed_filenum >= (successor_port[1]-diff):
            #     #send to the second successor
            #     self.clientSocket.connect((ServerName, successor_port[1]))
            #     self.clientSocket.send(request_message.encode())
            #     # response_message = self.clientSocket.recv(1024).decode() #test
            # else:
            #     #send to the first successor
            #     self.clientSocket.connect((ServerName, successor_port[0]))
            #     self.clientSocket.send(request_message.encode())
            #     # response_message = self.clientSocket.recv(1024).decode()#test
            # print(f"File request message for {self.filenum} has been sent to my successor.")

        elif self.mode == 4:
            # FILE FOUND FILENUM FROM_PORT
            request_message = "FILE FOUND "+self.filenum+" "+str(self.port_num)###################change at 0426
            self.clientSocket.connect((ServerName, self.target_port_num))
            self.clientSocket.send(request_message.encode())
            # response_message = self.clientSocket.recv(1024).decode()#test
        self.clientSocket.close()
        # print("TCP_Client_Thread closed.")
        return


class ping_thread(threading.Thread):
    # already: create a thread class that can regularly ping two successors and deal with sudden leave situation
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        # print("Ping_Thread open.")
        global central_ping_status
        global successor_no_response
        global new_successor_port_get
        while True:
            if not central_ping_status:  # when the central_ping_status changed to 0, quit the thread
                break
            new_ping = UDP_Client_Thread(self_port, successor_port[0])
            new_ping.start()
            new_ping.join()
            new_ping = UDP_Client_Thread(self_port, successor_port[1])
            new_ping.start()
            new_ping.join()
            if event.is_set():
                # if first successor is dead, then set the second successor as its first successor
                # then send a message through TCP to get the first successor of the new first successor
                # and set the result as the second successor
                if successor_no_response == 0:
                    successor_port[0]=successor_port[1]
                    request_thread_v1 = TCP_Client_Thread(self_port, successor_port[0], 1, None, None)
                    request_thread_v1.start()
                    request_thread_v1.join()
                    successor_port[1]=int(new_successor_port_get)
                # if the second successor is dead, then send the first successor what the first successor is
                # if the result is the same as the second successor, wait an interval and ask again
                # update the second successor
                else:
                    request_thread_v1 = TCP_Client_Thread(self_port, successor_port[0], 1, None, None)
                    request_thread_v1.start()
                    request_thread_v1.join()
                    while new_successor_port_get == successor_port[1]:
                        time.sleep(PingTimeInterval)
                        request_thread_v1 = TCP_Client_Thread(self_port, successor_port[0], 1, None, None)
                        request_thread_v1.start()
                        request_thread_v1.join()
                    successor_port[1]=int(new_successor_port_get)
                print(f"My first successor is now peer {successor_port[0]-diff}.")
                print(f"My second successor is now peer {successor_port[1]-diff}.")
                # need to ping two successors immediately, new added
                # question: testing!
                new_ping_v3 = UDP_Client_Thread(self_port, successor_port[0])
                new_ping_v3.start()
                new_ping_v3.join()
                new_ping_v3 = UDP_Client_Thread(self_port, successor_port[1])
                new_ping_v3.start()
                new_ping_v3.join()
                event.clear()
            # time.sleep(PingTimeInterval)
            # replaced by the for loop below, and exchange the position
            for sleep_interval in range(PingTimeInterval * 5):
                time.sleep(0.2)
                if not central_ping_status:
                    break
        # print("Ping_Thread closed.")

# quit directly
# new-added
def quit_procedure():
    # gracefully quit
    # tcp_client_for_leave = TCP_Client_Thread(self_port, predecessor_port[0][0], 2, None, None)
    # tcp_client_for_leave.start()
    # tcp_client_for_leave.join()
    # tcp_client_for_leave = TCP_Client_Thread(self_port, predecessor_port[1][0], 2, None, None)
    # tcp_client_for_leave.start()
    # tcp_client_for_leave.join()
    # modified by the following for loop
    for each_key in predecessor_port.keys():
        tcp_client_for_leave = TCP_Client_Thread(self_port, each_key, 2, None, None)
        tcp_client_for_leave.start()
        tcp_client_for_leave.join()
    global central_ping_status
    global central_udp_server_status
    global central_tcp_server_status
    central_ping_status = 0  # used to stop the ping thread
    central_udp_server_status = 0  # used to stop the udp server thread, first half process
    central_tcp_server_status = 0  # used to stop the tcp server thread, first half process
    temp_socket = socket(AF_INET, SOCK_DGRAM)
    temp_socket.sendto(" ".encode(), (ServerName, self_port))
    temp_socket.close()  # second half process to stop the udp server thread
    temp_socket = socket(AF_INET, SOCK_STREAM)
    temp_socket.connect((ServerName, self_port))
    temp_socket.send(" ".encode())
    temp_socket.close()  # second half process to stop the tcp server thread
    sys.exit()  # still need?

ping = ping_thread()
ping.start()  # start to ping others
udp_server = UDP_Server_Thread(self_port)
udp_server.start()  # start to listen to UDP messages
tcp_server = TCP_Server_Thread(self_port)
tcp_server.start()  # start to listen to TCP messages
# todo: get input from the user
while True:
    input_message = input()
    if input_message == "quit":
        quit_procedure()
    elif input_message.startswith("request"):
        # assume the input message format is correct
        filenum = input_message.split(" ")[1]###################change at 0426
        file_request_thread = TCP_Client_Thread(self_port, successor_port[0], 3, filenum, self_port)
        print(f"File request message for {filenum} has been sent to my successor.")  # new added
        file_request_thread.start()

# BY YU LIU, z5190675