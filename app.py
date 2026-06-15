import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import os
import re
import datetime # 변경: 서버 시차 해결을 위해 datetime 모듈 전체를 가져옵니다.

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

# --- 일별 방문자 수 체크 로직 (한국 시간 KST 적용) ---
if "visited" not in st.session_state:
    st.session_state.visited = True
    
    # 🛠️ 서버가 외부에 있어도 무조건 한국 시간(+9시간) 기준으로 날짜를 생성합니다.
    kst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    today_str = kst_now.strftime("%Y-%m-%d")
    
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
    st.header("📈 제휴 혜택 관리자 대시보드")
    st.markdown("누적 방문자 및 후기 데이터를 기반으로 한 통계입니다.")
    
    st.subheader("👥 일별 사이트 방문자 수")
    visitors_data = load_json(VISITORS_FILE)
    if visitors_data:
        df_visitors = pd.DataFrame(list(visitors_data.items()), columns=["날짜", "방문자수"])
        df_visitors = df_visitors.sort_values(by="날짜")
        
        # 🛠️ 대시보드 조회 시점에도 한국 시간 기준으로 오늘 방문자 데이터를 매칭합니다.
        kst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        today_str = kst_now.strftime("%Y-%m-%d")
        
        today_val = visitors_data.get(today_str, 0)
        total_val = sum(visitors_data.values())
        v_col1, v_col2 = st.columns(2)
        v_col1.metric(label="오늘 방문자 수", value=f"{today_val} 명")
        v_col2.metric(label="총 누적 방문자 수", value=f"{total_val} 명")
        
        st.line_chart(df_visitors.set_index("날짜"))
    else:
        st.info("방문자 데이터가 없습니다.")
        
    st.divider()
    
    if st.session_state.reviews:
        all_reviews = []
        for store, reviews in st.session_state.reviews.items():
            for r in reviews:
                all_reviews.append({
                    "가게이름": store,
                    "점수": r.get("점수", 0),
                    "후기내용": r["내용"]
                })
        
        df_reviews = pd.DataFrame(all_reviews)
        
        st.subheader("📝 리뷰 통계")
        col1, col2, col3 = st.columns(3)
        col1.metric(label="총 누적 후기 수", value=f"{len(df_reviews)} 개")
        col2.metric(label="전체 평균 평점", value=f"{round(df_reviews['점수'].mean(), 2)} 점")
        col3.metric(label="리뷰가 등록된 업체 수", value=f"{df_reviews['가게이름'].nunique()} 곳")
        
        st.subheader("📊 제휴 업체별 평균 평점")
        avg_scores = df_reviews.groupby('가게이름')['점수'].mean().reset_index()
        st.bar_chart(data=avg_scores, x='가게이름', y='점수', use_container_width=True)
        
        st.subheader("🔥 가장 리뷰가 많은 핫플레이스 TOP 5")
        review_counts = df_reviews['가게이름'].value_counts().head(5)
        st.bar_chart(review_counts, use_container_width=True)
        
        with st.expander("원본 후기 데이터 열람 (Raw Data)"):
            st.dataframe(df_reviews)
    else:
        st.info("아직 등록된 후기 데이터가 없습니다.")
        
    st.stop()

elif admin_password != "":
    st.sidebar.error("⚠️ 잘못된 코드입니다.")

# ==========================================
# --- 5. 👨‍🎓 일반 사용자 모드 (지도 및 혜택 표시) ---
# ==========================================

