from socket import *
# from _thread import *
import threading

port_num = 51000

# serverSocket_UDP = socket(AF_INET, SOCK_DGRAM)
# serverSocket_UDP.bind(('', port_num))
# serverSocket_TCP = socket(AF_INET, SOCK_STREAM)
# serverSocket_TCP.bind(('', port_num))
# serverSocket_TCP.listen(1)


class UDP_Server_Thread(threading.Thread):
    def __init__(self, portnum):
        threading.Thread.__init__(self)
        self.serverSocket = socket(AF_INET, SOCK_DGRAM)
        self.serverSocket.bind(('', portnum))
    def run(self):
        while True:
            message, clientAddress = self.serverSocket.recvfrom(1024)
            print(f"Get UDP segment from {clientAddress}.")
            modified_message = message.decode().upper()
            self.serverSocket.sendto(modified_message.encode(), clientAddress)

class TCP_Server_Thread(threading.Thread):
    def __init__(self, portnum):
        threading.Thread.__init__(self)
        self.serverSocket = socket(AF_INET, SOCK_STREAM)
        self.serverSocket.bind(('', portnum))
    def run(self):
        self.serverSocket.listen(1)
        while True:
            connectionSocket, addr = self.serverSocket.accept()
            print(f"Get TCP connection from {addr}.")
            message = connectionSocket.recv(1024).decode()
            modified_message = message.upper()
            connectionSocket.send(modified_message.encode())
            connectionSocket.close()

udp_server = UDP_Server_Thread(port_num)
tcp_server = TCP_Server_Thread(port_num)
udp_server.start()
tcp_server.start()
# thread1.join()
for i in range(0,5):
    print("Good")
print("Currently do something else...")
