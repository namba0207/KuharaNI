# import logging
import threading
import time
import keyboard
# logger = logging.getLogger(__name__)


class FootSwitchManager:
    def __init__(self) -> None:
        self.flag = False
        self.detecting = False

    def detect_start(self):
        footswitch_thread = threading.Thread(target=self.detect_switching)
        footswitch_thread.setDaemon(True)
        footswitch_thread.start()

    def detect_switching(self):
        print("Start foot switch manager")
        try:
            while True:
                if keyboard.is_pressed('enter'):
                    print("Foot Switch pressed")
                    self.flag = True
                else:
                    self.flag = False
                time.sleep(0.1)

        except Exception as e:
            print("FootSwitch error occured : ",e)
