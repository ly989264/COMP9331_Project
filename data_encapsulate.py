import time
import os
from socket import *
import random

MSS = 300
drop_prob = 0.5
sender_socket = socket(AF_INET, SOCK_DGRAM)
cnt = 0
current_message = None
else_message = None
final_message = None
second_else_message = None
seq = 1
flag = 0
finish_flag = 0
sender_socket.settimeout(1.0)
with open("2012.pdf", "rb") as f:
    message = f.read()
    print(len(message))
    while cnt<len(message) and not finish_flag:
        print(cnt, flag, sep=" ")
        if not flag:
            final_message = b""
            else_message = f"{seq:032d}".encode()
            second_else_message = f"{0:032d}".encode()
            current_message = message[cnt:cnt+MSS]
            cnt = cnt+MSS
            final_message+=else_message
            final_message+=second_else_message
            final_message+=current_message
        try:
            random_num = random.random()
            print(random_num)
            start_time = time.time()
            if random_num>=drop_prob:
                if not flag:
                    print(f"snd {seq} {len(current_message)} 0")
                else:
                    print(f"RTX {seq} {len(current_message)} 0")
                sender_socket.sendto(final_message, ('127.0.0.1', 12321))
                response, receiverAddress = sender_socket.recvfrom(2048)
                if not response:
                    raise Exception
                response = response.decode()
                if response.startswith("SUCCESS"):
                    if int(response.split(" ")[1])==(cnt+1):
                        flag = 0
                        seq+=len(current_message)
                        if seq>=len(message):
                            finish_flag = 1
            else:
                print(f"drop {seq} {len(current_message)} 0")
                raise Exception
        except:
            flag = 1
            continue
    print(cnt)
    end_message = "END"
    sender_socket.sendto(end_message.encode(), ('127.0.0.1', 12321))
    sender_socket.close()
