# nanを0に変換するプログラム

import os

# ファイル名とパスの設定
input_file = "/Users/sanolab/Documents/python/test_venv/R61029_Umamura_fittting/rawdata/data_kouseiRT3.txt"  # ここに元のファイル名を記入
output_folder = "/Users/sanolab/Documents/python/test_venv/R61029_Umamura_fittting/result"
output_file = os.path.join(output_folder, "data_kouseiRT3.txt")

# 出力フォルダが存在しない場合、フォルダを作成
os.makedirs(output_folder, exist_ok=True)

# ファイルの読み込みと書き換え
with open(input_file, "r") as file:
    lines = file.readlines()
    

# 新しい内容を保存
with open(output_file, "w") as file:
    for line in lines:
        # ヘッダー行かどうか確認
        if line.startswith("%") or line.strip() == "":
            file.write(line)
        else:
            line = line.replace('[', '').replace(']', '')
            values = line.replace(',', '').split()
            modified_values = [
                # f"{float(values[0]):.6f}",                   # %Time[s]を小数点以下6桁に
                f"{max(0.0, float(values[0])):.6f}",         # Fz[N]を小数点以下6桁に
                f"{max(0.0, float(values[1])):.6f}"          # Vout[V]を小数点以下6桁に
            ]
            file.write(" ".join(modified_values) + "\n")

print("変換が完了しました！編集したファイルは'result'フォルダに保存されています。")
