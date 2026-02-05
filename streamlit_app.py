import streamlit as st
import os
import datetime
import google.generativeai as genai
from google.generativeai import caching
import glob

# 페이지 설정: 제목 및 아이콘
st.set_page_config(page_title="명리(命理) - AI 사주 풀이", page_icon="🔮", layout="centered")

# 프리미엄 스타일링 (Oriental Light Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&display=swap');
    
    .main {
        background-color: #ffffff;
        color: #333333;
    }
    .stApp {
        background-color: #ffffff;
    }
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
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #f9f9f9 !important;
        color: #333333 !important;
        border: 1px solid #ddd !important;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# --- 서비스 로직 ---

def load_api_key():
    """환경 변수 또는 .env 파일에서 API 키를 가져옵니다."""
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key and os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GOOGLE_API_KEY="):
                        key = line.split("=")[1].strip()
        except Exception: pass
    return key

def initialize_saju_engine(api_key):
    """지식 베이스를 초기화합니다. 캐싱이 지원되지 않으면 일반 모드로 작동합니다."""
    # 세션에 이미 엔진 설정이 있다면 재사용
    if 'saju_engine_ready' in st.session_state and st.session_state['saju_engine_ready']:
        return genai.GenerativeModel(st.session_state.get('saju_model_name', 'gemini-flash-latest'))

    genai.configure(api_key=api_key)
    data_dir = "data"
    
    with st.spinner("사주 명리학의 깊은 지식을 불러오는 중입니다..."):
        # 1. 파일 업로드 로직 (세션에 보관하여 반복 업로드 방지)
        if 'uploaded_file_objects' not in st.session_state:
            uploaded_files = []
            extensions = ['*.pdf', '*.txt', '*.md']
            for ext in extensions:
                for filepath in glob.glob(os.path.join(data_dir, ext)):
                    try:
                        file = genai.upload_file(path=filepath, display_name=os.path.basename(filepath))
                        uploaded_files.append(file)
                    except Exception: pass
            st.session_state['uploaded_file_objects'] = uploaded_files
        
        files = st.session_state['uploaded_file_objects']

        # 2. 모델 선택 및 설정 (품격 있는 한글 출력을 위한 시스템 명령)
        model_name = 'gemini-flash-latest'
        sys_instr = (
            "당신은 평생을 명리학 연구에 바친 대한민국 최고의 사주 대가입니다. "
            "사용자의 사주 자료를 분석할 때는 문학적이고 깊이 있는 표현을 사용하며, "
            "단순한 나열이 아닌 한 사람의 영혼과 운명을 어루만지는 품격 있는 한글로 답변해야 합니다. "
            "전문 용어를 정확히 사용하되, 대중이 이해하기 쉽게 그 의미를 유려하게 풀어서 설명하세요."
        )
        
        try:
            # 캐싱 시도
            cache = caching.CachedContent.create(
                model=f'models/{model_name}',
                display_name='saju_kb_cache_v3',
                system_instruction=sys_instr,
                contents=files,
                ttl=datetime.timedelta(minutes=30),
            )
            model = genai.GenerativeModel.from_cached_content(cached_content=cache)
            st.session_state['is_cached'] = True
        except Exception:
            # 캐싱 실패 시 일반 모델 사용
            model = genai.GenerativeModel(model_name, system_instruction=sys_instr)
            st.session_state['is_cached'] = False
            
        st.session_state['saju_model_name'] = model_name
        st.session_state['saju_engine_ready'] = True
        return model

# --- UI 레이아웃 ---

