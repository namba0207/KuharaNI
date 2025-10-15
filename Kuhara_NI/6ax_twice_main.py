# 6軸2つをUDP通信で送信するプログラム
# enterキーでオフセット

import queue
import signal
import sys
import threading
import time

import nidaqmx
import numpy as np
from footswitch.footswitch_manager_default import FootSwitchManager
from nidaqmx.constants import AcquisitionType, TerminalConfiguration
from PyQt5 import QtCore, QtWidgets
from UDPmanager.UDP_client import UDP_Client

# from footswitch.footswitch_manager import FootSwitchManager


# ----------------------------
# Configuration
# ----------------------------
DEVICE_NAME = "Dev2"
CHANNELS = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5"]
#CHANNELS = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai16", "ai17", "ai18", "ai19", "ai20", "ai21"]
SAMPLING_RATE = 1000
BUFFER_SIZE = 50

ACC_INDEX = 0 #描画する加速度センサがつなげられているチャンネルのインデックス
PLOT_DURATION_SEC = 0.5 #何秒分プロット表示しておくか
PLOT_BUFFER_SIZE = int(SAMPLING_RATE * PLOT_DURATION_SEC)

IP = "192.168.1.106"
#IP = "127.0.0.1"
PORT = 4000

# SL241204
#right_transformation_matrix = np.array(
#    [
#        [ 0.82075, -0.01557,  0.01833, -0.00573,  0.13980, -0.03723 ],
#        [ 0.01000,  0.85419,  0.02723, -0.07019,  0.00863, -0.04327 ],
#        [-0.00113,  0.00209,  1.00162,  0.00393,  0.00109, -0.00561 ],
#        [ 0.00001,  0.00241,  0.00029,  0.00537, -0.00001,  0.00005 ],
#        [-0.00227, -0.00009, -0.00009,  0.00006,  0.00503,  0.00004 ],
#        [-0.00001,  0.00003,  0.00005, -0.00004, -0.00003,  0.00172 ],
#    ]
#)
right_transformation_matrix = np.array(
    [
        [0.10914659,	-0.175033812,	0.033204546,	37.83829747,	0.371201624,	-37.98082518],
        [0.794370141,	-0.698838417,	-0.26502932,	-22.17367438,	43.25516102,	-21.6462012],
        [-39.12493641,	-41.91198025,	-43.94914847,	-1.278777407,	0.219403608,	0.120865016],
        [-0.969774592,	0.010021827,	1.019471782,	-0.032829433,	-0.004120468,	0.010536731],
        [0.538330989,	-1.113419754,	0.592542023,	0.028002207,	-0.011676863,	0.00352569],
        [0.01011438,	0.002721234,	0.030332475,	-0.921533233,	-0.905764859,	-0.919035874],
    ]
)
# SL241001
# left_transformation_matrix = np.array(
#     [
#         [0.81444,-0.03822,0.00065,-0.00110,0.07771,0.07022,],
#         [0.01149,0.83642,-0.02069,-0.05656,0.00842,-0.05572,],
#         [0.00632,-0.00594,0.96449,0.00358,0.00042,0.02417,],
#         [0.00001,0.00229,-0.00008,0.00508,0.00001,0.00019,],
#         [-0.00221,-0.00001,-0.00004,0.00003,0.00495,0.00011,],
#         [0.00001,0.00004,0.00000,0.00002,-0.00002,0.00171,],
#     ]
# )
left_transformation_matrix = np.array(
    [
        [0.81444,-0.03822,0.00065,-0.00110,0.07771,0.07022,],
        [0.01149,0.83642,-0.02069,-0.05656,0.00842,-0.05572,],
        [0.00632,-0.00594,0.96449,0.00358,0.00042,0.02417,],
        [0.00001,0.00229,-0.00008,0.00508,0.00001,0.00019,],
        [-0.00221,-0.00001,-0.00004,0.00003,0.00495,0.00011,],
        [0.00001,0.00004,0.00000,0.00002,-0.00002,0.00171,],
    ]
)
# Z軸180度回転の6x6行列万博ver
# zax_180_matrix = np.array([
#             [-1,  0,  0,  0,  0,  0],
#             [ 0, -1,  0,  0,  0,  0],
#             [ 0,  0,  1,  0,  0,  0],
#             [ 0,  0,  0, -1,  0,  0],
#             [ 0,  0,  0,  0, -1,  0],
#             [ 0,  0,  0,  0,  0,  1]
#         ])
# MATRIX_LIST = [right_transformation_matrix, left_transformation_matrix, zax_180_matrix]
MATRIX_LIST = [right_transformation_matrix, left_transformation_matrix]

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_queue = queue.Queue()
        self.exit_event = threading.Event()  # 終了フラグを作成

        self.acquisition_thread = threading.Thread(target=self.live_plot_worker)
        self.acquisition_thread.daemon = True
        self.acquisition_thread.start()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(10) #10msごとに一回プロットをアップデート（約100fps)

        self.foot_switch = FootSwitchManager()
        self.foot_switch.detect_start()

        self.fz = 0.0
        self.fx = 0.0
        self.fy = 0.0
        self.mz = 0.0
        self.mx = 0.0
        self.my = 0.0
        self.fz2 = 0.0
        self.fx2 = 0.0
        self.fy2 = 0.0
        self.mz2 = 0.0
        self.mx2 = 0.0
        self.my2 = 0.0

        self.buffer_fx = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_fy = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_fz = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_mx = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_my = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_mz = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_fx2 = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_fy2 = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_fz2 = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_mx2 = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_my2 = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_mz2 = np.zeros(PLOT_BUFFER_SIZE)

        self.fz_offset = 0.0
        self.fx_offset = 0.0
        self.fy_offset = 0.0
        self.mz_offset = 0.0
        self.mx_offset = 0.0
        self.my_offset = 0.0
        self.fz2_offset = 0.0
        self.fx2_offset = 0.0
        self.fy2_offset = 0.0
        self.mz2_offset = 0.0
        self.mx2_offset = 0.0
        self.my2_offset = 0.0


