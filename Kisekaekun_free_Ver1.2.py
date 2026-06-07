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

# 無料版Ver1.2のバージョン連動エクセル名
filename_ver = "Compass_free_Ver1.2.xlsx"

# --- 🛠️ 事前入力コントロール用のダミーコンポーネント配置 ---
# スマホ版で下半分をスクロールさせるため、値の取得だけを先に行う
uploaded_master = None
thresh_val = 128
p_color1, p_color2 = DEFAULT_COLORS["color_1"], DEFAULT_COLORS["color_5"]
p_file1, p_file2 = None, None
p_size1, p_size2 = 0.20, 0.20
display_width = 518

# --- ⚡ 2領域・高速画像合成ロジック（プレビューを先に出すために前置き） ---
preview_ready = False
preview_img = None

# 実際の入力処理はレイアウト内で共通化するため、変数の器を準備
if is_mobile:
    # スマホ用に、上部固定（シアター用）のカスタムCSSを注入！
    # 上から350px分を固定コンテナにして、残りのコンテンツを下にスクロールさせる魔法だよ
    st.markdown("""
        <style>
        @media (max-width: 767px) {
            .stMain {
                padding-top: 0px !important;
            }
            .mobile-fixed-header {
                position: fixed;
                top: 50px;
                left: 0;
                width: 100%;
                height: 330px;
                background-color: #0e1117;
                z-index: 999;
                padding: 10px;
                border-bottom: 2px solid #31333f;
                text-align: center;
                box-shadow: 0px 4px 10px rgba(0,0,0,0.5);
            }
            .mobile-scroll-body {
                margin-top: 350px;
            }
        }
        </style>
    """, unsafe_allow_html=True)

# --- 🛠️ レイアウトの出し分け ＆ データ入力 ---

if is_mobile:
    # プレビュー表示用の空箱を先に「画面最上部」に用意（固定ヘッダーの中身になるよ）
    fixed_header_area = st.empty()
    
    # ここから下が、指でスクロールできる入力エリア（下半分）
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
    p_file2 = st.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key="f_2_mob")
    p_size2 = st.slider(T["pattern_size"], 0.02, 0.80, 0.20, step=0.02, key="s_2_mob")
    
    display_width = 320

else:
    st.write("📸 お気に入りの写真をポイッと入れて、2色の和柄ポップアートを作ろう！")
    uploaded_master = st.sidebar.file_uploader(T["uploader_lbl"], type=["jpg", "jpeg", "png"], key="free_uploader_pc")
    display_width = st.sidebar.slider(T["slider_width"], 200, 1200, 518)
    
    st.sidebar.subheader("🌓 白黒のバランス調整")
    thresh_val = st.sidebar.slider("🌓 白黒の境界値（右に動かすと黒が増えるよ）", 10, 245, 128, step=1, key="thresh_pc")
    
    st.sidebar.subheader("🎨 色と柄のデザイン設定")
    st.sidebar.markdown("### ⬜ 領域①（明るい部分）")
    p_color1 = st.sidebar.color_picker(T["base_color"], DEFAULT_COLORS["color_1"], key="c_1_pc")
    p_file1 = st.sidebar.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key="f_1_pc")
    p_size1 = st.sidebar.slider(T["pattern_size"], 0.02, 0.80, 0.20, step=0.02, key="s_1_pc")
    
    st.sidebar.markdown("### ⬛ 領域②（暗い部分）")
    p_color2 = st.sidebar.color_picker(T["base_color"], DEFAULT_COLORS["color_5"], key="c_2_pc")
    p_file2 = st.sidebar.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key="f_2_pc")
    p_size2 = st.sidebar.slider(T["pattern_size"], 0.02, 0.80, 0.20, step=0.02, key="s_2_pc")

# RGB値の変換処理
rgb1 = (int(p_color1[1:3], 16), int(p_color1[3:5], 16), int(p_color1[5:7], 16))
rgb2 = (int(p_color2[1:3], 16), int(p_color2[3:5], 16), int(p_color2[5:7], 16))

all_settings = [
    {"id": "1", "rgb": rgb1, "uploaded_file": p_file1, "p_size": p_size1},
    {"id": "2", "rgb": rgb2, "uploaded_file": p_file2, "p_size": p_size2}
]

# 画像合成の実行
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
    preview_ready = True

# --- 🎬 最終レンダリング（スマホ固定 vs PC中央） ---
if preview_ready:
    if is_mobile:
        # スマホの時は、最初に作っておいた画面最上部の空箱に、固定枠（HTML）として画像をドーンと流し込む！
        with fixed_header_area:
            st.markdown('<div class="mobile-fixed-header">', unsafe_allow_html=True)
            st.image(preview_img, caption=f"Kakera | {filename_ver}", height=260)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        col_l, col_c, col_r = st.columns([1, 4, 1])
        with col_c:
            st.subheader(T["preview_hdr"])
            st.image(preview_img, caption=f"{T['caption_footer']} | 連動対象: {filename_ver}", width=display_width)
            st.success(T["success_msg"])
else:
    if is_mobile:
        with fixed_header_area:
            st.markdown('<div class="mobile-fixed-header" style="padding-top:80px; color:#aaa;">📸 写真を下にアップロードしてね</div>', unsafe_allow_html=True)
    else:
        st.info("💡 画面上のボタンから写真をアップロードすると、自動でポップアートに変身するよ！")