import os
import time
import random
from socket import *
import threading

MSS = 300
start_time = time.time()
drop_rate = 0.85
ServerName = '127.0.0.1'


class UDP_File_Sender_Thread(threading.Thread):
    # already: send the file
    def __init__(self, port_num, target_port, filenum, filename):
        threading.Thread.__init__(self)
        self.port_num = int(port_num)
        self.target_port = int(target_port)
        self.filenum = int(filenum)
        # question: the hashed filenum?
        self.filename = filename
        self.sender_socket = socket(AF_INET, SOCK_DGRAM)
    def run(self):
        # new added print statement for file transfer
        print("We now start sending the file .........")
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
                    if flag and random_num < drop_rate:########
                        print(f"RTX/Drop {current_time - start_time} {seq} {len(current_message)} 0")#########
                        continue############
                    if random_num >= drop_rate:
                        if not flag:
                            print(f"snd {current_time-start_time} {seq} {len(current_message)} 0")
                        else:
                            print(f"RTX {current_time - start_time} {seq} {len(current_message)} 0")
                        self.sender_socket.sendto(final_message, (ServerName, self.target_port))
                        response, receiverAddress = self.sender_socket.recvfrom(2048)
                        current_time = time.time()
                        # todo: probability and logfile
                        if not response:
                            raise Exception
                        response = response.decode()
                        if response.startswith("SUCCESS"):
                            if int(response.split(" ")[1])==(cnt+1):
                                print(f"rcv {current_time-start_time} 0 {cnt+1-seq} {response.split(' ')[1]}")
                                flag = 0
                                seq += len(current_message)
                    else:
                        print(f"drop {current_time-start_time} {seq} {len(current_message)} 0")
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

filetransfer_client = UDP_File_Sender_Thread(50002, 50003, 2012, '2012.pdf')
filetransfer_client.start()
filetransfer_client.join()