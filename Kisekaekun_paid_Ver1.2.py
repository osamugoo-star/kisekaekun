import streamlit as st
import cv2
import numpy as np
import random
import json
import os

"""
プロジェクト名: KAKERAプロジェクト - 着せ替えくん (製品版)
バージョン: Kisekaekun_paid_Ver1.2
修正履歴:
- 2026-06-06: Kisekaekun_paid_Ver1.0 初版リリース。パスワード認証機能を搭載。
- 2026-06-06: Kisekaekun_paid_Ver1.1 鈴木英人風アートへの進化（MeanShiftフィルタ導入、Cannyによるエッジ線）。
- 2026-06-06: Kisekaekun_paid_Ver1.2 領域境界ライン化大改造。
              ①写真の輪郭（エッジ）ではなく、おとうくんが指定した5つのトーン領域の「すべての境目」に黒ラインを引くロジックへ刷新。
              ②ラインの太さを 0〜10（旧1〜5）までダイナミックに指定できるよう拡張。
              連動するエクセル名も「Compass_paid_Ver1.2.xlsx」へ完全連動。
"""

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

# セッション状態のリセット用初期化
if "reset_count" not in st.session_state:
    st.session_state["reset_count"] = 0

def force_reset():
    for key in list(st.session_state.keys()):
        if key != "reset_count" and key != "authenticated":
            del st.session_state[key]

st.set_page_config(page_title="KAKERA きせかえくん paid_Ver1.2", layout="wide")

# --- 🔑 クローズドテスト用 パスワード認証ロジック ---
CORRECT_PASSWORD = "kisekae196705"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 KAKERA Project: Kisekaekun Paid Version")
    st.write("このアプリはクローズドテスト用の製品版（Paid Version）です。")
    
    input_password = st.text_input("パスワードを入力してください / Enter Password", type="password")
    if st.button("ログイン / Login"):
        if input_password == CORRECT_PASSWORD:
            st.session_state["authenticated"] = True
            st.success("認証に成功しました！アプリを起動します。")
            st.rerun()
        else:
            st.error("パスワードが正しくありません / Incorrect Password")
    st.stop()

# --- 🔓 認証後のフル機能 UI ---
selected_lang = st.sidebar.selectbox("🌐 Language / 言語切り替え", list(LANG_DICT.keys()))
T = LANG_DICT[selected_lang]

st.title(f"🎨 {T['title']} - Paid Ver1.2")
st.sidebar.header(T["sidebar_hdr"])

if st.sidebar.button(T["reset_btn"]):
    st.session_state["reset_count"] += 1
    force_reset()
    st.rerun()

r_idx = st.session_state["reset_count"]

# ① 元画像の読み込み
uploaded_master = st.sidebar.file_uploader(T["uploader_lbl"], type=["jpg", "jpeg", "png"], key=f"master_uploader_{r_idx}")

# ② 画面・全体設定
st.sidebar.subheader(T["step2"])
display_width = st.sidebar.slider(T["slider_width"], 200, 1200, 640)
smooth_strength = st.sidebar.slider(T["slider_smooth"], 0, 30, 0, key=f"smooth_{r_idx}")
# 【Ver1.2拡張仕様】輪郭ラインの太さを 0〜10 まで選択可能に変更
line_thickness = st.sidebar.slider(T["slider_line"], 0, 10, 0, key=f"line_{r_idx}")

# ③ 5レイヤー境界設定
st.sidebar.subheader(T["step3"])
st.sidebar.caption(T["thresh_caption"])
thresh_1 = st.sidebar.slider(T["thresh1_lbl"], 0, 255, 180, key=f"th1_{r_idx}")
thresh_2 = st.sidebar.slider(T["thresh2_lbl"], 0, 255, 130, key=f"th2_{r_idx}")
thresh_3 = st.sidebar.slider(T["thresh3_lbl"], 0, 255, 80, key=f"th3_{r_idx}")
thresh_4 = st.sidebar.slider(T["thresh4_lbl"], 0, 255, 30, key=f"th4_{r_idx}")

sorted_thresh = sorted([thresh_1, thresh_2, thresh_3, thresh_4])
v1, v2, v3, v4 = sorted_thresh[0], sorted_thresh[1], sorted_thresh[2], sorted_thresh[3]

PARTS_CONFIG = [
    {"id": "1", "name": T["p1"], "default_color": DEFAULT_COLORS["color_1"], "emoji": "⬜"},
    {"id": "2", "name": T["p2"], "default_color": DEFAULT_COLORS["color_2"], "emoji": "🥈"},
    {"id": "3", "name": T["p3"], "default_color": DEFAULT_COLORS["color_3"], "emoji": "🪙"},
    {"id": "4", "name": T["p4"], "default_color": DEFAULT_COLORS["color_4"], "emoji": "🥇"},
    {"id": "5", "name": T["p5"], "default_color": DEFAULT_COLORS["color_5"], "emoji": "⬛"}
]

