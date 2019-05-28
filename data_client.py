import os
import time
import re
from socket import *

receiver_socket = socket(AF_INET, SOCK_DGRAM)
receiver_socket.bind(('', 12321))
start_time = time.time()
total = b""
temp = None
data = None
MSS=300
seq = 1
while True:
    message, clientAddress = receiver_socket.recvfrom(4000)
    current_time = time.time()
    try:
        temp = message.decode()
        if temp.startswith("END"):
            break
        print(f"rcv {current_time-start_time} {int(message[0:32].decode())} {len(message[64:])} 0")
        temp = int(message[0:32].decode())
        if temp == seq:
            total+=message[64:]
            seq+=len(message[64:])
            print(len(message[64:]))
            response_message = "SUCCESS "+str(seq)
            print(f"snd {current_time-start_time} 0 {MSS} {seq}")
        else:
            response_message = "SUCCESS "+str(seq)
            print(f"snd {current_time-start_time} 0 {MSS} {seq}")
        receiver_socket.sendto(response_message.encode(), clientAddress)
    except:
        temp = int(message[0:32].decode())
        if temp == seq:
            total += message[64:]
            seq += len(message[64:])
            response_message = "SUCCESS " + str(seq)
            print(f"snd {current_time-start_time} 0 {MSS} {seq}")
        else:
            response_message = "SUCCESS " + str(seq)
            print(f"snd {current_time-start_time} 0 {MSS} {seq}")
        receiver_socket.sendto(response_message.encode(), clientAddress)

with open("receive.pdf", "wb") as f:
    f.write(total)
receiver_socket.close()
