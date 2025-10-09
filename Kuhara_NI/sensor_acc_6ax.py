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

# ----------------------------
# Configuration
# ----------------------------
DEVICE_NAME = "Dev1"
CHANNELS = ["ai6", "ai7", "ai17", "ai18", "ai19", "ai20", "ai21", "ai22"]
SAMPLING_RATE = 25000
BUFFER_SIZE = 1000  # samples per channel per update

ACC_INDEX = 0  # ai6
FZ_INDEX = 4   # ai19
PLOT_DURATION_SEC = 0.5  # 0.5 seconds
PLOT_BUFFER_SIZE = int(SAMPLING_RATE * PLOT_DURATION_SEC)

# Calibration matrix for 6-axis force sensor (6x6)
CALIBRATION_MATRIX = np.array([
    [-0.06277504,-0.00480834, 0.175365125,-3.53200733,-0.034232648, 3.712051954],
    [-0.00103409, 4.363659635, 0.039568587,-2.04681801, 0.011019536,-2.16906922],
    [ 6.326047433,-0.08096102, 6.511267484, -0.11298753, 6.727075512, -0.12351941],
    [ 0.001311513, 0.052590741,-0.18750501,-0.02163648, 0.193626859,-0.02905352],
    [ 0.21226524,-0.00180459,-0.11079105, 0.044118346,-0.11272954,-0.04336467],
    [ 0.000568608,-0.11790644, 0.003529006,-0.11234363, -0.00040179,-0.11817436]
])

# ----------------------------
# Main GUI Window
# ----------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Plotter: acc + fz")
        self.setGeometry(100, 100, 1000, 600)

        self.record_button = QtWidgets.QPushButton("Start Recording")
        self.stop_button = QtWidgets.QPushButton("Stop Recording")
        self.stop_button.setEnabled(False)
        self.offset_button = QtWidgets.QPushButton("Zero Fz Offset")

        self.plot_widget = pg.GraphicsLayoutWidget()
        self.acc_plot = self.plot_widget.addPlot(title="Accelerometer (ai6)")
        self.acc_plot.setYRange(-5, 5)
        self.acc_curve = self.acc_plot.plot(pen='y')

        self.plot_widget.nextRow()
        self.fz_plot = self.plot_widget.addPlot(title="Fz Force (ai19)")
        self.fz_plot.setYRange(-5, 5)
        self.fz_curve = self.fz_plot.plot(pen='c')
        self.target_line_pos = pg.InfiniteLine(angle=0, pen=pg.mkPen('r', width=2, style=QtCore.Qt.DashLine))
        self.target_line_neg = pg.InfiniteLine(angle=0, pen=pg.mkPen('r', width=2, style=QtCore.Qt.DashLine))
        self.fz_plot.addItem(self.target_line_pos)
        self.fz_plot.addItem(self.target_line_neg)
        self.target_line_pos.hide()
        self.target_line_neg.hide()

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

        self.buffer_acc = np.zeros(PLOT_BUFFER_SIZE)
        self.buffer_fz = np.zeros(PLOT_BUFFER_SIZE)

        self.fz_offset = 0.0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(30)

        self.record_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        self.offset_button.clicked.connect(self.zero_fz_offset)

        self.acquisition_thread = threading.Thread(target=self.live_plot_worker)
        self.acquisition_thread.daemon = True
        self.acquisition_thread.start()

    def update_plot(self):
        try:
            while not self.data_queue.empty():
                acc, fz = self.data_queue.get_nowait()
                self.buffer_acc = np.roll(self.buffer_acc, -1)
                self.buffer_acc[-1] = acc
                self.buffer_fz = np.roll(self.buffer_fz, -1)
                self.buffer_fz[-1] = fz

            self.acc_curve.setData(self.buffer_acc)
            self.fz_curve.setData(self.buffer_fz)
        except Exception as e:
            print(f"Plot update error: {e}")

    def zero_fz_offset(self):
        self.fz_offset = np.mean(self.buffer_fz)
        #self.target_line_pos.setPos(0.5)
        self.target_line_neg.setPos(-0.5)
        #self.target_line_pos.show()
        self.target_line_neg.show()
        print(f"Fz offset set to: {self.fz_offset:.4f}. Target lines at ±0.5N.")

    def live_plot_worker(self):
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                ",".join([f"{DEVICE_NAME}/{ch}" for ch in CHANNELS]),
                terminal_config=TerminalConfiguration.DIFF,
                min_val=-5.0,
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
                acc_volts = data[:, ACC_INDEX]
                volt_matrix = data[:, 2:]
                calibrated = volt_matrix @ CALIBRATION_MATRIX.T
                current_time = time.perf_counter()
                t = np.arange(BUFFER_SIZE) / SAMPLING_RATE + current_time

                for i in range(BUFFER_SIZE):
                    acc_v = acc_volts[i]
                    fz = calibrated[i, 2] - self.fz_offset
                    self.data_queue.put((acc_v, fz))
                    if self.recording and self.record_start_time is not None:
                        fx, fy, fz_raw, mx, my, mz = calibrated[i]
                        rel_time = t[i] - self.record_start_time
                        self.record_queue.put([
                            f"{rel_time:.6f}",
                            f"{acc_v:.6f}",
                            f"{fx:.6f}", f"{fy:.6f}", f"{fz:.6f}",
                            f"{mx:.6f}", f"{my:.6f}", f"{mz:.6f}"
                        ])

    def start_recording(self):
        self.recording = True
        self.record_start_time = time.perf_counter()
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.worker_thread = threading.Thread(target=self.record_worker)
        self.worker_thread.start()

    def stop_recording(self):
        self.recording = False
        self.stop_button.setEnabled(False)
        self.record_button.setEnabled(True)
        self.worker_thread.join()

    def record_worker(self):
        print("Recording started")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recorded_data_{timestamp}.csv"

        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            header = ["Time[s]", "acc[V]", "fx[N]", "fy[N]", "fz[N]", "mx[Nm]", "my[Nm]", "mz[Nm]"]
            writer.writerow(header)

            while self.recording or not self.record_queue.empty():
                try:
                    row = self.record_queue.get(timeout=0.1)
                    writer.writerow(row)
                except queue.Empty:
                    continue

        print(f"Saved to {filename}")

# ----------------------------
# Entry point
# ----------------------------
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