st.sidebar.subheader(T["step4"])
all_settings = []
for part in PARTS_CONFIG:
    with st.sidebar.expander(f"{part['emoji']} {part['name']}"):
        p_color = st.color_picker(T["base_color"], part["default_color"], key=f"c_{part['id']}_{r_idx}")
        r, g, b = int(p_color[1:3], 16), int(p_color[3:5], 16), int(p_color[5:7], 16)
        
        p_file = st.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key=f"f_{part['id']}_{r_idx}")
        p_size_val = st.sidebar.slider(T["pattern_size"], 0.02, 0.80, 0.20, step=0.02, key=f"s_{part['id']}_{r_idx}")
        
        all_settings.append({
            "id": part["id"],
            "rgb": (r, g, b), 
            "uploaded_file": p_file, 
            "p_size": p_size_val
        })

# --- 画像合成ロジック ---
if uploaded_master is not None:
    img = imread_uploaded(uploaded_master)
    h, w = img.shape[:2]
    
    if smooth_strength > 0:
        spatial_radius = int(smooth_strength * 0.5) + 5
        color_radius = int(smooth_strength * 0.8) + 10
        processed_img = cv2.pyrMeanShiftFiltering(img, spatial_radius, color_radius)
    else:
        processed_img = img.copy()
        
    result_img = np.zeros((h, w, 3), dtype=float)
    gray = cv2.cvtColor(processed_img, cv2.COLOR_BGR2GRAY)
    
    # 4つの境界値で5枚のベースマスクを正確に抽出
    _, mask5_inv = cv2.threshold(gray, v1, 255, cv2.THRESH_BINARY)
    mask5 = cv2.bitwise_not(mask5_inv)
    
    _, mask4_raw1 = cv2.threshold(gray, v1, 255, cv2.THRESH_BINARY)
    _, mask4_raw2 = cv2.threshold(gray, v2, 255, cv2.THRESH_BINARY)
    mask4 = cv2.bitwise_and(mask4_raw1, cv2.bitwise_not(mask4_raw2))
    
    _, mask3_raw1 = cv2.threshold(gray, v2, 255, cv2.THRESH_BINARY)
    _, mask3_raw2 = cv2.threshold(gray, v3, 255, cv2.THRESH_BINARY)
    mask3 = cv2.bitwise_and(mask3_raw1, cv2.bitwise_not(mask3_raw2))
    
    _, mask2_raw1 = cv2.threshold(gray, v3, 255, cv2.THRESH_BINARY)
    _, mask2_raw2 = cv2.threshold(gray, v4, 255, cv2.THRESH_BINARY)
    mask2 = cv2.bitwise_and(mask2_raw1, cv2.bitwise_not(mask2_raw2))
    
    _, mask1 = cv2.threshold(gray, v4, 255, cv2.THRESH_BINARY)
    
    process_order = [("5", mask5), ("4", mask4), ("3", mask3), ("2", mask2), ("1", mask1)]
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
        
    # 【Ver1.2新ロジック】すべての領域の「境界のキワ」に一律でラインを引く
    if line_thickness > 0:
        # 各マスクの内側の境界線（エッジ）をラプラシアンまたは勾配で検出
        combined_edges = np.zeros((h, w), dtype=np.uint8)
        
        for _, mask in process_order:
            # 各領域の輪郭線を見つけるために、グラディエント（膨張 - 収縮）を計算
            kernel_edge = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            dilated = cv2.dilate(mask, kernel_edge)
            eroded = cv2.erode(mask, kernel_edge)
            edge = cv2.subtract(dilated, eroded)
            combined_edges = cv2.bitwise_or(combined_edges, edge)
            
        # スライダーの太さに応じて境界線を太らせる
        kernel_line = np.ones((line_thickness, line_thickness), np.uint8)
        dilated_lines = cv2.dilate(combined_edges, kernel_line)
        
        # 境界線部分を完全な黒にするためのマスク
        all_line_mask = (dilated_lines == 0).astype(float)[:, :, np.newaxis]
        result_img = result_img * all_line_mask
        
    preview_img = cv2.cvtColor(result_img.clip(0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB)
    
    # バージョン連動
    filename_ver = "Compass_paid_Ver1.2.xlsx"
    
    col_l, col_c, col_r = st.columns([1, 4, 1])
    with col_c:
        st.subheader(T["preview_hdr"])
        st.image(preview_img, caption=f"{T['caption_footer']} | 連動対象: {filename_ver}", width=display_width)
        st.success(T["success_msg"])
else:
    st.info(T["info_msg"])