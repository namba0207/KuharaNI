# NI計測用
import sys
import csv
import time
import threading
import queue
from datetime import datetime

import numpy as np
import nidaqmx
from nidaqmx.constants import TerminalConfiguration, AcquisitionType

from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import subprocess
import shutil
import os
from UDPmanager.UDP_client import UDP_Client

# ----------------------------
# Configuration
# ----------------------------
DEVICE_NAME = "Dev1"
# CHANNELS = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5"]
CHANNELS = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai16", "ai17", "ai18", "ai19", "ai20", "ai21", "ai22", "ai23" ,"ai7"]
SAMPLING_RATE = 10000
BUFFER_SIZE = 50

ACC_INDEX = 0 #描画する加速度センサがつなげられているチャンネルのインデックス
PLOT_DURATION_SEC = 0.5 #何秒分プロット表示しておくか
PLOT_BUFFER_SIZE = int(SAMPLING_RATE * PLOT_DURATION_SEC)

IP = "192.168.1.106"
# IP = "192.168.1.120" 
# IP = "127.0.0.1"
PORT = 4000

# #６軸センサのキャリブレーション行列
# CALIBRATION_MATRIX = np.array([
#     [-0.06277504,-0.00480834, 0.175365125,-3.53200733,-0.034232648, 3.712051954],
#     [-0.00103409, 4.363659635, 0.039568587,-2.04681801, 0.011019536,-2.16906922],
#     [ 6.326047433,-0.08096102, 6.511267484, -0.11298753, 6.727075512, -0.12351941],
#     [ 0.001311513, 0.052590741,-0.18750501,-0.02163648, 0.193626859,-0.02905352],
#     [ 0.21226524,-0.00180459,-0.11079105, 0.044118346,-0.11272954,-0.04336467],
#     [ 0.000568608,-0.11790644, 0.003529006,-0.11234363, -0.00040179,-0.11817436]
# ])
# SL241204
right_transformation_matrix = np.array(
    [
        [ 0.82075, -0.01557,  0.01833, -0.00573,  0.13980, -0.03723 ],
        [ 0.01000,  0.85419,  0.02723, -0.07019,  0.00863, -0.04327 ],
        [-0.00113,  0.00209,  1.00162,  0.00393,  0.00109, -0.00561 ],
        [ 0.00001,  0.00241,  0.00029,  0.00537, -0.00001,  0.00005 ],
        [-0.00227, -0.00009, -0.00009,  0.00006,  0.00503,  0.00004 ],
        [-0.00001,  0.00003,  0.00005, -0.00004, -0.00003,  0.00186 ],
    ]
)
# SL241001
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
zax_180_matrix = np.array([
            [-1,  0,  0,  0,  0,  0],
            [ 0, -1,  0,  0,  0,  0],
            [ 0,  0,  1,  0,  0,  0],
            [ 0,  0,  0, -1,  0,  0],
            [ 0,  0,  0,  0, -1,  0],
            [ 0,  0,  0,  0,  0,  1]
        ])
MATRIX_LIST = [right_transformation_matrix, left_transformation_matrix, zax_180_matrix]

#やり取りされている電圧値や力の値がちゃんと数値として成り立っているかの確認
def is_valid_number(val):
    return isinstance(val, float) and np.isfinite(val)

