# 6chの記録データのグラフ化
# テキストファイルは同じ階層

import sys
import numpy as np
from PyQt5 import QtWidgets
import pyqtgraph as pg

# === データ読み込み ===
# data = np.loadtxt(r"C:\Users\tanak\Documents\Kuhara_NI\R61029_Umamura_fittting\result\recorded_data_20250821_152630.txt", skiprows=1)  # ここにファイル名を記入
data = np.loadtxt(r"C:\Users\tanak\Documents\Kuhara_NI\recorded_data_20250828_112539.txt", skiprows=1)  # ここにファイル名を記入
t = data[:, 0]    # 時間[秒]
y1 = data[:, 1]   # 振動データ1
y2 = data[:, 2]   # 振動データ2
y3 = data[:, 3]   # 仮にy1をコピー
y4 = data[:, 4]   # 仮にy2をコピー
y5 = data[:, 5]   # 仮にy1をコピー
y6 = data[:, 6]   # 仮にy2をコピー

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