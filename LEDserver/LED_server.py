import socket
import threading
import time
import serial
import json as js

class UDP_Server:
    def __init__(self, ip, port, config_path, buffer_size=1024):
        print(ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))
        
        with open(config_path, "r") as f:
            self.config = js.load(f)
        
        self.ser_dict = {
            rb: serial.Serial(cfg["port"], 9600, timeout=1)
            for rb, cfg in self.config["LEDConfig"].items()
        }

        self.data = {} 

    def receive_start(self):
        udp_thread = threading.Thread(target=self.receive)
        udp_thread.setDaemon(True)
        udp_thread.start()

    def receive(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                decoded_data = data.decode("utf-8").split(",") 
                rigidbody = decoded_data[0] 
                rgb_values = decoded_data[1:]  

                if rigidbody in self.config["LEDConfig"]:  
                    self.data[rigidbody] = rgb_values
                    print(f"Updated data: {self.data}") 
            except Exception as e:
                print(f"Error: {e}") 

    def send_LED_values(self):
        while True:
            # print(f"Current LED Data: {self.data}") 
            for rigidbody, rgb_values in self.data.items():
                if rigidbody in self.ser_dict:
                    serial_data = "".join(rgb_values)  
                    self.ser_dict[rigidbody].write(serial_data.encode())
                    # print(f"Sent to {rigidbody}: {serial_data}")  

            time.sleep(0.1) 


if __name__ == "__main__":
    server_ip = "0.0.0.0"
    server_port = 57128
    # config_path = "/Users/hapticslab/Desktop/LEDserver/config/settings.json" 
    config_path = R"C:\Users\tanak\Desktop\LEDserver-main\LEDserver\config\settings.json"

    server = UDP_Server(server_ip, server_port, config_path)
    server.receive_start()

    server.send_LED_values() 