#GUIのメイン設定（描画やボタン等)
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Plotter: acc + fx/fy/fz")
        self.setGeometry(100, 100, 1000, 600)

        self.record_button = QtWidgets.QPushButton("Start Recording (R)")
        self.stop_button = QtWidgets.QPushButton("Stop Recording (S)")
        self.stop_button.setEnabled(False)
        self.offset_button = QtWidgets.QPushButton("Zero Fz Offset (Z)")

        self.plot_widget = pg.GraphicsLayoutWidget()
        self.acc_plot = self.plot_widget.addPlot(title="Accelerometer Propagating (ai6)")
        self.acc_plot.setYRange(-2, 2)
        self.acc_curve = self.acc_plot.plot(pen='y')

        self.plot_widget.nextRow()
        self.acc2_plot = self.plot_widget.addPlot(title="Accelerometer Vibrotactile (ai4)")
        self.acc2_plot.setYRange(-2, 2)
        self.acc2_curve = self.acc2_plot.plot(pen='y')

        self.plot_widget.nextRow()
        self.acc3_plot = self.plot_widget.addPlot(title="Accelerometer Vibrotactile (ai4)")
        self.acc3_plot.setYRange(-2, 2)
        self.acc3_curve = self.acc3_plot.plot(pen='y')

        self.plot_widget.nextRow()
        self.force_plot = self.plot_widget.addPlot(title="Forces (Fx, Fy, Fz)")
        self.force_plot.addLegend(offset=(80, 10))
        self.force_plot.setYRange(-10, 10)
        self.fx_curve = self.force_plot.plot(pen='b', name='Fx')
        self.fy_curve = self.force_plot.plot(pen='g', name='Fy')
        self.fz_curve = self.force_plot.plot(pen='r', name='Fz')
        self.target_line_pos = pg.InfiniteLine(angle=0, pen=pg.mkPen('r', width=2, style=QtCore.Qt.DashLine))
        self.target_line_neg = pg.InfiniteLine(angle=0, pen=pg.mkPen('r', width=2, style=QtCore.Qt.DashLine))
        self.force_plot.addItem(self.target_line_pos)
        self.force_plot.addItem(self.target_line_neg)
        self.target_line_pos.hide()
        self.target_line_neg.hide()

        self.plot_widget.nextRow()
        self.moment_plot = self.plot_widget.addPlot(title="Moment (Mx, My, Mz)")
        self.moment_plot.addLegend(offset=(80, 10))
        self.moment_plot.setYRange(-1, 1)
        self.mx_curve = self.moment_plot.plot(pen='b', name='Mx')
        self.my_curve = self.moment_plot.plot(pen='g', name='My')
        self.mz_curve = self.moment_plot.plot(pen='r', name='Mz')

        self.plot_widget.nextRow()
        self.force_plot2 = self.plot_widget.addPlot(title="Forces (Fx, Fy, Fz)")
        self.force_plot2.addLegend(offset=(80, 10))
        self.force_plot2.setYRange(-10, 10)
        self.fx_curve2 = self.force_plot2.plot(pen='b', name='Fx')
        self.fy_curve2 = self.force_plot2.plot(pen='g', name='Fy')
        self.fz_curve2 = self.force_plot2.plot(pen='r', name='Fz')
        self.target_line_pos2 = pg.InfiniteLine(angle=0, pen=pg.mkPen('r', width=2, style=QtCore.Qt.DashLine))
        self.target_line_neg2 = pg.InfiniteLine(angle=0, pen=pg.mkPen('r', width=2, style=QtCore.Qt.DashLine))
        self.force_plot.addItem(self.target_line_pos2)
        self.force_plot.addItem(self.target_line_neg2)
        self.target_line_pos2.hide()
        self.target_line_neg2.hide()

        self.plot_widget.nextRow()
        self.moment_plot2 = self.plot_widget.addPlot(title="Moment (Mx, My, Mz)")
        self.moment_plot2.addLegend(offset=(80, 10))
        self.moment_plot2.setYRange(-1, 1)
        self.mx_curve2 = self.moment_plot2.plot(pen='b', name='Mx')
        self.my_curve2 = self.moment_plot2.plot(pen='g', name='My')
        self.mz_curve2 = self.moment_plot2.plot(pen='r', name='Mz')
        

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.plot_widget)
        layout.addWidget(self.record_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.offset_button)

        container = QtWidgets.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.data_queue = queue.Queue()
        self.record_queue = queue.Queue()
        self.recording = False
        self.record_start_time = None
        self.worker_thread = None
        self.file_lock = threading.Lock()

        self.buffer_acc = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_acc2 = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_acc3 = np.zeros(PLOT_BUFFER_SIZE)
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
        self.flag = 0
        self.flag_v = 0
        # self.time_s = time.perf_counter()
        # self.timer = QtCore.QTimer()#プロットを非表示の場合この3行伏
        # self.timer.timeout.connect(self.update_plot)
        # self.timer.start(16) #16msごとに一回プロットをアップデート（約60fps)

        self.record_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        self.offset_button.clicked.connect(self.zero_fz_offset)

        self.acquisition_thread = threading.Thread(target=self.live_plot_worker)
        self.acquisition_thread.daemon = True
        self.acquisition_thread.start()
        # self.buffer_thread = threading.Thread(target=self.buffer_def)
        # self.buffer_thread.daemon = True
        # self.buffer_thread.start()        
        # self.udp_thread = threading.Thread(target=self.udp_send)
        # self.udp_thread.daemon = True
        # self.udp_thread.start()


        QtWidgets.QApplication.instance().installEventFilter(self)