try:
    df = pd.read_csv("store_data.csv", header=None, encoding="utf-8")
    
    if df.shape[1] >= 7:
        df = df[[0, 1, 2, 3, 4, 5, 6]]
        df.columns = ["학교", "단과대", "이름", "카테고리", "혜택", "위도", "경도"]
    else:
        st.error("⚠️ 엑셀 파일의 데이터 칸(G열까지)이 부족합니다. 구조를 확인해 주세요!")
        st.stop()

    for col in ["학교", "단과대", "이름", "카테고리", "혜택"]:
        df[col] = df[col].fillna("정보없음").astype(str).str.strip()

    df["위도"] = pd.to_numeric(df["위도"], errors='coerce')
    df["경도"] = pd.to_numeric(df["경도"], errors='coerce')
    df = df.dropna(subset=["위도", "경도"])

    st.sidebar.header("🔍 맞춤 조건 선택")
    
    school_list = sorted(df["학교"].unique().tolist())
    selected_school = st.sidebar.selectbox("1. 대학교를 선택하세요:", school_list)
    df_school = df[df["학교"] == selected_school]
    
    dept_list = sorted(df_school["단과대"].unique().tolist())
    selected_dept = st.sidebar.selectbox("2. 학과/단과대를 선택하세요:", dept_list)
    df_dept = df_school[df_school["단과대"] == selected_dept]
    
    category_list = ["전체보기", "밥집", "술집", "오락시설", "카페"]
    selected_category = st.sidebar.selectbox("3. 가게 종류를 선택하세요:", category_list)

    if selected_category != "전체보기":
        df_filtered = df_dept[df_dept["카테고리"].str.contains(selected_category)]
    else:
        df_filtered = df_dept

    col1, col2 = st.columns([2, 1])

    with col1:
        if not df_filtered.empty:
            map_center = [df_filtered["위도"].iloc[0], df_filtered["경도"].iloc[0]]
        else:
            map_center = [36.6253, 127.4574]
            
        m = folium.Map(location=map_center, zoom_start=16)
        color_map = {"밥집": "red", "술집": "purple", "카페": "orange", "오락시설": "blue"}

        for idx, row in df_filtered.iterrows():
            marker_color = "gray"
            for cat, color in color_map.items():
                if cat in row["카테고리"]:
                    marker_color = color
                    break
            
            avg_rate = get_avg_rating(row['이름'])
            short_benefit = str(row['혜택'])[:15] + "..." if len(str(row['혜택'])) > 15 else str(row['혜택'])
            
            popup_html = f"""
            <div style='font-family: sans-serif; min-width: 160px;'>
                <h4 style='margin:0;'>{row['이름']}</h4>
                <p style='margin: 3px 0; color: #f39c12; font-weight: bold;'>★ {avg_rate} / 5.0</p>
                <p style='margin:0; font-size: 13px; color: #2c3e50;'><b>핵심혜택:</b> {short_benefit}</p>
                <p style='margin: 5px 0 0 0; font-size: 11px; color: gray;'>클릭 후 패널에서 전체 정보 확인👇</p>
            </div>
            """
            
            folium.Marker(
                location=[row["위도"], row["경도"]],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{row['이름']} (클릭하여 정보 보기)",
                icon=folium.Icon(color=marker_color, icon="info-sign")
            ).add_to(m)

        map_data = st_folium(m, width=750, height=550, key="map")

    with col2:
        st.subheader("📋 가게 상세 정보 & 리뷰")
        
        clicked_store_name = None
        if map_data and map_data.get("last_object_clicked_tooltip"):
            raw_tooltip = map_data["last_object_clicked_tooltip"]
            clicked_store_name = raw_tooltip.split(" (")[0].strip()

        if clicked_store_name and clicked_store_name in df_filtered["이름"].values:
            store_info = df_filtered[df_filtered["이름"] == clicked_store_name].iloc[0]
            avg_rate = get_avg_rating(store_info['이름'])
            
            st.markdown(f"### 🏪 {store_info['이름']}")
            st.caption(f"📍 {store_info['학교']} {store_info['단과대']} | 🏷️ {store_info['카테고리']} | 🌟 평점: {avg_rate}")
            
            st.info(f"**🎁 특별 회원 전체 혜택**\n\n{store_info['혜택']}")
            st.markdown("---")
            
            st.write("✏️ **이 가게에 후기 남기기**")
            with st.form(key=f'review_form_{store_info["이름"]}'):
                rating = st.feedback("stars")
                review_text = st.text_input("후기 내용을 입력하세요 (최소 5글자 이상):", placeholder="예: 혜택 잘 받았습니다! 맛있어요.")
                
                st.write("🔒 **방문 인증 (필수)**")
                uploaded_file = st.file_uploader("리뷰 등록을 위해 해당 가게 방문을 인증할 수 있는 사진을 올려주세요.", type=["jpg", "jpeg", "png"])
                
                submit_button = st.form_submit_button(label="📝 후기 등록하기")
                
                if submit_button:
                    if rating is None:
                        st.error("⚠️ 별점을 선택해 주세요!")
                    elif len(review_text.strip()) < 5:
                        st.error("⚠️ 무의미한 후기 방지를 위해 최소 5글자 이상 작성해주세요.")
                    elif contains_bad_word(review_text):
                        st.error("🚨 비속어나 부적절한 단어가 포함된 후기는 등록할 수 없습니다.")
                    elif uploaded_file is None:
                        st.error("⚠️ 리뷰를 등록하려면 반드시 사진을 첨부해야 합니다.")
                    else:
                        if clicked_store_name not in st.session_state.reviews:
                            st.session_state.reviews[clicked_store_name] = []
                        
                        score = rating + 1 
                        stars = "⭐" * score
                        
                        st.session_state.reviews[clicked_store_name].append({
                            "별점": stars, 
                            "내용": review_text.strip(),
                            "점수": score
                        })
                        
                        save_json(REVIEWS_FILE, st.session_state.reviews)
                        st.success("✅ 사진이 정상 첨부되어 리뷰 등록이 완료되었습니다!")
                        st.rerun()
            
            st.write("💬 **등록된 후기 목록**")
            if clicked_store_name in st.session_state.reviews and st.session_state.reviews[clicked_store_name]:
                for r in reversed(st.session_state.reviews[clicked_store_name]):
                    st.markdown(f"- 📸 **[인증됨]** {r['별점']} | {r['내용']}")
            else:
                st.write("<small style='color:gray;'>아직 작성된 후기가 없습니다. 첫 후기를 남겨보세요!</small>", unsafe_allow_html=True)
                
        else:
            st.info("💡 지도 위에 있는 **마커**를 클릭하시면 해당 가게의 요약 혜택이 뜨고, 패널에 상세 정보가 나타납니다!")

    st.markdown(f"### 📋 {selected_school} {selected_dept} - {selected_category} 전체 목록")
    st.dataframe(df_filtered[["이름", "카테고리", "혜택"]], use_container_width=True)

except Exception as e:
    st.error(f"❌ 에러 발생 원인: {e}")
    st.write("📋 현재 불러온 데이터의 앞부분 모양새입니다. 위도/경도가 숫자가 맞는지 확인해 보세요:")
    st.dataframe(df.head(10))