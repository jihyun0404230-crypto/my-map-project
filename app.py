import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. 페이지 레이아웃 설정
st.set_page_config(page_title="대학별 학과 맛집 혜택 지도 🗺️", layout="wide")
st.title("🗺️ 우리 학교 & 학과 맞춤형 맛집 혜택 지도")
st.markdown("학교와 학과를 선택하면, 해당 학생들을 위한 **특별 제휴 혜택**과 맛집 지도가 나타납니다!")

# [메모리 데이터베이스] 사용자들이 남긴 별점과 후기를 임시 저장할 공간 생성
if "reviews" not in st.session_state:
    st.session_state.reviews = {}

# --- 🌟 추가된 함수: 평균 평점 계산 ---
def get_avg_rating(store_name):
    if store_name in st.session_state.reviews and st.session_state.reviews[store_name]:
        # '점수' 키가 있는 리뷰들만 모아서 평균 계산
        scores = [r["점수"] for r in st.session_state.reviews[store_name] if "점수" in r]
        if scores:
            return round(sum(scores) / len(scores), 1)
    return 0.0

try:
    # 2. 엑셀 파일(CSV) 읽어오기
    df = pd.read_csv("store_data.csv", header=None, encoding="utf-8")
    
    # 구조 매핑 (0:학교, 1:단과대/학과, 2:가게이름, 3:카테고리, 4:혜택내용, 5:위도, 6:경도)
    if df.shape[1] >= 7:
        df = df[[0, 1, 2, 3, 4, 5, 6]]
        df.columns = ["학교", "단과대", "이름", "카테고리", "혜택", "위도", "경도"]
    else:
        st.error("⚠️ 엑셀 파일의 데이터 칸(G열까지)이 부족합니다. 구조를 확인해 주세요!")
        st.stop()

    # 데이터 정리 및 공백 제거
    df["학교"] = df["학교"].astype(str).str.strip()
    df["단과대"] = df["단과대"].astype(str).str.strip()
    df["이름"] = df["이름"].astype(str).str.strip()
    df["카테고리"] = df["카테고리"].astype(str).str.strip()
    df["혜택"] = df["혜택"].fillna("지정된 혜택 정보가 없습니다.")
    df["위도"] = pd.to_numeric(df["위도"], errors='coerce')
    df["경도"] = pd.to_numeric(df["경도"], errors='coerce')
    df = df.dropna(subset=["위도", "경도"])

    # 3. 단계별 필터링 시스템 구축 (학교 -> 과 -> 카테고리)
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

    # 4. 화면 레이아웃 분할 (휴대폰에서는 col1이 위, col2가 아래로 자동 배치됨)
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
            
            # --- 🌟 수정된 부분: 지도 위 팝업에 평점과 요약 혜택 표시 ---
            avg_rate = get_avg_rating(row['이름'])
            # 혜택 내용이 길면 15글자까지만 자르고 '...' 붙이기
            short_benefit = str(row['혜택'])[:15] + "..." if len(str(row['혜택'])) > 15 else str(row['혜택'])
            
            popup_html = f"""
            <div style='font-family: sans-serif; min-width: 160px;'>
                <h4 style='margin:0;'>{row['이름']}</h4>
                <p style='margin: 3px 0; color: #f39c12; font-weight: bold;'>★ {avg_rate} / 5.0</p>
                <p style='margin:0; font-size: 13px; color: #2c3e50;'><b>핵심혜택:</b> {short_benefit}</p>
                <p style='margin: 5px 0 0 0; font-size: 11px; color: gray;'>클릭 후 패널에서 전체 혜택/후기 확인👇</p>
            </div>
            """
            
            folium.Marker(
                location=[row["위도"], row["경도"]],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{row['이름']} (클릭하여 정보 보기)",
                icon=folium.Icon(color=marker_color, icon="info-sign")
            ).add_to(m)

        map_data = st_folium(m, width=750, height=550, key="map")

    # 5. 우측(모바일은 하단) 패널: 가게 상세 정보 + 별점/후기 시스템
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
            
            # 🎁 1순위: 전체 혜택 출력
            st.info(f"**🎁 특별 회원 전체 혜택**\n\n{store_info['혜택']}")
            
            st.markdown("---")
            
            # 📝 2순위: 별점 및 후기 작성
            st.write("✏️ **이 가게에 후기 남기기**")
            rating = st.feedback("stars", key=f"star_{store_info['이름']}")
            review_text = st.text_input("후기 내용을 입력하세요 (최소 5글자 이상):", key=f"text_{store_info['이름']}", placeholder="예: 혜택 잘 받았습니다! 맛있어요.")
            
            if st.button("📝 후기 등록하기", key=f"btn_{store_info['이름']}"):
                # --- 🌟 수정된 부분: 별점 확인 및 5글자 제한 로직 ---
                if rating is None:
                    st.error("⚠️ 별점을 선택해 주세요!")
                elif len(review_text.strip()) < 5:
                    st.error("⚠️ 무의미한 후기 방지를 위해 최소 5글자 이상 작성해주세요.")
                else:
                    if clicked_store_name not in st.session_state.reviews:
                        st.session_state.reviews[clicked_store_name] = []
                    
                    # st.feedback은 0~4를 반환하므로 +1 처리
                    score = rating + 1 
                    stars = "⭐" * score
                    
                    st.session_state.reviews[clicked_store_name].append({
                        "별점": stars, 
                        "내용": review_text.strip(),
                        "점수": score  # 평균 계산을 위해 숫자 점수도 함께 저장
                    })
                    st.success("후기가 성공적으로 등록되었습니다!")
                    st.rerun() # 후기 등록 후 평점 갱신을 위해 화면 새로고침
            
            # 💬 3순위: 후기 목록 출력
            st.write("💬 **등록된 후기 목록**")
            if clicked_store_name in st.session_state.reviews and st.session_state.reviews[clicked_store_name]:
                for r in st.session_state.reviews[clicked_store_name]:
                    st.markdown(f"- {r['별점']} | {r['내용']}")
            else:
                st.write("<small style='color:gray;'>아직 작성된 후기가 없습니다. 첫 후기를 남겨보세요!</small>", unsafe_allow_html=True)
                
        else:
            st.info("💡 지도 위에 있는 **마커**를 클릭하시면 해당 가게의 요약 혜택이 뜨고, 패널에 상세 정보가 나타납니다!")

    # 6. 하단 목록 표 표시
    st.markdown(f"### 📋 {selected_school} {selected_dept} - {selected_category} 전체 목록")
    st.dataframe(df_filtered[["이름", "카테고리", "혜택"]], use_container_width=True)

except Exception as e:
    st.error(f"데이터를 불러오거나 지도를 구성하는 중 오류가 발생했습니다: {e}")