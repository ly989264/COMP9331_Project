# import random
# # with open("2012.pdf", "rb") as f:
# #     message = f.read()
# #     total = b""
# #     seq = "00000001".encode()
# #     total += seq
# #     total += message
# # print(total[0:8].decode())
# # seq = 5
# # mes = f"{0:032d}".encode()
# # res = int(mes.decode())
# # print(res)
# # print(mes.decode())
# while True:
#     print(random.random())
mes = "000001234".encode()
new = "123"
print(hasattr(mes, "decode"))
print(hasattr(new, "decode"))
print(len(mes))