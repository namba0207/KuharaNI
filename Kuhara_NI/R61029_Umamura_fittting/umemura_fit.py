# %%
import sys
import numpy as np
from scipy.optimize import curve_fit
from PyQt5 import QtWidgets
import pyqtgraph as pg

#####----- テキストファイルの読み込み -----#####
# 仮にCSV/テキストで空白区切りのデータとする
data = np.loadtxt(r"C:\Users\tanak\Documents\Kuhara_NI\R61029_Umamura_fittting\0822\recorded_data_20250822_095644.txt", skiprows=1)  # ここにファイル名を記入
x_data = -data[:, 6]
y_data = data[:, 3]
# data = np.loadtxt(r"C:\Users\tanak\Documents\Kuhara_NI\R61029_Umamura_fittting\result_1209\data_kouseiRT1.txt", skiprows=1)  # ここにファイル名を記入
# x_data = data[:, 0]
# y_data = data[:, 1]
#####----- テキストファイルの読み込み -----#####

# 正の値のみ
mask = (x_data > 0) & (y_data > 0)
x_data = x_data[mask]
y_data = y_data[mask]

# 定数 Rm
Rm = 1000

# 近似曲線の関数定義
def model(x, a, b):
    return 5 * Rm / (Rm + a * x**b)

# 曲線フィッティング
params, covariance = curve_fit(model, x_data, y_data, p0=[1000, 1], bounds=([0,-1],[1e5,5]))
a, b = params

print(f"推定値: a = {a:.4f}, b = {b:.4f}")

# フィット曲線用のデータ生成（x範囲をソートして滑らかにする）
x_fit = np.linspace(np.min(x_data), np.max(x_data), 500)
y_fit = model(x_fit, a, b)

# PyQt5 アプリケーション
app = QtWidgets.QApplication(sys.argv)

# pyqtgraph プロットウィンドウ
win = pg.GraphicsLayoutWidget(show=True, title="Data and Fit Curve")
plot = win.addPlot(title="data and fit curve")
plot.setLabel('bottom', 'x')
plot.setLabel('left', 'y')

# 元データの散布図（青）
plot.plot(x_data, y_data, pen=None, symbol='o', symbolSize=8, symbolBrush='b', name="data")

# フィット曲線（赤線）
plot.plot(x_fit, y_fit, pen=pg.mkPen('r', width=2), name="fit curve")

# 凡例を追加
legend = plot.addLegend()

# 実行
if __name__ == "__main__":
    sys.exit(app.exec_())