#         QtWidgets.QApplication.instance().installEventFilter(self)


# #キーボードによる操作も可能にするための関数
#     def eventFilter(self, source, event):
#         if event.type() == QtCore.QEvent.KeyPress:
#             key = event.key()
#             if key == QtCore.Qt.Key_Z:
#                 self.zero_fz_offset()
#         return super().eventFilter(source, event)

    def update_plot(self):
        try:
            # print(111)
            while not self.data_queue.empty():
                # print(211)
                fx, fy, fz, mx, my, mz, fx2, fy2, fz2, mx2, my2, mz2 = self.data_queue.get_nowait()
                self.buffer_fx = np.roll(self.buffer_fx, -1)
                self.buffer_fy = np.roll(self.buffer_fy, -1)
                self.buffer_fz = np.roll(self.buffer_fz, -1)
                self.buffer_mx = np.roll(self.buffer_mx, -1)
                self.buffer_my = np.roll(self.buffer_my, -1)
                self.buffer_mz = np.roll(self.buffer_mz, -1)
                self.buffer_fx2 = np.roll(self.buffer_fx2, -1)
                self.buffer_fy2 = np.roll(self.buffer_fy2, -1)
                self.buffer_fz2 = np.roll(self.buffer_fz2, -1)
                self.buffer_mx2 = np.roll(self.buffer_mx2, -1)
                self.buffer_my2 = np.roll(self.buffer_my2, -1)
                self.buffer_mz2 = np.roll(self.buffer_mz2, -1)

                self.buffer_fx[-1] = fx
                self.buffer_fy[-1] = fy
                self.buffer_fz[-1] = fz
                self.buffer_mz[-1] = mz
                self.buffer_my[-1] = my
                self.buffer_mx[-1] = mx
                self.buffer_fx2[-1] = fx2
                self.buffer_fy2[-1] = fy2
                self.buffer_fz2[-1] = fz2
                self.buffer_mz2[-1] = mz2
                self.buffer_my2[-1] = my2
                self.buffer_mx2[-1] = mx2
            # print(321)
        except Exception as e:
            print(f"Plot update error: {e}")

    def zero_fz_offset(self):
        #オフセットの作成
        self.fz_offset = np.mean(self.buffer_fz)
        self.fx_offset = np.mean(self.buffer_fx)
        self.fy_offset = np.mean(self.buffer_fy)
        self.my_offset = np.mean(self.buffer_my)
        self.mx_offset = np.mean(self.buffer_mx)
        self.mz_offset = np.mean(self.buffer_mz)
        self.fz2_offset = np.mean(self.buffer_fz2)
        self.fx2_offset = np.mean(self.buffer_fx2)
        self.fy2_offset = np.mean(self.buffer_fy2)
        self.my2_offset = np.mean(self.buffer_my2)
        self.mx2_offset = np.mean(self.buffer_mx2)
        self.mz2_offset = np.mean(self.buffer_mz2)

    def live_plot_worker(self):
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                ",".join([f"{DEVICE_NAME}/{ch}" for ch in CHANNELS]),
                terminal_config=TerminalConfiguration.DIFF,  #差分入力を用いている
                min_val=-5.0,   #最小・最大値が+- 5Vのため
                max_val=5.0
            )
            task.timing.cfg_samp_clk_timing(
                rate=SAMPLING_RATE,
                sample_mode=AcquisitionType.CONTINUOUS,
                samps_per_chan=BUFFER_SIZE
            )
            task.start()
            while not self.exit_event.is_set():##
                data = task.read(number_of_samples_per_channel=BUFFER_SIZE, timeout=10.0)
                data = np.array(data).T

                volt_matrix = data[:, 0:6]  # ai0~ai5
                volt_matrix2 = data[:, 6:12]  # ai16~ai21
                # 電圧地を見る場合、上を伏せ下を表示
                # calibrated = volt_matrix @ MATRIX_LIST[0].T @ MATRIX_LIST[2].T*1000
                calibrated = volt_matrix @ MATRIX_LIST[0].T *1000
                calibrated2 = volt_matrix2 @ MATRIX_LIST[1].T *1000
                # calibrated = volt_matrix
                # calibrated2 = volt_matrix2
                if self.foot_switch.flag:
                    self.zero_fz_offset()


                for i in range(BUFFER_SIZE):
                    fx, fy, fz, mx, my, mz= map(float, calibrated[i])
                    fx2, fy2, fz2, mx2, my2, mz2 = map(float, calibrated2[i])
                    self.data_queue.put((fx, fy, fz, mx, my, mz, fx2, fy2, fz2, mx2, my2, mz2))  #bufferの最後尾に追加され、f+enterでoffsetの値が更新される
                    # print(fx)
                    self.fz = fz - self.fz_offset
                    self.fx = fx - self.fx_offset
                    self.fy = fy - self.fy_offset
                    self.mx = mx - self.mx_offset
                    self.my = my - self.my_offset
                    self.mz = mz - self.mz_offset
                    self.fz2 = fz2 - self.fz2_offset
                    self.fx2 = fx2 - self.fx2_offset
                    self.fy2 = fy2 - self.fy2_offset
                    self.mx2 = mx2 - self.mx2_offset
                    self.my2 = my2 - self.my2_offset
                    self.mz2 = mz2 - self.mz2_offset
                    # print(f"size{self.data_queue.qsize()}")
    def stop(self):
        self.exit_event.set()
        self.acquisition_thread.join()


def main(window):
    udp_client = UDP_Client()

    try:
        while True:
            udp_list = []
            udp_list.append(round(window.fx,4))
            udp_list.append(round(window.fy,4))
            udp_list.append(round(window.fz,4))
            udp_list.append(round(window.mx,4))
            udp_list.append(round(window.my,4))
            udp_list.append(round(window.mz,4))
            udp_list.append(round(window.fx2,4))
            udp_list.append(round(window.fy2,4))
            udp_list.append(round(window.fz2,4))
            udp_list.append(round(window.mx2,4))
            udp_list.append(round(window.my2,4))
            udp_list.append(round(window.mz2,4))

            udp_client.send(udp_list, IP, PORT)
            # print(udp_list)
            time.sleep(0.01)  # UDP送信レート


    except KeyboardInterrupt:
        print("KeyboardInterrupt detected. Exiting gracefully.")
        window.stop()
        sys.exit(0)



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()

    def signal_handler(sig, frame):
        print("Ctrl+C detected. Exiting gracefully...")
        window.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    udp_thread = threading.Thread(target=main, args=(window,), daemon=True)
    udp_thread.start()

    # window.show()  # ウィンドウを表示
    sys.exit(app.exec_())
