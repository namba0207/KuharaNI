import socket
import time


class UDP_Client:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, data_list, client_ip, client_port):
        message = ",".join(map(str, data_list))
        self.sock.sendto(message.encode("utf-8"), (client_ip, client_port))

    def close(self):
        self.sock.close()


if __name__ == "__main__":
    client_ip = "192.168.1.110"  # 送信先のIPアドレス
    client_port = 7375  # 送信先のポート

    sender = UDP_Client()

    while True:
        for i in range(100):
            data_list = [ i / 100, i / 100]
            sender.send(data_list, client_ip, client_port)
            print(data_list)
            print(time.time())
            time.sleep(0.1)
