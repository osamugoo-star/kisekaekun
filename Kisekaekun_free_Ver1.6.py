import streamlit as st
import cv2
import numpy as np
import random
import json
import os

# プロジェクト名: KAKERAプロジェクト - 着せ替えくん (無料版)
# バージョン: Kisekaekun_free_Ver1.6
# 出力エクセル名: Compass_free_Ver1.6.xlsx

# --- 📁 外部パラメータ（settings.json）の読み込み ---
CONFIG_FILE = "settings.json"

@st.cache_data
def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        st.error(f"⚠️ {CONFIG_FILE} が見つかりません。プログラムと同じフォルダに配置してください。")
        st.stop()

CONFIG = load_settings()
DEFAULT_COLORS = CONFIG["DEFAULT_COLORS"]
LANG_DICT = CONFIG["LANGUAGES"]

def imread_uploaded(uploaded_file):
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    return cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

def create_seamless_tile(img):
    tile = img.copy()
    tile_h = cv2.flip(tile, 1); tile_v = cv2.flip(tile, 0); tile_hv = cv2.flip(tile, -1)
    return np.vstack((np.hstack((tile, tile_h)), np.hstack((tile_v, tile_hv))))

# 画面全体の初期設定（スマホ・PCどちらでも美しく収まる標準幅に設定）
st.set_page_config(page_title="KAKERA きせかえくん free_Ver1.6", layout="centered")

# --- 🌐 言語切り替え設定 ---
selected_lang = st.selectbox("🌐 Language / 言語切り替え", list(LANG_DICT.keys()))
T = LANG_DICT[selected_lang]

st.title(f"🎨 {T['title']} - Free Ver1.6")

filename_ver = "Compass_free_Ver1.6.xlsx"

# --- 🎬 100%バグらない最上部プレビューエリア（CSSの無理な固定を完全撤廃！） ---
preview_area = st.empty()

# --- 🛠️ 順番に並ぶ安心の操作メニュー ---
st.subheader("① 写真を選んでね / Upload Image")
uploaded_master = st.file_uploader(T["uploader_lbl"], type=["jpg", "jpeg", "png"], key="free_uploader_v16")

st.subheader("② 白黒のバランス調整 / Threshold")
thresh_val = st.slider("🌓 白黒の境界値（右に動かすと黒が増えるよ）", 10, 245, 128, step=1, key="thresh_v16")

st.subheader("③ 色と柄を選んでね / Design Palette")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### ⬜ 領域①（明るい部分）")
    p_color1 = st.color_picker(T["base_color"], DEFAULT_COLORS["color_1"], key="c_1_v16")
    p_file1 = st.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key="f_1_v16")
    p_size1 = st.slider(T["pattern_size"], 0.02, 0.80, 0.20, step=0.02, key="s_1_v16")

with col_right:
    st.markdown("### ⬛ 領域②（暗い部分）")
    p_color2 = st.color_picker(T["base_color"], DEFAULT_COLORS["color_5"], key="c_2_v16")
    p_file2 = st.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key="f_2_v16")
    p_size2 = st.slider(T["pattern_size"], 0.02, 0.80, 0.20, step=0.02, key="s_2_v16")

# RGB値の変換
rgb1 = (int(p_color1[1:3], 16), int(p_color1[3:5], 16), int(p_color1[5:7], 16))
rgb2 = (int(p_color2[1:3], 16), int(p_color2[3:5], 16), int(p_color2[5:7], 16))

all_settings = [
    {"id": "1", "rgb": rgb1, "uploaded_file": p_file1, "p_size": p_size1},
    {"id": "2", "rgb": rgb2, "uploaded_file": p_file2, "p_size": p_size2}
]

# --- ⚡ 画像合成 ＆ 表示ロジック ---
if uploaded_master is not None:
    img = imread_uploaded(uploaded_master)
    h, w = img.shape[:2]
    
    result_img = np.zeros((h, w, 3), dtype=float)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    _, mask1 = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
    mask2 = cv2.bitwise_not(mask1)
    
    process_order = [("1", mask1), ("2", mask2)]
    random.seed(42)
    
    for part_id, refined_mask in process_order:
        s = next(item for item in all_settings if item["id"] == part_id)
        alpha_mask = refined_mask.astype(float) / 255.0
        color_layer = np.full((h, w, 3), [s["rgb"][2], s["rgb"][1], s["rgb"][0]], dtype=float)
        
        if s["uploaded_file"] is not None:
            p_img = imread_uploaded(s["uploaded_file"])
            scale = s["p_size"]
            p_res = cv2.resize(p_img, (max(1, int(p_img.shape[1] * scale)), max(1, int(p_img.shape[0] * scale))), interpolation=cv2.INTER_AREA)
            seamless = create_seamless_tile(p_res)
            sth, stw = seamless.shape[:2]
            x_off, y_off = random.randint(0, stw - 1), random.randint(0, sth - 1)
            tiled = np.tile(seamless, (h // sth + 2, w // stw + 2, 1))[y_off:y_off+h, x_off:x_off+w].astype(float) / 255.0
            blend_layer = color_layer * tiled
        else:
            blend_layer = color_layer
            
        result_img = (blend_layer * alpha_mask[:,:,np.newaxis]) + (result_img * (1.0 - alpha_mask[:,:,np.newaxis]))
        
    preview_img = cv2.cvtColor(result_img.clip(0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB)
    
    # 100%絶対に表示が消えない頑丈な標準命令で、最上部に美しく画像を配置！
    with preview_area:
        st.image(preview_img, caption=f"Kakera | {filename_ver}", use_container_width=True)
        st.success("🎉 綺麗に着せ替えできたよ！下のメニューを動かして楽しんでね。")
else:
    with preview_area:
        st.info("💡 下の①から写真を選ぶと、ここに完成画像が綺麗に表示されるよ！")