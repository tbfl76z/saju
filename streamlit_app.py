import streamlit as st
import os
import datetime
import google.generativeai as genai
from google.generativeai import caching
import glob
from sajupy import calculate_saju, get_saju_details, lunar_to_solar
from saju_utils import get_extended_saju_data

# 페이지 설정: 제목 및 아이콘 (최상단 배치 필수)
st.set_page_config(page_title="Destiny Code - AI 사주 풀이", page_icon="🔮", layout="wide")

# --- 전역 스타일 주입 (모든 버튼 및 카드 스타일 통일) ---
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
    
    /* 버튼 스타일 통일 (이미지의 노란색 버튼) */
    div.stButton > button {
        background-color: #d4af37 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
        height: 3rem !important;
        width: 100% !important;
        margin: 5px 0 !important;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        font-family: 'Noto Serif KR', serif;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        font-size: 0.9rem !important;
    }
    div.stButton > button:hover {
        background-color: #bfa02d !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
        transform: translateY(-2px);
    }
    
    /* 모바일 그리드 강제 */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: wrap !important;
            gap: 5px !important;
        }
    }
    
    /* 카드 공통 스타일 (이미지 1 참조) */
    .saju-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px 10px;
        text-align: center;
        background-color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 5px;
        transition: all 0.2s ease;
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .saju-card.selected {
        border: 2px solid #d4af37 !important;
        background-color: #fffcf0 !important;
        box-shadow: 0 6px 15px rgba(212, 175, 55, 0.15) !important;
    }
    
    /* 상세 분석 요약 박스 (이미지 2 참조) */
    .analysis-summary-box {
        background-color: #e7f3ff;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        color: #2c3e50;
        font-size: 0.95rem;
        border-left: 5px solid #3498db;
    }

    /* 팝업 스타일 커스텀 */
    div[data-testid="stPopover"] > button {
        background-color: #ffffff !important;
        border: 1px solid #eee !important;
        border-radius: 8px !important;
        padding: 8px !important;
        width: 100% !important;
        height: auto !important;
        color: #333 !important;
        font-size: 0.75rem !important;
        box-shadow: none !important;
        margin: 0 !important;
    }
    div[data-testid="stPopover"] > button:hover {
        border-color: #d4af37 !important;
        background-color: #fffcf0 !important;
    }
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
    now_year = datetime.datetime.now().year
    if not os.path.exists("data"):
        os.makedirs("data", exist_ok=True)
        
    # 제목 및 로고 배치
    t_col1, t_col2 = st.columns([1, 4])
    with t_col1:
        st.write("") # 간격 조절용
        # 로고 경로를 스크립트 상대 경로로 설정하여 배포 환경 호환성 확보
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=80)
        else:
            st.write("🔮") # 로고 파일이 없을 경우의 예비 아이콘
    with t_col2:
        st.title("Destiny Code")
    st.markdown("<h3 style='text-align: center; opacity: 0.8;'>Your Life, Written in Code.</h3>", unsafe_allow_html=True)
    st.divider()

    with st.sidebar:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            st.error("⚠️ API Key 설정 필요 (Secrets)")

    # 입력 폼
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름 (선택)", placeholder="홍길동")
            st.write("🗓️ 생년월일")
            b_cols = st.columns([2, 1, 1])
            with b_cols[0]:
                b_year = st.number_input("년", min_value=1900, max_value=2100, value=1990)
            with b_cols[1]:
                b_month = st.number_input("월", min_value=1, max_value=12, value=1)
            with b_cols[2]:
                b_day = st.number_input("일", min_value=1, max_value=31, value=1)
        with col2:
            gender = st.radio("성별", ["여", "남"], horizontal=True)
            st.write("⏰ 태어난 시간")
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                b_hour = st.number_input("시", min_value=0, max_value=23, value=0)
            with t_col2:
                b_minute = st.number_input("분", min_value=0, max_value=59, value=0)
            
        col3, col4 = st.columns(2)
        with col3:
            calendar_type = st.selectbox("달력 선택", ["양력", "음력"])
        with col4:
            is_leap = st.checkbox("음력 윤달 여부", value=False)

    if st.button("사주 명식 계산하기"):
        try:
            # 날짜 유효성 체크 및 객체 생성
            birth_date = datetime.date(b_year, b_month, b_day)
            
            # 사주 계산 (라이브러리 내 태양시 보정 및 23:30 경계 설정 사용)
            saju_res = calculate_saju(
                b_year, b_month, b_day, 
                b_hour, b_minute,
                use_solar_time=True, 
                longitude=127.5,
                early_zi_time=False
            )
            details = get_saju_details(saju_res)
            
            # 음력일 경우 보정된 양력으로 재계산
            if calendar_type == "음력":
                solar_res = lunar_to_solar(b_year, b_month, b_day, is_leap_month=is_leap)
                y, m, d = solar_res['solar_year'], solar_res['solar_month'], solar_res['solar_day']
                saju_res = calculate_saju(y, m, d, b_hour, b_minute, 
                                        use_solar_time=True, longitude=127.5, early_zi_time=False)
                details = get_saju_details(saju_res)
            
            # 확장 데이터 추가 (십성, 12운성, 오행, 대운, 신살 등)
            details = get_extended_saju_data(details, gender=gender)
            
            st.session_state['saju_data'] = details
            st.session_state['target_name'] = name
            st.session_state['target_gender'] = gender
            # 초기 선택 상태 설정 (현재 대운 및 현재 연도)
            birth_year = int(details.get('birth_date', '1990-01-01').split('-')[0])
            now_year = datetime.datetime.now().year
            korean_age = now_year - birth_year + 1
            
            # 현재 나이에 해당하는 대운 찾기
            cur_daeun_age = details['fortune']['num']
            for d in details['fortune']['list']:
                if d['age'] <= korean_age < d['age'] + 10:
                    cur_daeun_age = d['age']
                    break
            
            st.session_state['selected_daeun_age'] = cur_daeun_age
            st.session_state['selected_seyun_year'] = now_year
            
            # 데이터 버전 관리용 플래그
            st.session_state['data_version'] = "v3"
            st.success("사주 명식이 정확하게 계산되었습니다.")
        except Exception as e:
            st.error(f"계산 중 오류 발생: {str(e)}")

    # 결과 표시 영역
    if 'saju_data' in st.session_state:
        data = st.session_state['saju_data']
        pillars = data['pillars']
        
        st.subheader("🔮 사주 4주 명식")
        from saju_data import SAJU_TERMS

        def term_popover(label, value, key_suffix):
            # 신살이나 관계의 경우 ','로 구분된 여러 개일 수 있음
            if not value or value == '-':
                st.write("-")
                return
                
            items = [v.strip() for v in value.split(',')]
            
            with st.popover(value, use_container_width=True):
                for item in items:
                    lookup_key = item
                    if item == '인': lookup_key = '본인'
                    
                    # '천간합', '지지충' 등 접두어가 붙은 경우 원본 단어 추출
                    clean_item = item.replace("천간", "").replace("지지", "")
                    lookup_key = clean_item if clean_item in SAJU_TERMS else lookup_key
                    if clean_item == '인': lookup_key = '본인'
                    
                    # 1. 먼저 단어로 검색
                    desc = SAJU_TERMS.get(lookup_key)
                    
                    if desc:
                        st.markdown(f"**{item}**")
                        st.caption(desc)
                    elif len(item) == 2:
                        # 2. 2글자 간지(예: '갑자')인 경우 각각 분리해서 검색
                        stem, branch = item[0], item[1]
                        stem_desc = SAJU_TERMS.get(stem)
                        branch_desc = SAJU_TERMS.get(branch)
                        
                        if stem_desc or branch_desc:
                            st.markdown(f"**{item} ({stem}+{branch})**")
                            if stem_desc: st.caption(f"**{stem}**: {stem_desc}")
                            if branch_desc: st.caption(f"**{branch}**: {branch_desc}")
                        else:
                            st.markdown(f"**{item}**")
                            st.caption("상세 정보가 구축 중입니다.")
                    else:
                        st.markdown(f"**{item}**")
                        st.caption("상세 정보가 구축 중입니다.")
                        
                    if len(items) > 1:
                        st.divider()

        # --- UI 컴포넌트 유틸리티 ---
        
        def render_saju_card(header, ganzhi, stem_tg, branch_tg, growth, sinsal, relations, is_selected=False):
            """이미지 1 스타일의 사주 카드 렌더링"""
            card_class = "saju-card selected" if is_selected else "saju-card"
            st.markdown(f"""
                <div class='{card_class}'>
                    <div style='font-size:0.85rem; font-weight:bold; color:#666; margin-bottom:5px;'>{header}</div>
                    <div style='font-size:2.2rem; font-weight:bold; color:#2c3e50; margin:10px 0;'>{ganzhi}</div>
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; border-top: 1px solid #eee; padding-top: 10px;'>
                        <div><div style='font-size:0.7rem; color:#999;'>십성</div><div style='font-size:0.95rem; color:#d32f2f; font-weight:500;'>{stem_tg} | {branch_tg}</div></div>
                        <div><div style='font-size:0.7rem; color:#999;'>운성</div><div style='font-size:0.9rem; color:#1976d2; font-weight:500;'>{growth}</div></div>
                    </div>
                    <div style='font-size:0.8rem; color:#e67e22; margin-top:10px;'>✨ {sinsal}</div>
                    <div style='font-size:0.75rem; color:#9b59b6;'>🔗 {relations}</div>
                </div>
            """, unsafe_allow_html=True)

        def render_analysis_table(title, instruction, row_labels, column_headers, data_grid):
            """이미지 2 스타일의 상세 분석 테이블 (팝업 연동)"""
            st.markdown(f"### 🔍 {title}")
            st.markdown(f"<div class='analysis-summary-box'>{instruction}</div>", unsafe_allow_html=True)
            
            # 테이블 헤더
            cols = st.columns([1.5] + [1] * len(column_headers))
            cols[0].markdown(f"<div style='background:#f1f3f5; border-radius:8px; padding:8px; text-align:center; font-weight:bold; font-size:0.8rem;'>분석 항목</div>", unsafe_allow_html=True)
            for i, header in enumerate(column_headers):
                cols[i+1].markdown(f"<div style='background:#f1f3f5; border-radius:8px; padding:8px; text-align:center; font-weight:bold; font-size:0.8rem;'>{header}</div>", unsafe_allow_html=True)
            
            # 데이터 행
            for row_idx, label in enumerate(row_labels):
                cols = st.columns([1.5] + [1] * len(column_headers))
                cols[0].markdown(f"<div style='background:#f8f9fa; border-radius:8px; padding:10px; font-weight:bold; font-size:0.8rem; height:100%; display:flex; align-items:center;'>{label}</div>", unsafe_allow_html=True)
                for col_idx, value in enumerate(data_grid[row_idx]):
                    with cols[col_idx+1]:
                        # 팝업 내부에 상세 설명 표시 (SAJU_TERMS 연동)
                        clean_val = value.replace(" ˅", "").strip()
                        with st.popover(value if value != "-" else " - ", use_container_width=True):
                            desc = SAJU_TERMS.get(clean_val, "상세 정보가 준비 중입니다.")
                            st.markdown(f"**{clean_val}**")
                            st.caption(desc)

        # --- 사주 4주 명식 (이미지 2 스타일로 구현) ---
        st.subheader("🔮 사주 4주 명식")
        
        # 안내 문구 박스
        st.markdown("<div class='analysis-summary-box'>당신의 타고난 기운인 사주(4주 8자) 명식입니다. 각 항목을 클릭하여 상세한 풀이를 확인해보세요.</div>", unsafe_allow_html=True)
        
        headers = ["시주(時)", "일주(日)", "월주(月)", "연주(년)"]
        rows = [
            ("천간", [
                (data['ten_gods']['hour'], pillars['hour']['stem']),
                (data['ten_gods']['day'], pillars['day']['stem']),
                (data['ten_gods']['month'], pillars['month']['stem']),
                (data['ten_gods']['year'], pillars['year']['stem'])
            ]),
            ("지지", [
                ("시지", pillars['hour']['branch'], data['jiji_ten_gods']['hour']),
                ("일지", pillars['day']['branch'], data['jiji_ten_gods']['day']),
                ("월지", pillars['month']['branch'], data['jiji_ten_gods']['month']),
                ("연지", pillars['year']['branch'], data['jiji_ten_gods']['year'])
            ]),
            ("12운성", [
                ("시주", data['twelve_growth']['hour']),
                ("일주", data['twelve_growth']['day']),
                ("월주", data['twelve_growth']['month']),
                ("연주", data['twelve_growth']['year'])
            ])
        ]
        
        # 헤더 출력
        h_cols = st.columns([1.2] + [1] * 4)
        h_cols[0].markdown("<div style='background:#f1f3f5; border-radius:8px; padding:8px; text-align:center; font-weight:bold; font-size:0.8rem;'>구분</div>", unsafe_allow_html=True)
        for i, h in enumerate(headers):
            h_cols[i+1].markdown(f"<div style='background:#f1f3f5; border-radius:8px; padding:8px; text-align:center; font-weight:bold; font-size:0.8rem;'>{h}</div>", unsafe_allow_html=True)
            
        # 데이터 행 출력
        for r_idx, (r_label, r_data) in enumerate(rows):
            r_cols = st.columns([1.2] + [1] * 4)
            r_cols[0].markdown(f"<div style='background:#f8f9fa; border-radius:8px; padding:10px; font-weight:bold; font-size:0.8rem; height:100%; display:flex; align-items:center;'>{r_label}</div>", unsafe_allow_html=True)
            for c_idx, cell_data in enumerate(r_data):
                with r_cols[c_idx+1]:
                    if r_label == "천간":
                        tg, stem = cell_data
                        label_val = f"{tg}\n{stem}"
                        lookup_key = stem
                    elif r_label == "지지":
                        label, branch, jtg = cell_data
                        label_val = f"{branch}\n{jtg}"
                        lookup_key = branch
                    else: # 12운성
                        unit, growth = cell_data
                        label_val = growth
                        lookup_key = growth
                        
                    with st.popover(label_val, use_container_width=True):
                        st.markdown(f"**{lookup_key}**")
                        st.caption(SAJU_TERMS.get(lookup_key, "상세 정보가 준비 중입니다."))
        
        # 공망 및 지지 관계 표시
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.warning(f"🕳️ **공망 (Void):** [년]{data['gongmang']['year']} [일]{data['gongmang']['day']}")
        with col_g2:
            if data.get('relations'):
                st.info(f"💡 **지지 관계:** {', '.join(data['relations'])}")
        
        # 오행 분포 시각화 고도화
        elems = data['five_elements']
        st.subheader("☯️ 오행의 기운 분포")
        
        cols = st.columns(5)
        for idx, (el, val) in enumerate(elems.items()):
            cols[idx].metric(el, f"{val}개")
            # 시각적 강도 표시 (8개를 만점으로 가정)
            progress_val = min(val / 8, 1.0)
            cols[idx].progress(progress_val)

        # 대운 리스트 - 이미지 4 스타일 (버튼 상단 배치, 고밀도 카드)
        daeun_info = data['fortune']
        st.subheader("📅 대운(大運)의 흐름")
        st.write(f"현재 대운수: **{daeun_info['num']}** ({daeun_info['direction']})")
        
        for item in data['fortune']['list']:
            age_val = item.get('age', 0)
            is_sel_daeun = st.session_state.get('selected_daeun_age') == age_val
            
            # 카드 렌더링 (이미지 1 스타일)
            render_saju_card(
                f"{age_val}세 대운",
                item.get('ganzhi', '-'),
                item.get('stem_ten_god', '-'),
                item.get('branch_ten_god', '-'),
                item.get('twelve_growth', '-'),
                f"신살: {item.get('sinsal', '-')}",
                f"관계: {item.get('relations', '-')}",
                is_sel_daeun
            )
            
            if st.button(f"{age_val}세 대운 선택", key=f"btn_daeun_{age_val}", use_container_width=True):
                st.session_state['selected_daeun_age'] = age_val
                birth_year = int(data.get('birth_date', '1990-01-01').split('-')[0])
                st.session_state['selected_seyun_year'] = birth_year + age_val - 1
                st.rerun()

        # --- 대운 상세 상호작용 분석 섹션 (NEW) ---
        if 'selected_daeun_age' in st.session_state:
            sel_age = st.session_state['selected_daeun_age']
            sel_daeun = next((d for d in data['fortune']['list'] if d['age'] == sel_age), None)
            
            if sel_daeun:
                # 상세 관계 데이터 재산출 (각 기둥별로 개별 관계 추출)
                def get_pillar_relation(pillar_key):
                    p = pillars[pillar_key]
                    d_ganzhi = sel_daeun['ganzhi']
                    if not d_ganzhi or len(d_ganzhi) < 2: return {}
                    d_stem, d_branch = d_ganzhi[0], d_ganzhi[1]
                    p_stem, p_branch = p['stem'], p['branch']
                    
                    from saju_utils import GAN_TEN_GODS, TWELVE_GROWTH, STEM_RELATIONS, BRANCH_RELATIONS
                    day_gan = pillars['day']['stem']
                    
                    inter_rels = []
                    sinsal_rels = []
                    if STEM_RELATIONS['충'].get(d_stem) == p_stem: inter_rels.append("천간충(沖)")
                    if STEM_RELATIONS['합'].get(d_stem) == p_stem: inter_rels.append("천간합(合)")
                    if BRANCH_RELATIONS['충'].get(d_branch) == p_branch: inter_rels.append("충(沖)")
                    if BRANCH_RELATIONS['합'].get(d_branch) == p_branch: inter_rels.append("합(合)")
                    
                    h_val = BRANCH_RELATIONS['형'].get(d_branch)
                    if h_val:
                        if isinstance(h_val, list):
                            if p_branch in h_val: inter_rels.append("형(刑)")
                        elif h_val == p_branch: inter_rels.append("형(刑)")
                    
                    if BRANCH_RELATIONS['파'].get(d_branch) == p_branch: inter_rels.append("파(破)")
                    if BRANCH_RELATIONS['해'].get(d_branch) == p_branch: inter_rels.append("해(害)")
                    if BRANCH_RELATIONS['원진'].get(d_branch) == p_branch: sinsal_rels.append("원진(元嗔)")
                    if BRANCH_RELATIONS['귀문'].get(d_branch) == p_branch: sinsal_rels.append("귀문(鬼門)")
                    
                    year_branch = pillars['year']['branch']
                    from saju_utils import get_sinsal_list
                    twelve_sinsal = get_sinsal_list(year_branch, d_branch)
                    if twelve_sinsal and twelve_sinsal not in sinsal_rels: sinsal_rels.append(twelve_sinsal)
                    
                    return {
                        "ganzhi": p['pillar'],
                        "ten_god": GAN_TEN_GODS.get(day_gan, {}).get(p_stem, '-'),
                        "growth": TWELVE_GROWTH.get(d_stem, {}).get(p_branch, '-'),
                        "sinsal": ", ".join(sinsal_rels) if sinsal_rels else "-",
                        "interaction": ", ".join(inter_rels) if inter_rels else "평온"
                    }

                p_keys = ['hour', 'day', 'month', 'year']
                p_data = {k: get_pillar_relation(k) for k in p_keys}
                
                row_labels = ["사주원국 간지", "원국 해당 십성", "대운 적용 운성", "적용 신살·귀인", "상호 관계 분석"]
                column_headers = ["시주(時)", "일주(日)", "월주(月)", "연주(년)"]
                data_grid = [
                    [p_data[k]['ganzhi'] for k in p_keys],
                    [p_data[k]['ten_god'] for k in p_keys],
                    [p_data[k]['growth'] for k in p_keys],
                    [p_data[k]['sinsal'] for k in p_keys],
                    [p_data[k]['interaction'] for k in p_keys]
                ]
                
                render_analysis_table(
                    f"{sel_age}세 대운({sel_daeun['ganzhi']}) 상세 분석",
                    "선택하신 대운이 원국의 각 기둥(연,월,일,시)과 맺는 명리적 상호작용을 항목별로 풀이합니다.",
                    row_labels, column_headers, data_grid
                )
                
                st.markdown("---")

        # 세운(Seyun) 시각화 - 10년치 전체 그리드
        from saju_utils import get_seyun_list
        try:
            birth_year = int(data.get('birth_date', '1990-01-01').split('-')[0])
            # 선택된 대운 연령 기준 또는 현재 대운 기준
            selected_daeun_age = st.session_state.get('selected_daeun_age')
            if selected_daeun_age is None:
                # 현재 나이에 해당하는 대운 찾기
                korean_age = now_year - birth_year + 1
                selected_daeun_age = data['fortune']['num']
                for d in data['fortune']['list']:
                    if d['age'] <= korean_age < d['age'] + 10:
                        selected_daeun_age = d['age']
                        break
                st.session_state['selected_daeun_age'] = selected_daeun_age

            seyun_start_year = birth_year + selected_daeun_age - 1
            seyun_list = get_seyun_list(pillars.get('day', {}).get('stem', '甲'), 
                                      pillars.get('year', {}).get('branch', '子'), 
                                      seyun_start_year, count=10, pillars=pillars,
                                      day_branch=pillars.get('day', {}).get('branch', '丑'))
        except:
            seyun_list = []

        if seyun_list:
            st.subheader(f"📅 세운(年運): {seyun_start_year}년 ~ {seyun_start_year+9}년")
            for i in range(0, len(seyun_list), 5):
                s_cols = st.columns(5)
                chunk = seyun_list[i:i+5]
                for idx, s_item in enumerate(chunk):
                    s_year = s_item['year']
                    is_sel_year = st.session_state.get('selected_seyun_year') == s_year
                    is_now = s_year == now_year
                    
                    card_class = "saju-card selected" if is_sel_year else "saju-card"
                    border_color = "#d63384" if is_sel_year else ("#ffc107" if is_now else "#e0e0e0")
                    bg_color = "#fff0f6" if is_sel_year else ("#fffdf0" if is_now else "#ffffff")
                    
                    with s_cols[idx]:
                        render_saju_card(
                            f"{s_year}년 {'(현재)' if is_now else ''}",
                            s_item['ganzhi'],
                            s_item['stem_ten_god'],
                            s_item['branch_ten_god'],
                            s_item['twelve_growth'],
                            f"✨ {s_item['sinsal']}",
                            f"🔗 {s_item['relations']}",
                            is_sel_year
                        )
                        if st.button(f"{s_year}년 선택", key=f"btn_year_{s_year}", use_container_width=True):
                            st.session_state['selected_seyun_year'] = s_year
                            st.rerun()

            # --- 세운 상세 상호작용 분석 섹션 (NEW) ---
            if 'selected_seyun_year' in st.session_state:
                sel_year = st.session_state['selected_seyun_year']
                sel_seyun = next((s for s in seyun_list if s['year'] == sel_year), None)
                sel_daeun_age = st.session_state.get('selected_daeun_age')
                sel_daeun = next((d for d in data['fortune']['list'] if d['age'] == sel_daeun_age), None)
                
                if sel_seyun:
                    # 세운 상호작용 데이터 산출
                    def get_seyun_relation(target_pillar_val, target_name):
                        if not target_pillar_val or len(target_pillar_val) < 2: return {}
                        s_ganzhi = sel_seyun['ganzhi']
                        s_stem, s_branch = s_ganzhi[0], s_ganzhi[1]
                        t_stem, t_branch = target_pillar_val[0], target_pillar_val[1]
                        
                        from saju_utils import GAN_TEN_GODS, TWELVE_GROWTH, STEM_RELATIONS, BRANCH_RELATIONS
                        day_gan = pillars['day']['stem']
                        
                        inter_rels = []
                        sinsal_rels = []
                        if STEM_RELATIONS['충'].get(s_stem) == t_stem: inter_rels.append("천간충(沖)")
                        if STEM_RELATIONS['합'].get(s_stem) == t_stem: inter_rels.append("천간합(合)")
                        if BRANCH_RELATIONS['충'].get(s_branch) == t_branch: inter_rels.append("충(沖)")
                        if BRANCH_RELATIONS['합'].get(s_branch) == t_branch: inter_rels.append("합(合)")
                        
                        h_val = BRANCH_RELATIONS['형'].get(s_branch)
                        if h_val:
                            if isinstance(h_val, list):
                                if t_branch in h_val: inter_rels.append("형(刑)")
                            elif h_val == t_branch: inter_rels.append("형(刑)")
                        
                        if BRANCH_RELATIONS['파'].get(s_branch) == t_branch: inter_rels.append("파(破)")
                        if BRANCH_RELATIONS['해'].get(s_branch) == t_branch: inter_rels.append("해(害)")
                        if BRANCH_RELATIONS['원진'].get(s_branch) == t_branch: sinsal_rels.append("원진(元嗔)")
                        if BRANCH_RELATIONS['귀문'].get(s_branch) == t_branch: sinsal_rels.append("귀문(鬼門)")
                        
                        year_branch = pillars['year']['branch']
                        from saju_utils import get_sinsal_list
                        twelve_sinsal = get_sinsal_list(year_branch, s_branch)
                        if twelve_sinsal and twelve_sinsal not in sinsal_rels: sinsal_rels.append(twelve_sinsal)
                        
                        return {
                            "name": target_name,
                            "ganzhi": target_pillar_val,
                            "ten_god": GAN_TEN_GODS.get(day_gan, {}).get(t_stem, '-'),
                            "growth": TWELVE_GROWTH.get(s_stem, {}).get(t_branch, '-'),
                            "sinsal": ", ".join(sinsal_rels) if sinsal_rels else "-",
                            "interaction": ", ".join(inter_rels) if inter_rels else "평온"
                        }

                    targets = [
                        ('hour', pillars['hour']['pillar'], "시주"),
                        ('day', pillars['day']['pillar'], "일주"),
                        ('month', pillars['month']['pillar'], "월주"),
                        ('year', pillars['year']['pillar'], "연주"),
                        ('daeun', sel_daeun['ganzhi'] if sel_daeun else None, "대운")
                    ]
                    sy_data = [get_seyun_relation(t[1], t[2]) for t in targets if t[1]]

                    # 이미지 2 스타일 세운 상세 분석 테이블 호출
                    syc_headers = [d['name'] for d in sy_data]
                    sy_grid = [
                        [d['ganzhi'] for d in sy_data],
                        [d['ten_god'] for d in sy_data],
                        [d['growth'] for d in sy_data],
                        [d['sinsal'] for d in sy_data],
                        [d['interaction'] for d in sy_data]
                    ]
                    
                    render_analysis_table(
                        f"{sel_year}년 세운({sel_seyun['ganzhi']}) 상세 분석",
                        f"선택하신 세운이 원국(4주) 및 현재 대운({sel_daeun['ganzhi'] if sel_daeun else '-'})과 맺는 복합 상호작용을 풀이합니다.",
                        ["대상 사주 간지", "대상 기둥 십성", "세운 적용 운성", "적용 신살·귀인", "상호 관계 분석"],
                        syc_headers, sy_grid
                    )
                    
                    st.markdown("---")

            # 월운(Wolun) 시각화 - 선택된 연도 기준
            from saju_utils import get_wolun_data
            sel_year = st.session_state.get('selected_seyun_year', now_year)
            st.subheader(f"📅 {sel_year}년 월별 운세 흐름")
            
            # 선택된 연도 세운 정보 찾기
            cur_seyun = next((s for s in seyun_list if s['year'] == sel_year), seyun_list[0] if seyun_list else {})
            
            st.markdown('<div class="wolun-grid">', unsafe_allow_html=True)
            w_cols = st.columns(4)
            for m in range(1, 13):
                wolun = get_wolun_data(pillars.get('day', {}).get('stem', '甲'), 
                                     pillars.get('year', {}).get('branch', '子'), 
                                     cur_seyun.get('ganzhi', '甲子'), m, 
                                     pillars=pillars, 
                                     day_branch=pillars.get('day', {}).get('branch', '丑'))
                
                selected_month = st.session_state.get('selected_wolun_month', datetime.datetime.now().month)
                is_sel_month = selected_month == m
                card_class = "saju-card selected" if is_sel_month else "saju-card"
                
                with w_cols[(m-1) % 4]:
                    render_saju_card(
                        f"{m}월",
                        wolun.get('ganzhi', '-'),
                        wolun.get('stem_ten_god', '-'),
                        wolun.get('branch_ten_god', '-'),
                        wolun.get('twelve_growth', '-'),
                        f"✨ 신살: {wolun.get('sinsal', '-')}",
                        "-",
                        is_sel_month
                    )
                    if st.button(f"{m}월 선택", key=f"btn_month_{m}", use_container_width=True):
                        st.session_state['selected_wolun_month'] = m
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # --- 월운 상세 상호작용 분석 섹션 (NEW) ---
        sel_month = st.session_state.get('selected_wolun_month')
        if sel_month:
            sel_year = st.session_state.get('selected_seyun_year', now_year)
            cur_seyun = next((s for s in seyun_list if s['year'] == sel_year), seyun_list[0])
            from saju_utils import get_wolun_data
            wol_data = get_wolun_data(pillars['day']['stem'], pillars['year']['branch'], cur_seyun['ganzhi'], sel_month, pillars, pillars['day']['branch'])
            
            # 월운 상호작용 데이터 산출
            mw_targets = [
                ('year', "연주"), ('month', "월주"), ('day', "일주"), ('hour', "시주"),
                ('daeun', "대운"), ('seyun', "세운")
            ]
            mw_data = []
            w_gz = wol_data['ganzhi']
            w_stem, w_branch = w_gz[0], w_gz[1]
            
            from saju_utils import GAN_TEN_GODS, TWELVE_GROWTH, STEM_RELATIONS, BRANCH_RELATIONS
            for k, label in mw_targets:
                if k == 'daeun': gz = sel_daeun['ganzhi'] if sel_daeun else "-"
                elif k == 'seyun': gz = cur_seyun['ganzhi'] if cur_seyun else "-"
                else: 
                    gz_info = pillars.get(k, {})
                    gz = gz_info.get('pillar', '-') if isinstance(gz_info, dict) else "-"
                
                if gz != "-" and len(gz) >= 2:
                    t_stem, t_branch = gz[0], gz[1]
                else:
                    t_stem, t_branch = "-", "-"
                
                rels = []
                if t_stem != "-" and STEM_RELATIONS['충'].get(w_stem) == t_stem: rels.append("천간충")
                if t_stem != "-" and STEM_RELATIONS['합'].get(w_stem) == t_stem: rels.append("천간합")
                if t_branch != "-" and BRANCH_RELATIONS['충'].get(w_branch) == t_branch: rels.append("충")
                if t_branch != "-" and BRANCH_RELATIONS['합'].get(w_branch) == t_branch: rels.append("합")
                
                mw_data.append({
                    "label": label,
                    "ganzhi": gz,
                    "ten_god": GAN_TEN_GODS.get(pillars['day']['stem'], {}).get(t_stem, '-'),
                    "growth": TWELVE_GROWTH.get(w_stem, {}).get(t_branch, '-'),
                    "interaction": ", ".join(rels) if rels else "평온"
                })

            # 이미지 2 스타일 월운 상세 분석 테이블 호출
            mw_headers = [d['label'] for d in mw_data if d['label'] != '항목']
            mw_grid = [
                [d['ganzhi'] for d in mw_data],
                [d['ten_god'] for d in mw_data],
                [d['growth'] for d in mw_data],
                [d['interaction'] for d in mw_data]
            ]
            
            render_analysis_table(
                f"{sel_month}월({wol_data['ganzhi']}) 상세 분석",
                f"선택하신 {sel_month}월의 기운이 원국(4주) 및 대운/세운과 맺는 관계를 분석합니다.",
                ["분석 대상 간지", "해당 기둥 십성", "월운 적용 운성", "상호 관계 분석"],
                ["연주", "월주", "일주", "시주", "대운", "세운"],
                mw_grid
            )

        st.divider()
        
        # --- AI 심층 분석 섹션 (5단계 전문 버튼) ---
        st.subheader("🔮 AI 명리 대가 전문 분석")
        
        # 버튼 스타일링 (그리드 레이아웃)
        add_query = st.text_input("AI 대가에게 특별히 궁금한 점 (선택 사항)", placeholder="예: 구체적인 건강운이나 조언이 궁금합니다.")
        
        b1, b2, b3 = st.columns(3)
        b4, b5, _ = st.columns(3)
        
        analysis_type = None
        if b1.button("📜 전체사주보기", use_container_width=True): analysis_type = "total"
        if b2.button("🌿 사주원국 해석", use_container_width=True): analysis_type = "original"
        if b3.button("🌊 선택한 대운 분석", use_container_width=True): analysis_type = "daeun"
        if b4.button("🎢 선택한 세운 분석", use_container_width=True): analysis_type = "seyun"
        if b5.button("🗓️ 선택한 월운 분석", use_container_width=True): analysis_type = "wolun"
        
        if analysis_type:
            if not api_key:
                st.error("API 키가 설정되지 않았습니다.")
                return
                
            model = initialize_saju_engine(api_key)
            with st.status("대가의 식견으로 분석 중입니다...", expanded=True) as status:
                try:
                    name_str = st.session_state.get('target_name', '사용자')
                    gender_str = st.session_state.get('target_gender', '여')
                    birth_year = int(data['birth_date'].split('-')[0])
                    cur_age = now_year - birth_year + 1
                    
                    # 1. 공통 사주 기초 정보
                    basic_info = f"""
[사주 정보]
- 성별: {gender_str}
- 생년월일시: (양) {data['birth_date']} {data['birth_time']}
- 사주팔자: 년주({pillars['year']['pillar']}), 월주({pillars['month']['pillar']}), 일주({pillars['day']['pillar']}), 시주({pillars['hour']['pillar']})
- 십성: 년간({pillars['year'].get('stem_ten_god','-')}), 년지({pillars['year'].get('branch_ten_god','-')}), 월간({pillars['month'].get('stem_ten_god','-')}), 월지({pillars['month'].get('branch_ten_god','-')}), 일지({pillars['day'].get('branch_ten_god','-')}), 시간({pillars['hour'].get('stem_ten_god','-')}), 시지({pillars['hour'].get('branch_ten_god','-')})
- 십이운성: 년지({pillars['year'].get('twelve_growth','-')}), 월지({pillars['month'].get('twelve_growth','-')}), 일지({pillars['day'].get('twelve_growth','-')}), 시지({pillars['hour'].get('twelve_growth','-')})
- 오행 분포: 木 {elems.get('木',0)}, 火 {elems.get('火',0)}, 土 {elems.get('土',0)}, 金 {elems.get('金',0)}, 水 {elems.get('水',0)}
"""
                    
                    # 2. 분석 타입별 맞춤 프롬프트 구성
                    prompt = ""
                    common_instr = "본 분석은 데스티니 코드 정밀한 로직으로 산출된 데이터를 바탕으로 합니다. 제공된 사주 정보는 검증된 값이므로 다시 계산하지 말고, 이 데이터를 절대적 기준으로 해석하십시오. 답변 시작 시 '데스티니 코드 앱의 데이터를 바탕으로 해석함을 가볍게 언급하며, 전문가의 품격에 맞는 존댓말로 답변해 주십시오."
                    
                    if analysis_type == "total":
                        prompt = f"""
{basic_info}
[질문 사항]
{add_query if add_query else '전체적인 인생 흐름 분석 부탁드립니다.'}

위 사주 명식을 비유와 통찰을 담아 종합적으로 분석해 보고서 형식으로 작성해 주세요. (가독성 높은 구성 필수)
"""
                    elif analysis_type == "original":
                        prompt = f"""
{basic_info}
[질문 사항]
위 데이터를 바탕으로 명리학 전문가의 관점에서 다음 사항을 상세히 분석해 주십시오.
1. 일간과 일주를 중심으로 본연의 기질과 중심 성격을 설명해 주십시오.
2. 월지에 배정된 기운과 전체적인 십성의 흐름을 바탕으로, 이 사주가 사회에서 어떤 환경에 놓이기 쉬우며 어떤 방식으로 역량을 발휘하는지 분석해 주십시오.
3. 주어진 십성 구성에서 나타나는 특징적인 장단점과 그에 따른 인생 흐름의 특성을 분석해 주십시오.
4. 제공된 오행 분포 수치를 절대적 기준으로 삼아, 부족하거나 과한 기운을 조절할 수 있는 실생활의 보완책(색상, 습관 등)을 제안해 주십시오.
5. 재물운, 연애·결혼운, 직업 적성, 건강운 등 주요 영역을 주어진 데이터를 근거로 종합 해석해 주십시오.
6. 전체적인 사주 구성의 균형을 맞추기 위해 이 사주가 지향해야 할 삶의 태도와 핵심적인 조언을 들려주십시오.
"""
                    elif analysis_type == "daeun":
                        sel_age = st.session_state.get('selected_daeun_age')
                        sel_daeun = next((d for d in data['fortune']['list'] if d['age'] == sel_age), data['fortune']['list'][0])
                        prompt = f"""
{basic_info}
[대운 정보]
- 시작되는 나이: {sel_daeun['age']} 세
- 대운 간지: {sel_daeun['ganzhi']}
- 십성: {sel_daeun.get('stem_ten_god','-')}(천간) / {sel_daeun.get('branch_ten_god','-')}(지지)
- 십이운성: {sel_daeun.get('twelve_growth','-')}

[질문 사항]
위 데이터를 바탕으로 명리학 전문가의 관점에서 다음 사항을 상세히 분석해 주십시오.
1. 현재 지나고 있는 '대운'의 간지와 십성 정보를 바탕으로, 이 시기가 사주 원국에 가져오는 전반적인 운의 흐름과 환경 변화를 분석해 주십시오.
2. 제공된 대운의 십성(천간/지지)과 12운성 수치를 절대적 근거로 삼아, 이 시기에 나타날 사회적 성취 가능성과 심리적 변화를 심층 설명해 주십시오.
3. 이 대운 기간 동안의 직업 및 재물운, 그리고 건강과 대인관계를 포함한 개인적 삶의 영역에서 예상되는 주요 변화를 분석해 주십시오.
4. 명리학 전문가의 관점에서 이 시기에 반드시 잡아야 할 기회와, 특별히 주의하거나 보완해야 할 점을 구체적으로 조언해 주십시오.
5. 본 대운이 다음 대운으로 넘어가는 과정에서 이 사주가 가져야 할 마음가짐과 현실적인 행동 지침을 들려주십시오.
"""
                    elif analysis_type == "seyun":
                        sel_age = st.session_state.get('selected_daeun_age')
                        sel_daeun = next((d for d in data['fortune']['list'] if d['age'] == sel_age), data['fortune']['list'][0])
                        sel_year = st.session_state.get('selected_seyun_year', now_year)
                        sel_seyun = next((s for s in seyun_list if s['year'] == sel_year), seyun_list[0])
                        prompt = f"""
{basic_info}
[현재 대운 정보]
- 나이: {sel_daeun['age']} 세 ~
- 간지: {sel_daeun['ganzhi']}
- 십성: {sel_daeun.get('stem_ten_god','-')}(천간) / {sel_daeun.get('branch_ten_god','-')}(지지)
- 십이운성: {sel_daeun.get('twelve_growth','-')}

[세운 정보]
- 세운 년도: {sel_year}년
- 세운 간지: {sel_seyun['ganzhi']}
- 십성: {sel_seyun.get('stem_ten_god','-')}(천간) / {sel_seyun.get('branch_ten_god','-')}(지지)
- 십이운성: {sel_seyun.get('twelve_growth','-')}

[질문 사항]
위 데이터를 바탕으로 명리학 전문가의 관점에서 다음 사항을 상세히 분석해 주십시오.
1. 위의 세운 정보를 바탕으로, 올해가 사주 원국 및 현재 대운과 상호작용하여 만들어내는 핵심 운의 흐름을 분석해 주십시오.
2. 제공된 세운의 십성과 12운성 기운을 절대적 근거로 하여, 직업, 재물, 대인관계, 건강 등 실생활 영역의 변화를 설명해 주십시오.
3. 올해 가장 주목해야 할 긍정적인 기회와 전문가적 관점에서 주의가 필요한 리스크를 짚어 주십시오.
4. 올해의 기운을 가장 현명하게 활용하기 위해 취해야 할 구체적인 태도와 행동 지침을 조언해 주십시오.
"""
                    elif analysis_type == "wolun":
                        sel_year = st.session_state.get('selected_seyun_year', now_year)
                        cur_seyun = next((s for s in seyun_list if s['year'] == sel_year), seyun_list[0])
                        from saju_utils import get_wolun_data
                        target_month = st.session_state.get('selected_wolun_month', datetime.datetime.now().month)
                        wolun_data = get_wolun_data(pillars['day']['stem'], pillars['year']['branch'], cur_seyun['ganzhi'], target_month, pillars, pillars['day']['branch'])
                        
                        prompt = f"""
{basic_info}
[현재 대운 정보]
- 간지: {sel_daeun['ganzhi']}
- 십성: {sel_daeun.get('stem_ten_god','-')}(천간) / {sel_daeun.get('branch_ten_god','-')}(지지)

[현재 세운 정보]
- 년도: {sel_year}년
- 세운 간지: {cur_seyun['ganzhi']}
- 십성: {cur_seyun.get('stem_ten_god','-')}(천간) / {cur_seyun.get('branch_ten_god','-')}(지지)

[월운 정보]
- 년월: {sel_year}년 {target_month}월
- 월운 간지: {wolun_data['ganzhi']}
- 십성: {wolun_data['stem_ten_god']}(천간) / {wolun_data['branch_ten_god']}(지지)
- 십이운성: {wolun_data['twelve_growth']} (일간 기준)

[질문 사항]
위 데이터를 바탕으로 명리학 전문가의 관점에서 다음 사항을 상세히 분석해 주십시오.
1. 월운 간지와 십성, 12운성 정보를 바탕으로, 이번 달이 전체적인 세운 흐름 속에서 어떤 구체적인 변곡점이 되는지 분석해 주십시오.
2. 제공된 월운의 십성 기운을 절대적 기준으로 삼아, 이번 달 직업적 성과, 재물 흐름, 대인관계의 변화를 실질적인 관점에서 설명해 주십시오.
3. 이번 달에 특히 집중해야 할 긍정적인 기회와, 예기치 않게 발생할 수 있는 부정적인 변수를 관리하기 위한 현실적인 조언을 제시해 주십시오.
4. 해당 월의 12운성 기운이 시사하는 심리적 상태를 고려하여, 이번 한 달을 가장 후회 없이 보낼 수 있는 핵심 행동 지침을 들려주십시오.
"""

                    full_prompt = f"{common_instr}\n\n{prompt}"
                    
                    if st.session_state.get('is_cached', False):
                        response = model.generate_content(full_prompt)
                    else:
                        response = model.generate_content([full_prompt] + st.session_state.get('uploaded_file_objects', []))
                    
                    if response and response.text:
                        st.balloons()
                        status.update(label="분석이 완료되었습니다.", state="complete", expanded=False)
                        st.divider()
                        st.markdown(f"### 📑 {name_str}님을 위한 전문가 분석 리포트")
                        st.markdown(f"<div class='result-container' id='report-text'>{response.text}</div>", unsafe_allow_html=True)
                        
                        report_content = response.text.replace("'", "\\'").replace("\n", "\\n")
                        copy_js = f"""
                        <script>
                        function copyReport() {{
                            const text = `{report_content}`;
                            const textArea = document.createElement("textarea");
                            textArea.value = text;
                            document.body.appendChild(textArea);
                            textArea.select();
                            try {{
                                document.execCommand('copy');
                                alert('보고서가 클립보드에 복사되었습니다.');
                            }} catch (err) {{ }}
                            document.body.removeChild(textArea);
                        }}
                        </script>
                        <button onclick="copyReport()" class="share-btn">📋 분석 결과 복사하여 공유하기</button>
                        """
                        st.components.v1.html(copy_js, height=70)
                    else:
                        st.error("결과를 도출하지 못했습니다.")
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")



if __name__ == "__main__":
    main()
