import streamlit as st
import cv2
import numpy as np
import random
import json
import os

"""
プロジェクト名: KAKERAプロジェクト - 着せ替えくん (製品版)
バージョン: Kisekaekun_paid_Ver1.0
修正履歴:
- 2026-06-06: app_Ver5.8 の安定した5ヶ国語5階調ロジックを完全継承。
              製品化ロードマップに基づき、ファイル名・バージョン名を「Kisekaekun_paid_Ver1.0」へ刷新。
              連動するエクセル名も「Compass_paid_Ver1.0.xlsx」へ連動変更。
              クローズドテスト用に、コード内直接指定によるパスワード認証機能（kisekae196705）を実装。
              正しいパスワードが入力されるまで、アプリの全機能を完全にロックするガードレールを配置。
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

st.set_page_config(page_title="KAKERA きせかえくん paid_Ver1.0", layout="wide")

# --- 🔑 クローズドテスト用 パスワード認証ロジック ---
CORRECT_PASSWORD = "kisekae196705"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# パスワードがまだ通っていない場合は認証画面を表示してシャットアウト
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
    st.stop()  # 認証されるまでこれ以降のコードは絶対に実行させない

# --- 🔓 ここから認証後のフル機能 UI ---
# --- 🌐 5ヶ国語対応 言語選択ボックス ---
selected_lang = st.sidebar.selectbox("🌐 Language / भाषा / 言語切り替え", list(LANG_DICT.keys()))
T = LANG_DICT[selected_lang]

# 画面タイトルを有料版表記にオーバーライド
st.title(f"🎨 {T['title']} - Paid Ver1.0")
st.sidebar.header(T["sidebar_hdr"])

# ① 完全リセットボタン
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

# ③ 5階調マスク境界設定
st.sidebar.subheader(T["step3"])
st.sidebar.caption(T["thresh_caption"])
thresh_1 = st.sidebar.slider(T["thresh1_lbl"], 0, 255, 180, key=f"th1_{r_idx}")
thresh_2 = st.sidebar.slider(T["thresh2_lbl"], 0, 255, 130, key=f"th2_{r_idx}")
thresh_3 = st.sidebar.slider(T["thresh3_lbl"], 0, 255, 80, key=f"th3_{r_idx}")
thresh_4 = st.sidebar.slider(T["thresh4_lbl"], 0, 255, 30, key=f"th4_{r_idx}")

# 安全にソートして4つの境界値を確定
sorted_thresh = sorted([thresh_1, thresh_2, thresh_3, thresh_4])
v1, v2, v3, v4 = sorted_thresh[0], sorted_thresh[1], sorted_thresh[2], sorted_thresh[3]

# 5領域の設定定義
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
    
    result_img = np.zeros((h, w, 3), dtype=float)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 4つの境界値で5枚のベースマスクを抽出
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
    
    for part_id, raw_mask in process_order:
        s = next(item for item in all_settings if item["id"] == part_id)
        
        if smooth_strength > 0:
            calculated_val = float(smooth_strength) / 6.0
            g_size = int(calculated_val) * 2 + 1
            if g_size < 3: 
                g_size = 3
                
            blurred = cv2.GaussianBlur(raw_mask, (g_size, g_size), 0)
            _, refined_mask = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
        else:
            refined_mask = raw_mask
            
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
    
    # 【バージョン連動】出力ファイル名を有料版Ver1.0に連動！
    filename_ver = "Compass_paid_Ver1.0.xlsx"
    
    col_l, col_c, col_r = st.columns([1, 4, 1])
    with col_c:
        st.subheader(T["preview_hdr"])
        st.image(preview_img, caption=f"{T['caption_footer']} | 連動対象: {filename_ver}", width=display_width)
        st.success(T["success_msg"])
else:
    st.info(T["info_msg"])