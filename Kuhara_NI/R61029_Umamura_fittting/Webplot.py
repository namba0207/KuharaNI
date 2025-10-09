# 最適な抵抗値を比較するためのプログラム

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
# import japanize_matplotlib #日本語対応

# CSVファイルからデータを読み込む（圧力センサの力と抵抗値）
data = pd.read_csv('FSRsensor.csv')

# 圧力センサのデータ（力と抵抗値）を取得
force = data['Force'].values  # 圧力データ（g単位）データフレームの中から Force という名前の列（カラム）を取り出している．
resistance = data['Resistance'].values  # 抵抗データ（Ω単位）

# フィッティング関数を定義（べき乗、線形、二次、指数、対数）
def power_law(x, a, b):
    """べき乗関数の定義"""
    return a * np.power(x, b) # a * x^b の形

def linear(x, a, b):
    """線形関数の定義"""
    return a * x + b

def quadratic(x, a, b, c):
    """二次関数の定義"""
    return a * x**2 + b * x + c

def exponential(x, a, b):
    """指数関数の定義"""
    return a * np.exp(b * x) # a * e^(b * x) の形

def logarithmic(x, a, b):
    """対数関数の定義"""
    return a * np.log(x) + b # a * log(x) + b の形

# 各関数にフィッティングして最適パラメータを求める，何近似曲線でフィッティングするというところ．
params_power, _ = curve_fit(power_law, force, resistance, p0=[1, -1])  # べき乗関数フィット，p0は初期推定値を指定するためのオプション引数
params_linear, _ = curve_fit(linear, force, resistance)  # 線形関数フィット
params_quadratic, _ = curve_fit(quadratic, force, resistance)  # 二次関数フィット
params_exponential, _ = curve_fit(exponential, force, resistance, p0=[resistance[0], 0.01])  # 指数関数フィット
params_logarithmic, _ = curve_fit(logarithmic, force, resistance, p0=[1, 1])  # 対数関数フィット
#popt はフィッティングされた関数のパラメータ a と b の最適値であり、
# pcov はこれらのパラメータの不確かさや関係性を示す共分散行列

# フィットしたモデルで予測値を計算
resistance_fit_power = power_law(force, params_power[0], params_power[1]) #[0], [1]で，a, bの値がどういう値か？
resistance_fit_linear = linear(force, params_linear[0], params_linear[1])
resistance_fit_quadratic = quadratic(force, params_quadratic[0], params_quadratic[1], params_quadratic[2]) #[3] はc
resistance_fit_exponential = exponential(force, params_exponential[0], params_exponential[1])
resistance_fit_logarithmic = logarithmic(force, params_logarithmic[0], params_logarithmic[1])

# 決定係数（R²値）を計算する関数
def calculate_r_squared(actual, predicted):
    """R²値を計算"""
    residuals = actual - predicted  # 残差
    ss_res = np.sum(residuals**2)  # 残差平方和　モデルの誤差
    ss_tot = np.sum((actual - np.mean(actual))**2)  # 全体の平方和　データの総ばらつき
    r_squared = 1 - (ss_res / ss_tot)  # R²値　モデルの誤差/データの総ばらつきが小さければいい　0-1の間．R²値は0から1の範囲で表され、観測データとモデルによって予測されたデータの間の一致度を示す
    return r_squared

# 各関数に対するR²値を計算
r_squared_power = calculate_r_squared(resistance, resistance_fit_power)
r_squared_linear = calculate_r_squared(resistance, resistance_fit_linear)
r_squared_quadratic = calculate_r_squared(resistance, resistance_fit_quadratic)
r_squared_exponential = calculate_r_squared(resistance, resistance_fit_exponential)
r_squared_logarithmic = calculate_r_squared(resistance, resistance_fit_logarithmic)

# データとフィッティング結果を可視化するためにプロット
plt.figure(figsize=(12, 8))  # プロットのサイズを設定
plt.scatter(force, resistance, label='data', color='blue')  # 観測データを青の点で表示

# フィットした各モデルをプロット（色分けしてR²値を表示）
plt.plot(force, resistance_fit_power, 'r--', label=f'べき乗関数: $R^2$ = {r_squared_power:.4f}')
plt.plot(force, resistance_fit_linear, 'g--', label=f'線形関数: $R^2$ = {r_squared_linear:.4f}')
plt.plot(force, resistance_fit_quadratic, 'b--', label=f'二次関数: $R^2$ = {r_squared_quadratic:.4f}')
plt.plot(force, resistance_fit_exponential, 'c--', label=f'指数関数: $R^2$ = {r_squared_exponential:.4f}')
plt.plot(force, resistance_fit_logarithmic, 'm--', label=f'対数関数: $R^2$ = {r_squared_logarithmic:.4f}')

# 軸ラベルとグラフのタイトルを設定
plt.xlabel('圧力センサの力(g)')
plt.ylabel('圧力センサの抵抗値(Ω)')
plt.title('圧力センサデータへの各種関数フィッティング結果')

# 凡例とグリッドを追加
plt.legend()
plt.grid(True)

# 各関数の近似式とR²値をグラフに表示
textstr = '\n'.join((
    f'べき乗関数: y = {params_power[0]:.4f} * x^{params_power[1]:.4f} ($R^2$ = {r_squared_power:.4f})',
    f'線形関数: y = {params_linear[0]:.4f} * x + {params_linear[1]:.4f} ($R^2$ = {r_squared_linear:.4f})',
    f'二次関数: y = {params_quadratic[0]:.4f} * x^2 + {params_quadratic[1]:.4f} * x + {params_quadratic[2]:.4f} ($R^2$ = {r_squared_quadratic:.4f})',
    f'指数関数: y = {params_exponential[0]:.4f} * e^({params_exponential[1]:.4f} * x) ($R^2$ = {r_squared_exponential:.4f})',
    f'対数関数: y = {params_logarithmic[0]:.4f} * log(x) + {params_logarithmic[1]:.4f} ($R^2$ = {r_squared_logarithmic:.4f})'
))

# テキストボックスをプロット内に表示
props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
plt.gca().text(0.05, 0.95, textstr, transform=plt.gca().transAxes, fontsize=10,
               verticalalignment='top', bbox=props)

# グラフを表示
plt.show()

# 各関数のフィッティング結果とR²値をコンソールに出力
print(f'フィットされたべき乗関数: y = {params_power[0]:.4f} * x^{params_power[1]:.4f}')
print(f'R²値 (べき乗関数): {r_squared_power:.4f}')

print(f'フィットされた線形関数: y = {params_linear[0]:.4f} * x + {params_linear[1]:.4f}')
print(f'R²値 (線形関数): {r_squared_linear:.4f}')

print(f'フィットされた二次関数: y = {params_quadratic[0]:.4f} * x^2 + {params_quadratic[1]:.4f} * x + {params_quadratic[2]:.4f}')
print(f'R²値 (二次関数): {r_squared_quadratic:.4f}')

print(f'フィットされた指数関数: y = {params_exponential[0]:.4f} * e^({params_exponential[1]:.4f} * x)')
print(f'R²値 (指数関数): {r_squared_exponential:.4f}')

print(f'フィットされた対数関数: y = {params_logarithmic[0]:.4f} * log(x) + {params_logarithmic[1]:.4f}')
print(f'R²値 (対数関数): {r_squared_logarithmic:.4f}')

# %%