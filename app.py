import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import os
import re
from datetime import date

# --- 1. 페이지 레이아웃 설정 ---
st.set_page_config(page_title="대학별 학과 제휴 혜택 지도 🗺️", layout="wide")
st.title("🗺️ 우리 학교 & 학과 맞춤형 제휴 혜택 지도")
st.markdown("학교와 학과를 선택하면, 해당 학생들을 위한 **특별 제휴 혜택**과 지도가 나타납니다!")

# --- 2. 영구 저장 시스템 (리뷰 및 방문자 수) ---
REVIEWS_FILE = "reviews.json"
VISITORS_FILE = "visitors.json"

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if "reviews" not in st.session_state:
    st.session_state.reviews = load_json(REVIEWS_FILE)

# --- 일별 방문자 수 체크 로직 ---
if "visited" not in st.session_state:
    st.session_state.visited = True
    today_str = str(date.today())
    visitors_data = load_json(VISITORS_FILE)
    
    visitors_data[today_str] = visitors_data.get(today_str, 0) + 1
    save_json(VISITORS_FILE, visitors_data)

# --- 3. 유틸리티 함수 (필터링 및 평점 계산) ---
BAD_WORDS = ["씨발", "시발", "병신", "개새끼", "지랄", "존나", "미친", "좆"]

def contains_bad_word(text):
    text_without_space = text.replace(" ", "")
    for word in BAD_WORDS:
        if word in text or word in text_without_space:
            return True
    return False

def get_avg_rating(store_name):
    if store_name in st.session_state.reviews and st.session_state.reviews[store_name]:
        scores = [r.get("점수", 0) for r in st.session_state.reviews[store_name] if "점수" in r]
        if scores:
            return round(sum(scores) / len(scores), 1)
    return 0.0

# --- 4. 🛠️ 관리자 모드 ---
st.sidebar.markdown("---")
admin_password = st.sidebar.text_input(" ", type="password", placeholder="관리자 코드 입력")

if admin_password == "7777":