#キーボードによる操作も可能にするための関数（今回はｚ、ｒ、ｓ、escの４種類に対応）
    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            if key == QtCore.Qt.Key_R:
                self.start_recording()
            elif key == QtCore.Qt.Key_S:
                self.stop_recording()
            elif key == QtCore.Qt.Key_Z:
                self.zero_fz_offset()
            elif key == QtCore.Qt.Key_Escape:
                print("Interrupted by keyboard. Exiting.")
                QtWidgets.QApplication.quit()
        return super().eventFilter(source, event)


    def update_plot(self):
        try:
            while not self.data_queue.empty():
                acc, acc2, acc3, fx, fy, fz, mx, my, mz, fx2, fy2, fz2, mx2, my2, mz2 = self.data_queue.get_nowait()
                self.buffer_acc = np.roll(self.buffer_acc, -1)
                self.buffer_acc2 = np.roll(self.buffer_acc2, -1)
                self.buffer_acc3 = np.roll(self.buffer_acc3, -1)
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
                self.buffer_acc[-1] = acc
                self.buffer_acc2[-1] = acc2
                self.buffer_acc3[-1] = acc3
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

            # self.acc_curve.setData(self.buffer_acc)
            # self.acc2_curve.setData(self.buffer_acc2)
            # self.acc3_curve.setData(self.buffer_acc3)
            # self.fx_curve.setData(self.buffer_fx)
            # self.fy_curve.setData(self.buffer_fy)
            # self.fz_curve.setData(self.buffer_fz)
            # self.mz_curve.setData(self.buffer_mz)
            # self.my_curve.setData(self.buffer_my)
            # self.mx_curve.setData(self.buffer_mx)
            # self.fx_curve2.setData(self.buffer_fx2)
            # self.fy_curve2.setData(self.buffer_fy2)
            # self.fz_curve2.setData(self.buffer_fz2)
            # self.mz_curve2.setData(self.buffer_mz2)
            # self.my_curve2.setData(self.buffer_my2)
            # self.mx_curve2.setData(self.buffer_mx2)
        except Exception as e:
            print(f"Plot update error: {e}")

    def zero_fz_offset(self):
        #オフセットの作成（fzのみ反転させて表示させているため-1）
        self.flag = 1
        self.fz_offset = np.mean(self.buffer_fz) *1
        self.fx_offset = np.mean(self.buffer_fx) *1
        self.fy_offset = np.mean(self.buffer_fy) *1
        self.my_offset = np.mean(self.buffer_my) *1
        self.mx_offset = np.mean(self.buffer_mx) *1
        self.mz_offset = np.mean(self.buffer_mz) *1
        self.fz2_offset = np.mean(self.buffer_fz2) *1
        self.fx2_offset = np.mean(self.buffer_fx2) *1
        self.fy2_offset = np.mean(self.buffer_fy2) *1
        self.my2_offset = np.mean(self.buffer_my2) *1
        self.mx2_offset = np.mean(self.buffer_mx2) *1
        self.mz2_offset = np.mean(self.buffer_mz2) *1
        # self.target_line_pos.setPos(0.5)
        # self.target_line_neg.setPos(-1.5)
        # self.target_line_pos.show()
        # self.target_line_neg.show()

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
            udp_client = UDP_Client()
            while True:
                data = task.read(number_of_samples_per_channel=BUFFER_SIZE, timeout=10.0)
                data = np.array(data).T

                acc1_volts = data[:, 12]  # ai6
                acc2_volts = data[:, 13]  # ai7
                acc3_volts = data[:, 14]  # ai7
                volt_matrix = data[:, 0:6]  # ai0~ai5
                volt_matrix2 = data[:, 6:12]  # ai16~ai21

                calibrated = volt_matrix @ MATRIX_LIST[0].T
                calibrated = calibrated @ MATRIX_LIST[2].T*1000
                calibrated2 = volt_matrix2 @ MATRIX_LIST[1].T
                calibrated2 = calibrated2 @ MATRIX_LIST[2].T*1000

                for i in range(BUFFER_SIZE):
                    acc1_v = float(acc1_volts[i])
                    acc2_v = float(acc2_volts[i])
                    acc3_v = float(acc3_volts[i])
                    fx, fy, fz, mx, my, mz = map(float, calibrated[i])
                    fz -= self.fz_offset
                    fx -= self.fx_offset
                    fy -= self.fy_offset
                    mx -= self.mx_offset
                    my -= self.my_offset
                    mz -= self.mz_offset
                    fx2, fy2, fz2, mx2, my2, mz2 = map(float, calibrated2[i])
                    fz2 -= self.fz2_offset
                    fx2 -= self.fx2_offset
                    fy2 -= self.fy2_offset
                    mx2 -= self.mx2_offset
                    my2 -= self.my2_offset
                    mz2 -= self.mz2_offset

                    if self.flag == 1:
                        self.fz_offset = fz
                        self.fx_offset = fx
                        self.fy_offset = fy
                        self.mx_offset = mx
                        self.my_offset = my
                        self.mz_offset = mz
                        self.fz2_offset = fz2
                        self.fx2_offset = fx2
                        self.fy2_offset = fy2
                        self.mx2_offset = mx2
                        self.my2_offset = my2
                        self.mz2_offset = mz2
                        self.flag = 0

                    self.data_queue.put((acc1_v,acc2_v,acc3_v,fx, fy, fz, mx, my, mz, fx2, fy2, fz2, mx2, my2, mz2))   # プロットに与えるデータ（ここをいじることで、描画するデータを変化できる）

                    if self.recording and self.record_start_time is not None:
                        rel_time = float(self.sample_counter) / SAMPLING_RATE
                        try:
                            self.record_queue.put((rel_time, acc1_v, acc2_v, acc3_v, fx, fy, fz, mx, my, mz, fx2, fy2, fz2, mx2, my2, mz2)) #記録されるデータのやり取り。今回は加速度2ch、６軸センサ、時間の9ch
                        except ValueError as e:
                            print(f"[ERROR] Float変換失敗: {e}") #データがちゃんと数値であることを再確認
                        self.sample_counter += 1
                    udp_list = []
                    udp_list.append(fx)
                    udp_list.append(fy)
                    udp_list.append(fz)
                    udp_list.append(mx)
                    udp_list.append(my)
                    udp_list.append(mz)
                    udp_list.append(fx2)
                    udp_list.append(fy2)
                    udp_list.append(fz2)
                    udp_list.append(mx2)
                    udp_list.append(my2)
                    udp_list.append(mz2)

                    udp_client.send(udp_list, IP, PORT)
                    # if acc3_v > 1 & self.flag_v == 0:
                    #    print(1/(time.perf_counter() - self.time_s))
                    #    self.time_s = time.perf_counter()
                    #    self.flag_v = 1
                    # elif acc3_v < 1 & self.flag_v == 1:
                    #     self.flag_v = 0
                        

    def start_recording(self):
        if self.worker_thread and self.worker_thread.is_alive():
            print("[WARN] Recording already in progress.")
            return
        self.recording = True
        # self.frame_count = 0
        # self.screenshot_timer = QtCore.QTimer()
        # self.screenshot_timer.timeout.connect(self.save_frame)
        # self.screenshot_timer.start(100)
        self.record_start_time = time.perf_counter()
        self.sample_counter = 0
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        while not self.record_queue.empty():
            self.record_queue.get()
        self.worker_thread = threading.Thread(target=self.record_worker)
        self.worker_thread.start()

    # def save_frame(self):           #あとから変化を視覚的に見返せるように動画も作成されるようにスクリーンショットが撮影される。
    #     pixmap = self.plot_widget.grab()
    #     image = pixmap.toImage()
    #     width = image.width()
    #     height = image.height()
    #     if height % 2 != 0:
    #         image = image.copy(0, 0, width, height - 1)
    #     image.save(f"frames/frame_{self.frame_count:05d}.png")
    #     self.frame_count += 1

    def stop_recording(self):
        self.recording = False
        # self.screenshot_timer.stop()
        self.stop_button.setEnabled(False)
        self.record_button.setEnabled(True)
        if self.worker_thread:
            self.worker_thread.join()
            self.worker_thread = None

        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # video_filename = f"plot_video_{timestamp}.mp4"
        # print("Generating video...")
        # subprocess.run([
        #     "ffmpeg", "-y", "-framerate", "10", "-i",
        #     "frames/frame_%05d.png", "-vcodec", "libx264",
        #     "-pix_fmt", "yuv420p", video_filename
        # ])
        # print(f"Saved video to {video_filename}")

        # print("Cleaning up frames...")
        # if os.path.exists("frames"):
        #     shutil.rmtree("frames")
        # os.makedirs("frames", exist_ok=True)
        # print("Cleanup complete.")


