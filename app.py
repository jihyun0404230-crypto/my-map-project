import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math

# --- 1. 페이지 설정 및 초기화 ---
st.set_page_config(page_title="학과 제휴 혜택 지도", layout="wide")

# 세션 상태 초기화 (후기 데이터 저장용)
if 'reviews' not in st.session_state:
    st.session_state.reviews = pd.DataFrame(columns=['place_name', 'rating', 'review_text'])

# --- 2. 샘플 데이터 로드 (실제 엑셀 파일 경로로 변경 필요) ---
# 실제 환경에서는 pd.read_excel('data.xlsx') 등으로 불러옵니다.
@st.cache_data
def load_data():
    data = {
        '이름': ['전북대 밥집', '전북대 술집', '전북대 카페'],
        '위도': [35.8468, 35.8450, 35.8475],
        '경도': [127.1290, 127.1300, 127.1310],
        '카테고리': ['밥집', '술집', '카페'],
        '혜택': ['테이블당 음료 1병 무료', '메인 안주 10% 할인', '아메리카노 사이즈업'],
        '상세설명': ['전북대 구정문 앞 맛있는 밥집입니다.', '분위기 좋은 술집입니다.', '카공하기 좋은 카페입니다.']
    }
    return pd.DataFrame(data)

df = load_data()

# --- 3. 평점 계산 함수 ---
def get_average_rating(place_name):
    place_reviews = st.session_state.reviews[st.session_state.reviews['place_name'] == place_name]
    if not place_reviews.empty:
        # 소수점 첫째 자리까지 표시
        return round(place_reviews['rating'].mean(), 1)
    return 0.0

# --- 4. 메인 화면 UI ---
st.title("🗺️ 학과 제휴 혜택 지도")

# 카테고리 필터
categories = ['전체'] + df['카테고리'].unique().tolist()
selected_category = st.selectbox("카테고리 선택", categories)

if selected_category != '전체':
    filtered_df = df[df['카테고리'] == selected_category]
else:
    filtered_df = df

# --- 5. 지도 생성 및 마커 추가 ---
# 기본 중심 좌표 (전북대 부근)
map_center = [35.8468, 127.1290]
m = folium.Map(location=map_center, zoom_start=15)

# 마커 추가
for idx, row in filtered_df.iterrows():
    place_name = row['이름']
    benefit = row['혜택']
    avg_rating = get_average_rating(place_name)
    
    # 🌟 개선포인트 1: 마커 클릭 시 나타나는 Popup (간단한 요약 혜택 + 평점 표시)
    # Popup 내부에 버튼이나 링크를 넣어 상세 혜택을 볼 수 있도록 유도합니다.
    popup_html = f"""
    <div style="width: 200px; font-family: sans-serif;">
        <h4 style="margin-top:0; margin-bottom:5px;">{place_name}</h4>
        <p style="margin:0; color: #f39c12; font-weight: bold;">★ {avg_rating} / 5.0</p>
        <hr style="margin: 5px 0;">
        <p style="margin:0; font-size: 14px;"><b>간단 혜택:</b> {benefit}</p>
        <p style="margin-top:5px; font-size: 12px; color: gray;">지도 아래에서 상세 정보와 후기를 확인하세요.</p>
    </div>
    """
    
    folium.Marker(
        [row['위도'], row['경도']],
        popup=folium.Popup(popup_html, max_width=250),
        tooltip=place_name,
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(m)

# 지도 출력 (width 100%로 설정하여 모바일 화면에 맞춤)
st_data = st_folium(m, width="100%", height=400)


# --- 6. 상세 정보 및 후기 영역 (지도 하단) ---
st.divider()
st.subheader("📋 장소 상세 및 후기")

# 사용자가 지도에서 마커(Popup)를 클릭했는지 확인
if st_data['last_object_clicked_popup'] is not None:
    # 팝업 HTML에서 장소 이름 추출 (조금 투박하지만 Streamlit-folium 연동에서 자주 쓰는 방식)
    clicked_html = st_data['last_object_clicked_popup']
    
    # HTML 문자열에서 <h4> 태그 안의 텍스트(장소 이름)를 찾아냄
    import re
    match = re.search(r'<h4>(.*?)<\/h4>', clicked_html)
    
    if match:
        selected_place = match.group(1)
        place_data = df[df['이름'] == selected_place].iloc[0]
        
        avg_rating = get_average_rating(selected_place)
        
        st.markdown(f"### {selected_place}")
        st.markdown(f"**🌟 평균 평점:** {avg_rating} / 5.0")
        st.markdown(f"**🎁 전체 혜택:** {place_data['혜택']}")
        st.markdown(f"**설명:** {place_data['상세설명']}")
        
        # 길찾기 링크 (카카오맵 등)
        kakao_map_url = f"https://map.kakao.com/link/to/{selected_place},{place_data['위도']},{place_data['경도']}"
        st.markdown(f"[📍 길찾기 (카카오맵)]({kakao_map_url})")
        
        st.divider()
        
        # --- 7. 후기 작성 및 🌟 개선포인트 2: 글자 수 제한 ---
        st.markdown("#### ✏️ 후기 작성")
        with st.form(key=f'review_form_{selected_place}'):
            rating = st.slider("별점", 1, 5, 5)
            review_text = st.text_area("후기를 남겨주세요 (최소 5자 이상)")
            submit_button = st.form_submit_button(label="후기 등록")
            
            if submit_button:
                # 글자 수 검증
                if len(review_text.strip()) < 5:
                    st.error("⚠️ 후기는 최소 5글자 이상 작성해주세요.")
                else:
                    # 후기 저장
                    new_review = pd.DataFrame([{
                        'place_name': selected_place, 
                        'rating': rating, 
                        'review_text': review_text
                    }])
                    st.session_state.reviews = pd.concat([st.session_state.reviews, new_review], ignore_index=True)
                    st.success("후기가 등록되었습니다!")
                    st.rerun() # 화면 새로고침하여 평점 및 리뷰 반영
        
        # --- 8. 후기 목록 표시 ---
        st.markdown("#### 💬 후기 목록")
        place_reviews = st.session_state.reviews[st.session_state.reviews['place_name'] == selected_place]
        
        if place_reviews.empty:
            st.info("아직 등록된 후기가 없습니다.")
        else:
            for idx, review in place_reviews.iterrows():
                st.markdown(f"⭐ {review['rating']}점 | {review['review_text']}")
                
else:
    st.info("👆 지도에서 장소를 클릭(터치)하면 상세 정보와 전체 혜택이 여기에 표시됩니다.")