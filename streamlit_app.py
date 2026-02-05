import streamlit as st
import os
import datetime
import google.generativeai as genai
from google.generativeai import caching
import glob
from sajupy import calculate_saju, get_saju_details, lunar_to_solar
from saju_utils import get_extended_saju_data

# 페이지 설정: 제목 및 아이콘
st.set_page_config(page_title="명리(命理) - AI 사주 풀이", page_icon="🔮", layout="centered")

# 프리미엄 스타일링 (Oriental Light Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&display=swap');
    
    .main { background-color: #ffffff; color: #333333; }
    .stApp { background-color: #ffffff; }
    h1, h2, h3 {
        font-family: 'Noto Serif KR', serif !important;
        color: #2c3e50 !important;
        text-align: center;
        letter-spacing: 0.1em;
        margin-top: 20px;
    }
    .stButton>button {
        width: 100%;
        background-color: #d4af37;
        color: #ffffff;
        font-family: 'Noto Serif KR', serif;
        font-weight: 700;
        border: none;
        padding: 0.8rem;
        border-radius: 5px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #c49b32;
        transform: translateY(-2px);
    }
    .result-container {
        border: 2px solid #d4af37;
        padding: 25px;
        border-radius: 12px;
        background-color: #fdfdfd;
        color: #333333;
        line-height: 1.8;
        font-family: 'Noto Serif KR', serif;
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.1);
    }
    /* 테이블 스타일링 */
    .saju-table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        text-align: center;
        font-family: 'Noto Serif KR', serif;
    }
    .saju-table th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; color: #2c3e50; }
    .saju-table td { border: 1px solid #dee2e6; padding: 10px; color: #333; }
    .pillar-cell { font-size: 1.2rem; font-weight: bold; }
    .ten-god { color: #d4af37; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# --- 서비스 로직 ---

def initialize_saju_engine(api_key):
    """지식 베이스를 초기화합니다. 캐싱이 지원되지 않으면 일반 모드로 작동합니다."""
    if 'saju_engine_ready' in st.session_state and st.session_state['saju_engine_ready']:
        return genai.GenerativeModel(st.session_state.get('saju_model_name', 'gemini-flash-latest'))

    genai.configure(api_key=api_key)
    data_dir = "data"
    
    with st.spinner("사주 명리학의 깊은 지식을 불러오는 중입니다..."):
        if 'uploaded_file_objects' not in st.session_state:
            uploaded_files = []
            for ext in ['*.pdf', '*.txt', '*.md']:
                for filepath in glob.glob(os.path.join(data_dir, ext)):
                    try:
                        file = genai.upload_file(path=filepath, display_name=os.path.basename(filepath))
                        uploaded_files.append(file)
                    except Exception: pass
            st.session_state['uploaded_file_objects'] = uploaded_files
        
        files = st.session_state['uploaded_file_objects']
        model_name = 'gemini-flash-latest'
        sys_instr = (
            "당신은 평생을 명리학 연구에 바친 대한민국 최고의 사주 대가이자, 한 사람의 인생을 따스한 비유로 풀어내는 스토리텔러입니다. "
            "사용자의 사주 자료를 분석할 때는 어려운 한자어나 전문 용어보다는 일상적이고 문학적인 비유(날씨, 풍경, 계절 등)를 적극 사용하여 "
            "일반인도 자신의 운명을 그림 보듯 쉽게 이해할 수 있도록 풀이해야 합니다. "
            "단순한 결과 나열이 아닌, 영혼을 어루만지는 품격 있고 다정한 한글로 답변하세요."
        )
        
        try:
            cache = caching.CachedContent.create(
                model=f'models/{model_name}',
                display_name='saju_kb_cache_v8',
                system_instruction=sys_instr,
                contents=files,
                ttl=datetime.timedelta(minutes=30),
            )
            model = genai.GenerativeModel.from_cached_content(cached_content=cache)
            st.session_state['is_cached'] = True
        except Exception:
            model = genai.GenerativeModel(model_name, system_instruction=sys_instr)
            st.session_state['is_cached'] = False
            
        st.session_state['saju_model_name'] = model_name
        st.session_state['saju_engine_ready'] = True
        return model

# --- UI 레이아웃 ---

def main():
    if not os.path.exists("data"):
        os.makedirs("data", exist_ok=True)
        
    st.title("命 理 (명 리)")
    st.markdown("<h3 style='text-align: center; opacity: 0.8;'>AI 정통 사주 심층 분석 (일체형)</h3>", unsafe_allow_html=True)
    st.divider()

    with st.sidebar:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        st.markdown("### 📖 이용 안내")
        st.info("이제 외부 사이트 이동 없이 바로 정보를 입력하여 풀이를 받으실 수 있습니다.")
        st.caption("1. 이름과 생년월일시 입력")
        st.caption("2. [사주 명식 계산] 버튼 클릭")
        st.caption("3. 결과 확인 후 [심층 분석 보고서 생성] 클릭")
        if not api_key:
            st.error("⚠️ API Key 설정 필요 (Secrets)")

    # 입력 폼
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름 (선택)", placeholder="홍길동")
            birth_date = st.date_input(
                "생년월일", 
                value=datetime.date(1990, 1, 1),
                min_value=datetime.date(1900, 1, 1),
                max_value=datetime.date(2100, 12, 31)
            )
        with col2:
            gender = st.radio("성별", ["여", "남"], horizontal=True)
            birth_time = st.time_input("태어난 시각", value=datetime.time(0, 0))
            
        col3, col4 = st.columns(2)
        with col3:
            calendar_type = st.selectbox("달력 선택", ["양력", "음력"])
        with col4:
            is_leap = st.checkbox("음력 윤달 여부", value=False)

    if st.button("사주 명식 계산하기"):
        try:
            # 음력일 경우 양력으로 변환
            if calendar_type == "음력":
                solar_res = lunar_to_solar(birth_date.year, birth_date.month, birth_date.day, is_leap_month=is_leap)
                y, m, d = solar_res['solar_year'], solar_res['solar_month'], solar_res['solar_day']
            else:
                y, m, d = birth_date.year, birth_date.month, birth_date.day
            
            # 사주 계산
            saju_res = calculate_saju(y, m, d, birth_time.hour, birth_time.minute)
            details = get_saju_details(saju_res)
            
            # 확장 데이터 추가 (십성, 12운성, 오행 등)
            details = get_extended_saju_data(details)
            
            st.session_state['saju_data'] = details
            st.session_state['target_name'] = name
            st.session_state['target_gender'] = gender
            st.success("사주 명식이 정확하게 계산되었습니다.")
        except Exception as e:
            st.error(f"계산 중 오류 발생: {str(e)}")

    # 결과 표시 영역
    if 'saju_data' in st.session_state:
        data = st.session_state['saju_data']
        pillars = data['pillars']
        
        st.subheader("🔮 사주 4주 명식")
        # 테이블 시각화
        html_table = f"""
        <table class='saju-table'>
            <tr><th>구분</th><th>시주(時)</th><th>일주(日)</th><th>월주(月)</th><th>연주(年)</th></tr>
            <tr><td>천간</td><td class='pillar-cell'>{pillars['hour']['stem']}</td><td class='pillar-cell'>{pillars['day']['stem']}</td><td class='pillar-cell'>{pillars['month']['stem']}</td><td class='pillar-cell'>{pillars['year']['stem']}</td></tr>
            <tr><td>지지</td><td class='pillar-cell'>{pillars['hour']['branch']}</td><td class='pillar-cell'>{pillars['day']['branch']}</td><td class='pillar-cell'>{pillars['month']['branch']}</td><td class='pillar-cell'>{pillars['year']['branch']}</td></tr>
            <tr><td>십성</td><td class='ten-god'>{data['ten_gods']['hour']}</td><td class='ten-god'>{data['ten_gods']['day']}</td><td class='ten-god'>{data['ten_gods']['month']}</td><td class='ten-god'>{data['ten_gods']['year']}</td></tr>
            <tr><td>12운성</td><td>{data['twelve_growth']['hour']}</td><td>{data['twelve_growth']['day']}</td><td>{data['twelve_growth']['month']}</td><td>{data['twelve_growth']['year']}</td></tr>
        </table>
        """
        st.markdown(html_table, unsafe_allow_html=True)
        
        # 오행 분포 시각화 고도화
        elems = data['five_elements']
        st.subheader("☯️ 오행의 기운 분포")
        
        cols = st.columns(5)
        for idx, (el, val) in enumerate(elems.items()):
            cols[idx].metric(el, f"{val}개")
            # 시각적 강도 표시 (8개를 만점으로 가정)
            progress_val = min(val / 8, 1.0)
            cols[idx].progress(progress_val)

        st.divider()
        
        # 추가 질문 및 심층 분석 버튼
        add_query = st.text_input("AI 명리 대가에게 특별히 궁금한 점", placeholder="예: 구체적인 올해 건강운이나 이사운이 궁금합니다.")
        
        if st.button("심층 분석 보고서 생성 시작"):
            if not api_key:
                st.error("API 키가 설정되지 않았습니다. 개발자에게 문의하세요.")
                return
                
            model = initialize_saju_engine(api_key)
            with st.status("대가의 식견으로 당신의 운명을 통찰하는 중...", expanded=True) as status:
                try:
                    name_str = st.session_state.get('target_name', '사용자')
                    gender_str = st.session_state.get('target_gender', '여')
                    saju_summary = f"""
                    [대상자] {name_str} ({gender_str})
                    [양력 생일] {data['birth_date']} {data['birth_time']}
                    [사주] 연:{pillars['year']}, 월:{pillars['month']}, 일:{pillars['day']}, 시:{pillars['hour']}
                    [오행분포] {elems}
                    [환경] {data['zi_time_type']}
                    """
                    
                    prompt = f"""
                    {saju_summary}
                    [사용자 추가 질문] {add_query if add_query else '전체적인 인생의 흐름과 운세 분석 부탁드립니다.'}
                    
                    위 사주 명식을 바탕으로 당신이 가진 전문 명리 지식(PDF)을 활용하여 분석하되, 
                    **일반인도 한눈에 이해할 수 있도록 친절하고 쉬운 비유**를 사용하여 보고서를 작성해 주세요.
                    
                    보고서 구성 필수 항목:
                    1. 🖼️ **운명의 풍경**: 이 사주의 구성을 한 폭의 그림이나 풍경으로 묘사해 주세요. (예: "끝없는 평야에 홀로 서 있는 소나무의 형상입니다")
                    2. 🌱 **나의 본 모습**: 어려운 용어 대신 비유(자연물, 도구 등)를 통해 타고난 성정과 기질을 쉽게 설명해 주세요.
                    3. 🎢 **운의 흐름**: 현재와 미래의 운의 흐름을 날씨나 계절의 변화에 비유하여 알려주세요.
                    4. 💡 **대가의 조언**: 일상에서 실천할 수 있는 구체적이고 따뜻한 조언을 담아주세요.
                    
                    *반드시 수필처럼 유려한 한글 문체로 작성하며, 전문 용어가 나올 경우 반드시 쉬운 풀이를 덧붙여 주십시오.*
                    """
                    
                    if st.session_state.get('is_cached', False):
                        response = model.generate_content(prompt)
                    else:
                        response = model.generate_content([prompt] + st.session_state.get('uploaded_file_objects', []))
                    
                    if response and response.text:
                        st.balloons()
                        status.update(label="분석이 모두 완료되었습니다.", state="complete", expanded=False)
                        st.divider()
                        st.markdown(f"## {name_str}님을 위한 심층 운명 보고서")
                        st.markdown(f"<div class='result-container'>{response.text}</div>", unsafe_allow_html=True)
                    else:
                        st.error("분석 결과를 도출하지 못했습니다.")
                except Exception as e:
                    st.error(f"분석 중 오류 발생: {str(e)}")

    st.markdown("<br><br><p style='text-align: center; opacity: 0.5;'>© 2026 AI 명리학 연구원. All rights reserved.</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
