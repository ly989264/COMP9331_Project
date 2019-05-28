from socket import *

serverName = "192.168.1.8"
serverPort = 50001
my_port = 50002

clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName, serverPort))
request_message = "SUCCESSOR REQUEST "+my_port
clientSocket.send(request_message.encode())
response_message = clientSocket.recv(1024).decode()
clientSocket.close()