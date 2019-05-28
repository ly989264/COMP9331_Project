# testing for multi-client tcp
import threading
from socket import *

successor_port = [50007,50009]
self_port = 50001

class TCP_Certain_Server_Thread(threading.Thread):
    # mode: 1(SUCCESSOR RESPONSE)
    # already: implement the mode 1, that is, respond to a SUCCESSOR REQUEST
    # improve: add more modes
    def __init__(self, connectionSocket, port_num, target_port, mode):
        threading.Thread.__init__(self)
        self.connectionSocket = connectionSocket
        self.port_num = port_num
        self.target_port = target_port
        self.mode = mode

    def run(self):
        if self.mode == 1:
            response_message = "SUCCESSOR RESPONSE "+str(self.port_num)+" "+str(successor_port[0])
            self.connectionSocket.send(response_message.encode())
            self.connectionSocket.close()


class TCP_Server_Thread(threading.Thread):
    # todo: need to add methods to respond to certain modes, such as successor request and so on
    def __init__(self, port_num):
        threading.Thread.__init__(self)
        self.port_num = port_num
        self.serverSocket = socket(AF_INET, SOCK_STREAM)
        self.serverSocket.bind(('', port_num))

    def run(self):# need to modify
        self.serverSocket.listen(5)
        while True:
            connectionSocket, addr = self.serverSocket.accept()
            try:
                message = connectionSocket.recv(1024).decode()
                target_port_num = int(message.split(" ")[2])
                if message.startswith("SUCCESSOR REQUEST"):
                    current_working_thread = TCP_Certain_Server_Thread(connectionSocket, self.port_num, target_port_num, 1)
                    current_working_thread.start()
            except ConnectionResetError:
                print("Testing... ConnectionResetError occurs.")
                connectionSocket.close()

tcp_server = TCP_Server_Thread(self_port)
tcp_server.start()