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

# ----------------------------
# Configurati
# ----------------------------
DEVICE_NAME = "Dev3"
CHANNELS = ["ai23", "ai22", "ai21"]
# CHANNELS = ["ai20", "ai19", "ai18"]
SAMPLING_RATE = 10000
BUFFER_SIZE = 50

ACC_INDEX = 0 #描画する加速度センサがつなげられているチャンネルのインデックス
PLOT_DURATION_SEC = 0.5 #何秒分プロット表示しておくか
PLOT_BUFFER_SIZE = int(SAMPLING_RATE * PLOT_DURATION_SEC)


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

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(16) #16msごとに一回プロットをアップデート（約60fps)

        self.record_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        self.offset_button.clicked.connect(self.zero_fz_offset)

        self.acquisition_thread = threading.Thread(target=self.live_plot_worker)
        self.acquisition_thread.daemon = True
        self.acquisition_thread.start()

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
                acc, acc2, acc3 = self.data_queue.get_nowait()
                self.buffer_acc = np.roll(self.buffer_acc, -1)
                self.buffer_acc2 = np.roll(self.buffer_acc2, -1)
                self.buffer_acc3 = np.roll(self.buffer_acc3, -1)
                self.buffer_acc[-1] = acc
                self.buffer_acc2[-1] = acc2
                self.buffer_acc3[-1] = acc3

            self.acc_curve.setData(self.buffer_acc)
            self.acc2_curve.setData(self.buffer_acc2)
            self.acc3_curve.setData(self.buffer_acc3)
        except Exception as e:
            print(f"Plot update error: {e}")

    def zero_fz_offset(self):
        #オフセットの作成（fzのみ反転させて表示させているため-1）
        # self.target_line_pos.setPos(0.5)
        # self.target_line_neg.setPos(-1.5)
        # self.target_line_pos.show()
        # self.target_line_neg.show()
        print("zero_fz_offset")

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

            while True:
                data = task.read(number_of_samples_per_channel=BUFFER_SIZE, timeout=10.0)
                data = np.array(data).T

                acc1_volts = data[:, 0]  # ai6
                acc2_volts = data[:, 1]  # ai7
                acc3_volts = data[:, 2]  # ai7

                for i in range(BUFFER_SIZE):
                    acc1_v = float(acc1_volts[i])
                    acc2_v = float(acc2_volts[i])
                    acc3_v = float(acc3_volts[i])

                    self.data_queue.put((acc1_v,acc2_v,acc3_v))  # プロットに与えるデータ（ここをいじることで、描画するデータを変化できる）

                    if self.recording and self.record_start_time is not None:
                        rel_time = float(self.sample_counter) / SAMPLING_RATE
                        try:
                            self.record_queue.put((rel_time, acc1_v, acc2_v, acc3_v)) #記録されるデータのやり取り。今回は加速度2ch、６軸センサ、時間の9ch
                        except ValueError as e:
                            print(f"[ERROR] Float変換失敗: {e}") #データがちゃんと数値であることを再確認
                        self.sample_counter += 1


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
                    "%Time[s]", "Acc1[V]", "Acc2[V]", "Acc3[V]"
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