def main():
    # 데이터 디렉토리 강제 생성 (배포 환경 오류 방지)
    if not os.path.exists("data"):
        os.makedirs("data", exist_ok=True)
        
    st.title("命 理 (명 리)")
    st.markdown("<h3 style='text-align: center; opacity: 0.8;'>AI 정통 사주 심층 분석</h3>", unsafe_allow_html=True)
    st.divider()

    # 사이드바 (API 키 설정)
    with st.sidebar:
        st.header("설정")
        stored_key = load_api_key()
        # Streamlit Secrets 우선 순위 적용
        secrets_key = st.secrets.get("GOOGLE_API_KEY", "")
        default_key = secrets_key if secrets_key else stored_key
        
        api_key = st.text_input("Gemini API Key", type="password", value=default_key)
        if st.button("엔진 초기화 / 데이터 새로고침"):
            if 'saju_engine_ready' in st.session_state:
                del st.session_state['saju_engine_ready']
            if 'uploaded_file_objects' in st.session_state:
                del st.session_state['uploaded_file_objects']
            st.rerun()
        st.info("API 키 및 데이터를 관리합니다. 문제가 생기면 위 버튼을 눌러주세요.")

    # 상단 가이드 및 외부 주소 안내
    st.markdown("""
    <div style='background-color: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px solid #d4af37; margin-bottom: 25px;'>
        <p style='margin-bottom: 10px; color: #333;'><b>1단계.</b> 아래 전문 만세력 사이트에 접속하여 본인의 사주 정보를 확인하세요.</p>
        <a href='https://beta-ybz6.onrender.com/' target='_blank' style='display: inline-block; background-color: #d4af37; color: #ffffff; padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: bold;'>정통 만세력 확인하기 (클릭)</a>
        <p style='margin-top: 20px; color: #333;'><b>2단계.</b> 위 사이트의 결과 화면에 나오는 <b>분석 내용 전체</b>를 복사하여 아래창에 붙여넣어 주세요.</p>
    </div>
    """, unsafe_allow_html=True)

    # 사용자 입력 폼 (텍스트 영역)
    with st.container():
        user_saju_text = st.text_area(
            "복사한 사주 정보를 여기에 붙여넣으세요", 
            placeholder="전문 만세력 사이트의 결과 내용을 복사해서 넣어주세요.",
            height=200
        )
        col_n, col_q = st.columns([1, 2])
        with col_n:
            name = st.text_input("분석받을 분의 이름 (선택)", placeholder="홍길동")
        with col_q:
            add_query = st.text_input("추가로 궁금한 점 (선택)", placeholder="예: 올해 이직운이 있을까요? 연애운은 어떤가요?")

    if st.button("AI 대가에게 심층 풀이 받기"):
        if not api_key:
            st.error("API 키가 필요합니다. 설정창을 확인해 주세요.")
            return
        if not user_saju_text:
            st.warning("사주 정보를 붙여넣어 주세요.")
            return

        # 엔진 초기화 (최초 1회만 실행됨)
        model = initialize_saju_engine(api_key)

        with st.status("천기(天氣)를 정밀 분석하며 대가의 식견을 더하는 중...", expanded=True) as status:
            try:
                # 분석 요청 프롬프트 (한글 품질 및 추가 질문 반영)
                prompt_text = f"""
                [분석 대상자] 이름: {name if name else "사용자"}
                
                [사주 데이터]
                {user_saju_text}
                
                {f'[사용자 특별 문의] {add_query}' if add_query else ''}
                
                위의 외부 데이터를 바탕으로, 제공된 전문 사주 원전 데이터를 사용하여 
                다음 사항들에 대해 '심층 분석 보고서'를 작성해 주세요:

                1. 명식의 정수: 연주, 월주, 일주, 시주 및 지장간의 조화 재검토
                2. 오행의 세력: 타고난 기운의 강약과 그 속에 담긴 성정 풀이
                3. 격국과 용신: 삶의 큰 방향성과 운을 열어줄 열쇠(용신) 판정
                4. 주요 신살 및 12운성: 신살 및 12운성 데이터를 참조한 입체적 해석
                5. 특별한 상담: 사용자의 추가 문의 사항({add_query if add_query else '전반적 운세'})에 대한 대가로서의 명쾌한 조언

                *답변은 반드시 수필처럼 유려하고 품격 있는 한글 문체로 작성하세요. 번역투를 배제하고 한국 명리학의 깊이를 담아주세요.*
                """
                
                # 캐싱 여부에 따른 호출 방식 차이
                if st.session_state.get('is_cached', False):
                    response = model.generate_content(prompt_text)
                else:
                    content_payload = [prompt_text] + st.session_state.get('uploaded_file_objects', [])
                    response = model.generate_content(content_payload)
                
                if response and response.text:
                    st.balloons()
                    status.update(label="대가가 분석을 마쳤습니다.", state="complete", expanded=False)
                    
                    st.divider()
                    st.markdown(f"## {name if name else '사용자'}님을 위한 명리 분석 보고서")
                    st.markdown(f"<div class='result-container'>{response.text}</div>", unsafe_allow_html=True)
                    st.text_area("분석 결과 전문 복사하기", value=response.text, height=200)
                else:
                    st.error("분석 결과를 생성하지 못했습니다. 입력한 텍스트를 확인해 주세요.")
                
            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다: {str(e)}")

    st.markdown("<br><br><p style='text-align: center; opacity: 0.5;'>© 2026 AI 명리학 연구원. All rights reserved.</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
