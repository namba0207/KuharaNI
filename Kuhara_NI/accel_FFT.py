import sys
import numpy as np
from PyQt5 import QtWidgets
import pyqtgraph as pg

# === データ読み込み ===
filename = "data.txt"
data = np.loadtxt(filename, skiprows=1)
t = data[:, 0]    # 時間[秒]
y1 = data[:, 1]   # 振動データ1
y2 = data[:, 2]   # 振動データ2
y3 = data[:, 1]   # 仮にy1をコピー
y4 = data[:, 2]   # 仮にy2をコピー
y5 = data[:, 1]   # 仮にy1をコピー
y6 = data[:, 2]   # 仮にy2をコピー

# === PyQt5 アプリケーション ===
app = QtWidgets.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(title="6 Rows Time Series")
win.resize(800, 800)

# 1行目
p1 = win.addPlot(title="Graph 1")
p1.plot(t, y1, pen=pg.mkPen('b', width=2))
p1.setLabel('left', 'Accel', units='m/s^2')
p1.setLabel('bottom', 'Time', units='s')
p1.showGrid(x=True, y=True)

# 2行目
win.nextRow()
p2 = win.addPlot(title="Graph 2")
p2.plot(t, y2, pen=pg.mkPen('r', width=2))
p2.setLabel('left', 'Accel', units='m/s^2')
p2.setLabel('bottom', 'Time', units='s')
p2.showGrid(x=True, y=True)

# 3行目
win.nextRow()
p3 = win.addPlot(title="Graph 3")
p3.plot(t, y3, pen=pg.mkPen('g', width=2))
p3.setLabel('left', 'Accel', units='m/s^2')
p3.setLabel('bottom', 'Time', units='s')
p3.showGrid(x=True, y=True)

# 4行目
win.nextRow()
p4 = win.addPlot(title="Graph 4")
p4.plot(t, y4, pen=pg.mkPen('c', width=2))
p4.setLabel('left', 'Accel', units='m/s^2')
p4.setLabel('bottom', 'Time', units='s')
p4.showGrid(x=True, y=True)

# 5行目
win.nextRow()
p5 = win.addPlot(title="Graph 5")
p5.plot(t, y5, pen=pg.mkPen('m', width=2))
p5.setLabel('left', 'Accel', units='m/s^2')
p5.setLabel('bottom', 'Time', units='s')
p5.showGrid(x=True, y=True)

# 6行目
win.nextRow()
p6 = win.addPlot(title="Graph 6")
p6.plot(t, y6, pen=pg.mkPen('y', width=2))
p6.setLabel('left', 'Accel', units='m/s^2')
p6.setLabel('bottom', 'Time', units='s')
p6.showGrid(x=True, y=True)

# ウィンドウ表示
win.show()
sys.exit(app.exec_())




import sys
import numpy as np
from PyQt5 import QtWidgets
import pyqtgraph as pg

# === 設定 ===
filename = "data.txt"       # 読み込むファイル名
Fs = 10000                  # サンプリング周波数 [Hz]
start_time = 10             # FFT開始時間 [秒]
end_time = 15               # FFT終了時間 [秒]

# === データ読み込み ===
data = np.loadtxt(filename, skiprows=1)  # 1行目をスキップ
t = data[:, 0]
y = data[:, 1]

# === 指定区間の抽出 ===
mask = (t >= start_time) & (t <= end_time)
t_seg = t[mask]
y_seg = y[mask]

# === FFT計算 ===
N = len(y_seg)
Y = np.fft.fft(y_seg)
freq = np.fft.fftfreq(N, d=1/Fs)

# 正の周波数だけ抽出
pos_mask = freq >= 0
freq_pos = freq[pos_mask]
amp_pos = np.abs(Y[pos_mask]) * 2 / N

# === PyQtアプリ作成 ===
app = QtWidgets.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(show=True, title="Acceleration FFT Viewer")
win.resize(1000, 600)

# 上段プロット: 全体波形（青）＋FFT区間（赤）
p1 = win.addPlot(row=0, col=0)
p1.setLabel('bottom', "Time", units='s')
p1.setLabel('left', "Accel", units='m/s²')
p1.showGrid(x=True, y=True)
p1.plot(t, y, pen=pg.mkPen('b', width=1), name="All data")
p1.plot(t_seg, y_seg, pen=pg.mkPen('r', width=1), name="FFT range")

# 下段プロット: FFTスペクトル
p2 = win.addPlot(row=1, col=0)
p2.setLabel('bottom', "Frequency", units='Hz')
p2.setLabel('left', "Accel", units='m/s²')
p2.showGrid(x=True, y=True)
p2.setXRange(0, 500)
p2.plot(freq_pos, amp_pos, pen=pg.mkPen('r', width=1))

# 実行
sys.exit(app.exec_())