## CSVファイルで出力したい場合
    # def record_worker(self):
    #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #     filename_csv = f"recorded_data_{timestamp}.csv"
    #     with self.file_lock:
    #         with open(filename_csv, mode='w', newline='', encoding='utf-8') as file:
    #             writer = csv.writer(file)
    #             writer.writerow([
                #     "Time[s]", "Acc1[V]", "Acc2[V]",
                #     "Fx[N]", "Fy[N]", "Fz[N]",
                #     "Mx[Nm]", "My[Nm]", "Mz[Nm]"
                #   ])
    #             while self.recording or not self.record_queue.empty():
    #                 try:
    #                     row = self.record_queue.get(timeout=0.1)
    #                     if all(is_valid_number(val) for val in row):
    #                         writer.writerow(["{:.6f}".format(val) for val in row])
    #                     else:
    #                         print(f"[SKIP] Invalid data row: {row}")
    #                 except queue.Empty:
    #                     continue

    def record_worker(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_txt = f"recorded_data_{timestamp}.txt"
        with self.file_lock:
            with open(filename_txt, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter='\t')  # タブ区切りでTXT形式に
                writer.writerow([
                    "%Time[s]",
                    "Fx[N]", "Fy[N]", "Fz[N]",
                    "Mx[Nm]", "My[Nm]", "Mz[Nm]" "Acc1[V]", "Acc2[V]", "Acc3[V]"
                    # "Fx2[N]", "Fy2[N]", "Fz2[N]",
                    # "Mx2[Nm]", "My2[Nm]", "Mz2[Nm]"
                ])
                while self.recording or not self.record_queue.empty():
                    try:
                        row = self.record_queue.get(timeout=0.1)
                        if all(is_valid_number(val) for val in row):
                            writer.writerow(["{:.6f}".format(val) for val in row])
                        else:
                            print(f"[SKIP] Invalid data row: {row}")
                    except queue.Empty:
                        continue


if __name__ == '__main__':
    try:
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("KeyboardInterrupt detected. Exiting gracefully.")
        sys.exit(0)
