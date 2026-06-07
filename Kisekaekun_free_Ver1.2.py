import streamlit as st
import cv2
import numpy as np
import random
import json
import os
from streamlit_javascript import st_javascript

"""
プロジェクト名: KAKERAプロジェクト - 着せ替えくん (無料版)
バージョン: Kisekaekun_free_Ver1.2
修正履歴:
- 2026-06-07: Kisekaekun_free_Ver1.0 初版リリース。
              ①販売戦略に基づいた「スマホファースト」のレスポンシブ画面自動切り替え機能を搭載。
              ②2領域（白と黒）に機能を絞ったお気軽版仕様。画像を読み込むと同時に自動で2分割。
              ③無料サーバーでも爆速で動くよう、スムージング・輪郭ラインを廃止した軽量・引き算設計。
              出力エクセル名も「Compass_free_Ver1.0.xlsx」に完全連動。
- 2026-06-07: Kisekaekun_free_Ver1.1 
              ①実際の写真（ブラピ等のポートレート）で白飛び・顔の潰れが発生する不具合を解消。
              ②完全自動（大津の二値化）を廃止し、手動で影のバランスを調整できる「白黒の境界値スライダー」を新設。
              出力エクセル名も「Compass_free_Ver1.1.xlsx」に連動更新。
- 2026-06-07: Kisekaekun_free_Ver1.2
              ①スマホ操作時の手触りをさらに追求。画面上部に完成画像を固定表示（ピン留め）するCSSカスタムを実装。
              ②下半分のスライダーを動かした瞬間に、上の画像がリアルタイムに変わる「シアターモード」を搭載。
              ③【バグ修正】画像未アップロード時に「preview_img」が未定義で発生するNameErrorを完全に解消。
              出力エクセル名も「Compass_free_Ver1.2.xlsx」に連動更新。
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

# 画面全体の初期設定
st.set_page_config(page_title="KAKERA きせかえくん free_Ver1.2", layout="wide")

# --- 🌐 言語切り替え設定 ---
selected_lang = st.selectbox("🌐 Language / 言語切り替え", list(LANG_DICT.keys()))
T = LANG_DICT[selected_lang]

st.title(f"🎨 {T['title']} - Free Ver1.2")

# --- 🔓 画面サイズ（User-Agent/Window Width）の自動判定 ---
ui_width = st_javascript("window.innerWidth")
is_mobile = bool(ui_width and ui_width < 768)

filename_ver = "Compass_free_Ver1.2.xlsx"

# --- 🎨 スマホ専用の固定ヘッダーCSSの注入 ---
if is_mobile:
    st.markdown("""
        <style>
        @media (max-width: 767px) {
            .stMain { padding-top: 0px !important; }
            .mobile-fixed-header {
                position: fixed; top: 50px; left: 0; width: 100%; height: 330px;
                background-color: #0e1117; z-index: 999; padding: 10px;
                border-bottom: 2px solid #31333f; text-align: center;
                box-shadow: 0px 4px 10px rgba(0,0,0,0.5);
            }
            .mobile-scroll-body { margin-top: 350px; }
        }
        </style>
    """, unsafe_allow_html=True)

# --- 🛠️ レイアウトの出し分け ＆ データ入力 ---
if is_mobile:
    # 画面最上部にプレビュー用の固定枠を確保
    fixed_header_area = st.empty()
    st.markdown('<div class="mobile-scroll-body"></div>', unsafe_allow_html=True)
    
    st.subheader("① 写真を選んでね / Upload Image")
    uploaded_master = st.file_uploader(T["uploader_lbl"], type=["jpg", "jpeg", "png"], key="free_uploader_mob")
    
    st.subheader("② 白黒のバランス調整 / Threshold")
    thresh_val = st.slider("🌓 白黒の境界値（右に動かすと黒が増えるよ）", 10, 245, 128, step=1, key="thresh_mob")
    
    st.subheader("③ 色と柄を選んでね / Design Palette")
    st.markdown("### ⬜ 領域①（明るい部分）")
    p_color1 = st.color_picker(T["base_color"], DEFAULT_COLORS["color_1"], key="c_1_mob")
    p_file1 = st.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key="f_1_mob")
    p_size1 = st.slider(T["pattern_size"], 0.02, 0.80, 0.20, step=0.02, key="s_1_mob")
    
    st.markdown("### ⬛ 領域②（暗い部分）")
    p_color2 = st.color_picker(T["base_color"], DEFAULT_COLORS["color_5"], key="c_2_mob")
    p_file2 = st.file_uploader(T["pattern_select"], type=