import streamlit as st
import cv2
import numpy as np
import random
import json
import os
from streamlit_javascript import st_javascript

"""
プロジェクト名: KAKERAプロジェクト - 着せ替えくん (無料版)
バージョン: Kisekaekun_free_Ver1.1
修正履歴:
- 2026-06-07: Kisekaekun_free_Ver1.0 初版リリース。
              ①販売戦略に基づいた「スマホファースト」のレスポンシブ画面自動切り替え機能を搭載。
              ②2領域（白と黒）に機能を絞ったお気軽版仕様。画像を読み込むと同時に自動で2分割。
              ③無料サーバーでも爆速で動くよう、スムージング・輪郭ラインを廃止した軽量・引き算設計。
              出力エクセル名も「Compass_free_Ver1.0.xlsx」に完全連動。
- 2026-06-07: Kisekaekun_free_Ver1.1 にバージョンアップ。
              ①販売担当（翔くん）の必須要件に基づき、スマホ表示時の「画面上下分割＆上半分プレビュー固定」に対応。
              ②CSS（position: fixed）を用いたカスタムレイアウトを実装し、操作中も常にプレビューが確認可能に。
              出力エクセル名も「Compass_free_Ver1.1.xlsx」に完全連動。
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
st.set_page_config(page_title="KAKERA きせかえくん free_Ver1.1", layout="wide")

# --- 🌐 言語切り替え設定 ---
selected_lang = st.selectbox("🌐 Language / 言語切り替え", list(LANG_DICT.keys()))
T = LANG_DICT[selected_lang]

st.title(f"🎨 {T['title']} - Free Ver1.1")
st.write("📸 お気に入りの写真をポイッと入れて、2色の和柄ポップアートを作ろう！")

# --- 🔓 画面サイズ（User-Agent/Window Width）の自動判定 ---
ui_width = st_javascript("window.innerWidth")

# スマホ（768px未満）かどうかの判定フラグ
is_mobile = bool(ui_width and ui_width < 768)

# 無料版のバージョン連動エクセル名
filename_ver = "Compass_free_Ver1.1.xlsx"

# --- 🎨 共通のカラー＆パターン変数初期化 ---
p_color1 = DEFAULT_COLORS["color_1"]
p_file1 = None
p_size1 = 0.20
p_color2 = DEFAULT_COLORS["color_5"]
p_file2 = None
p_size2 = 0.20
uploaded_master = None
display_width = 518

# --- ⚡ 先に画像を処理するロジック（プレビューを上部に固定するため、配置より前に計算） ---
preview_img = None
is_image_ready = False

# 一旦ユーザーの入力を受け取るための器を、スマホ/PCの条件分岐の前で定義するか、それぞれのフォームから取得する
# Streamlitの仕様上、キーの衝突を防ぎつつ画像ロジックを先に行うため、最初に入力部分をダミー定義せず、
# セッション状態（st.session_state）を利用して、後述のUIからの入力をリアルタイムに反映させるアプローチをとります。

# ユーザー入力値をセッションから取得、または初期化
if "c_1" not in st.session_state: st.session_state["c_1"] = DEFAULT_COLORS["color_1"]
if "c_2" not in st.session_state: st.session_state["c_2"] = DEFAULT_COLORS["color_5"]
if "s_1" not in st.session_state: st.session_state["s_1"] = 0.20
if "s_2" not in st.session_state: st.session_state["s_2"] = 0.20

# --- 🛠️ レイアウトの出し分け ---

if is_mobile:
    # --- 📱 スマホ版：上下分割＆上部固定レイアウト ---
    
    # CSSを注入して、上半分を固定、下半分をスクロール可能なコンテナにする
    st.markdown(
        """
        <style>
        /* 固定プレビューエリアの枠を設定 */
        .fixed-preview-container {
            position: fixed;
            top: 60px; /* タイトルや言語設定の下に配置 */
            left: 0;
            width: 100%;
            height: 40vh; /* 画面の高さの40%をプレビューに割り当て */
            background-color: #ffffff;
            z-index: 999;
            border-bottom: 2px solid #ccc;
            padding: 10px;
            box-sizing: border-box;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        /* スクロールする操作エリアの枠を設定 */
        .scrollable-controls-container {
            margin-top: 42vh; /* プレビューエリアの分だけ隙間をあける */
            padding-bottom: 50px;
        }
        </style>
        """,
        unsafe_allow_index=True
    )

    # プレビューコンテナの「箱」を先に定義（プレビュー画像は後からここに流し込むイメージですが、
    # Streamlitの仕様上、コードの実行順に描画されるため、先に画像処理を行うためにここで一度ダミーではなく
    # プレビュー用の st.empty() を作成しておきます）
    preview_placeholder = st.empty()

    # ここから下半分（操作エリア）
    st.markdown('<div class="scrollable-controls-container">', unsafe_allow_index=True)
    
    st.subheader("① 写真を選んでね / Upload Image")
    uploaded_master = st.file_uploader(T["uploader_lbl"], type=["jpg", "jpeg", "png"], key="free_uploader_mob")
    
    st.subheader("② 色と柄を選んでね / Design Palette")
    
    st.markdown("### ⬜ 領域①（明るい部分）")
    p_color1 = st.color_picker(T["base_color"], st.session_state["c_1"], key="c_1_mob")
    p_file1 = st.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key="f_1_mob")
    p_size1 = st.slider(T["pattern_size"], 0.02, 0.80, st.session_state["s_1"], step=0.02, key="s_1_mob")
    
    st.markdown("### ⬛ 領域②（暗い部分）")
    p_color2 = st.color_picker(T["base_color"], st.session_state["c_2"], key="c_2_mob")
    p_file2 = st.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key="f_2_mob")
    p_size2 = st.slider(T["pattern_size"], 0.02, 0.80, st.session_state["s_2"], step=0.02, key="s_2_mob")
    
    st.markdown('</div>', unsafe_allow_index=True)
    
    display_width = 320

else:
    # --- 💻 PC・タブレット版：従来の左右2カラムレイアウト ---
    uploaded_master = st.sidebar.file_uploader(T["uploader_lbl"], type=["jpg", "jpeg", "png"], key="free_uploader_pc")
    display_width = st.sidebar.slider(T["slider_width"], 200, 1200, 518)
    
    st.sidebar.subheader("🎨 色と柄のデザイン設定")
    
    st.sidebar.markdown("### ⬜ 領域①（明るい部分）")
    p_color1 = st.sidebar.color_picker(T["base_color"], st.session_state["c_1"], key="c_1_pc")
    p_file1 = st.sidebar.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key="f_1_pc")
    p_size1 = st.sidebar.slider(T["pattern_size"], 0.02, 0.80, st.session_state["s_1"], step=0.02, key="s_1_pc")
    
    st.sidebar.markdown("### ⬛ 領域②（暗い部分）")
    p_color2 = st.sidebar.color_picker(T["base_color"], st.session_state["c_2"], key="c_2_pc")
    p_file2 = st.sidebar.file_uploader(T["pattern_select"], type=["jpg", "jpeg", "png"], key="f_2_pc")
    p_size2 = st.sidebar.slider(T["pattern_size"], 0.02, 0.80, st.session_state["s_2"], step=0.02, key="s_2_pc")

# セッション状態に入力値を同期
st.session_state["c_1"] = p_color1
st.session_state["c_2"] = p_color2
st.session_state["s_1"] = p_size1
st.session_state["s_2"] = p_size2

# RGB値の変換処理
rgb1 = (int(p_color1[1:3], 16), int(p_color1[3:5], 16), int(p_color1[5:7], 16))
rgb2 = (int(p_color2[1:3], 16), int(p_color2[3:5], 16), int(p_color2[5:7], 16))

all_settings = [
    {"id": "1", "rgb": rgb1, "uploaded_file": p_file1, "p_size": p_size1},
    {"id": "2", "rgb": rgb2, "uploaded_file": p_file2, "p_size": p_size2}
]

# --- ⚡ 画像合成処理の実行 ---
if uploaded_master is not None:
    img = imread_uploaded(uploaded_master)
    h, w = img.shape[:2]
    
    result_img = np.zeros((h, w, 3), dtype=float)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    _, mask1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
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
    is_image_ready = True

# --- 📺 プレビューの最終描画（スマホ固定枠 or PC右カラム） ---
if is_mobile:
    if is_image_ready:
        # スマホ版の上部固定コンテナの中にプレビューを流し込む
        with preview_placeholder.container():
            st.markdown('<div class="fixed-preview-container">', unsafe_allow_index=True)
            st.image(preview_img, caption=f"Kakera Project | {filename_ver}", use_container_width=True)
            st.markdown('</div>', unsafe_allow_index=True)
    else:
        with preview_placeholder.container():
            st.markdown('<div class="fixed-preview-container">', unsafe_allow_index=True)
            st.info("💡 📸 写真をアップロードしてね！")
            st.markdown('</div>', unsafe_allow_index=True)
else:
    # PC版は今まで通り右側にどっしり表示
    if is_image_ready:
        col_l, col_c, col_r = st.columns([1, 4, 1])
        with col_c:
            st.subheader(T["preview_hdr"])
            st.image(preview_img, caption=f"{T['caption_footer']} | 連動対象: {filename_ver}", width=display_width)
            st.success(T["success_msg"])
    else:
        st.info("💡 画面上のボタンから写真をアップロードすると、自動でポップアートに変身するよ！")