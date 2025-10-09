import logging
import threading
import time

logger = logging.getLogger(__name__)


class FootSwitchManager:
    def __init__(self) -> None:
        self.flag = False
        self.detecting = False

    def detect_start(self):
        footswitch_thread = threading.Thread(target=self.detect_switching)
        footswitch_thread.setDaemon(True)
        footswitch_thread.start()

    def detect_switching(self):
        logger.info("Start foot switch manager")
        try:
            while True:
                self.flag = False
                key = input("Press to change mode")
                if key == "f":
                    if self.flag == False:
                        self.flag = True

                else:
                    pass
                time.sleep(0.1)

        except:
            logger.error("FootSwitch error occured")
