import socket
import threading
import time


class UDP_Server:
    def __init__(self, ip, port, buffer_size=1024):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))
        self.data = []

    def receive_start(self):
        udp_thread = threading.Thread(target=self.receive)
        udp_thread.setDaemon(True)
        udp_thread.start()

    def receive(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                self.data = list(map(float, data.decode("utf-8").split(",")))
            except:
                pass


if __name__ == "__main__":
    # server_ip = "133.68.108.51"
    server_ip = "0.0.0.0"
    # server_port = 31111
    server_port = 4000

    server = UDP_Server(server_ip, server_port)
    server.receive_start()

    while True:
        print(server.data)
        # print(time.time())
        time.sleep(0.01)
