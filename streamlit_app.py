import streamlit as st
import os
import datetime
import google.generativeai as genai
from google.generativeai import caching
import glob
from sajupy import calculate_saju, get_saju_details, lunar_to_solar
from saju_utils import get_extended_saju_data

# 페이지 설정: 제목 및 아이콘
st.set_page_config(page_title="Destiny Code - AI 사주 풀이", page_icon="🔮", layout="centered")

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
                    
                    # 1. 먼저 전체 단어로 검색
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

        # 헤더
        h_cols = st.columns(5)
        headers = ["구분", "시주(時)", "일주(日)", "월주(月)", "연주(년)"]
        for i, h in enumerate(headers):
            h_cols[i].markdown(f"<div style='text-align:center; font-weight:bold; background-color:#f8f9fa; padding:5px; border-radius:5px;'>{h}</div>", unsafe_allow_html=True)

        # 데이터 행 정의
        rows = [
            ("천간", [pillars['hour']['stem'], pillars['day']['stem'], pillars['month']['stem'], pillars['year']['stem']]),
            ("지지", [pillars['hour']['branch'], pillars['day']['branch'], pillars['month']['branch'], pillars['year']['branch']]),
            ("십성", [data['ten_gods']['hour'], data['ten_gods']['day'], data['ten_gods']['month'], data['ten_gods']['year']]),
            ("지지십성", [data['jiji_ten_gods']['hour'], data['jiji_ten_gods']['day'], data['jiji_ten_gods']['month'], data['jiji_ten_gods']['year']]),
            ("12운성", [data['twelve_growth']['hour'], data['twelve_growth']['day'], data['twelve_growth']['month'], data['twelve_growth']['year']]),
            ("신살", [data['sinsal_details']['hour']['sinsal'], data['sinsal_details']['day']['sinsal'], data['sinsal_details']['month']['sinsal'], data['sinsal_details']['year']['sinsal']])
        ]

        for r_idx, (label, vals) in enumerate(rows):
            r_cols = st.columns(5)
            r_cols[0].markdown(f"<div style='text-align:center; padding:10px; font-size:0.9rem; color:#666;'>{label}</div>", unsafe_allow_html=True)
            for c_idx, val in enumerate(vals):
                with r_cols[c_idx+1]:
                    term_popover(label, val, f"{r_idx}_{c_idx}")
        
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

        # 대운(Daeun) 시각화 (신살/관계 추가 및 레이아웃 개선)
        st.subheader("📅 대운(大運)의 흐름")
        daeun_info = data['fortune']
        st.write(f"현재 대운수: **{daeun_info['num']}** ({daeun_info['direction']}, 대운이 바뀌는 나이)")
        
        df_list = data['fortune']['list']
        for i in range(0, len(df_list), 4):
            cols = st.columns(4)
            chunk = df_list[i:i+4]
            for idx, item in enumerate(chunk):
                with cols[idx]:
                    age_val = item.get('age', 0)
                    is_sel_daeun = st.session_state.get('selected_daeun_age') == age_val
                    border_css = "3px solid #d4af37" if is_sel_daeun else "1px solid #e0e0e0"
                    bg_css = "#fffcf0" if is_sel_daeun else "#ffffff"
                    
                    st.markdown(f"""
                    <div style='border:{border_css}; padding:12px; border-radius:12px; text-align:center; background-color:{bg_css}; margin-bottom:5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);'>
                        <div style='font-size:0.9rem; font-weight:bold; color:#ff9800;'>{age_val}세~</div>
                        <div style='font-size:1.6rem; font-weight:bold; color:#2c3e50; margin:5px 0;'>{item.get('ganzhi', '-')}</div>
                        <div style='font-size:0.85rem; color:#d32f2f;'>{item.get('stem_ten_god', '-')} | {item.get('branch_ten_god', '-')}</div>
                        <div style='font-size:0.8rem; color:#1976d2;'>{item.get('twelve_growth', '-')}</div>
                        <div style='font-size:0.75rem; color:#388e3c; margin-top:5px;'>✨ {item.get('sinsal', '-')}</div>
                        <div style='font-size:0.7rem; color:#7b1fa2;'>🔗 {item.get('relations', '-')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"{age_val}세 대운 선택", key=f"btn_daeun_{age_val}"):
                        st.session_state['selected_daeun_age'] = age_val
                        # 대운이 바뀌면 해당 대운의 시작 연도로 세운 선택값도 초기화
                        birth_year = int(data.get('birth_date', '1990-01-01').split('-')[0])
                        st.session_state['selected_seyun_year'] = birth_year + age_val - 1
                        st.rerun()

        # --- 대운 상세 상호작용 분석 섹션 (NEW) ---
        if 'selected_daeun_age' in st.session_state:
            sel_age = st.session_state['selected_daeun_age']
            sel_daeun = next((d for d in data['fortune']['list'] if d['age'] == sel_age), None)
            
            if sel_daeun:
                st.markdown(f"### 🔍 {sel_age}세 대운({sel_daeun['ganzhi']}) 상세 분석")
                st.info(f"선택하신 대운이 원국의 각 기둥(연,월,일,시)과 맺는 명리적 상호작용을 항목별로 풀이합니다.")
                
                # 상세 관계 데이터 재산출 (각 기둥별로 개별 관계 추출)
                def get_pillar_relation(pillar_key):
                    p = pillars[pillar_key]
                    name = {'year':'년', 'month':'월', 'day':'일', 'hour':'시'}[pillar_key]
                    d_ganzhi = sel_daeun['ganzhi']
                    if not d_ganzhi or len(d_ganzhi) < 2: return {}
                    d_stem, d_branch = d_ganzhi[0], d_ganzhi[1]
                    p_stem, p_branch = p['stem'], p['branch']
                    
                    # 십성 (대운 -> 원국 기준)
                    from saju_utils import GAN_TEN_GODS, BRANCH_HIDDEN_GANS, TWELVE_GROWTH, STEM_RELATIONS, BRANCH_RELATIONS
                    day_gan = pillars['day']['stem']
                    
                    # 관계 산출 (합충형파해 vs 신살 분리)
                    inter_rels = []
                    sinsal_rels = []
                    
                    if STEM_RELATIONS['충'].get(d_stem) == p_stem: inter_rels.append("충(沖)")
                    if STEM_RELATIONS['합'].get(d_stem) == p_stem: inter_rels.append("합(合)")
                    if BRANCH_RELATIONS['충'].get(d_branch) == p_branch: inter_rels.append("충(沖)")
                    if BRANCH_RELATIONS['합'].get(d_branch) == p_branch: inter_rels.append("합(合)")
                    
                    h_val = BRANCH_RELATIONS['형'].get(d_branch)
                    if h_val:
                        if isinstance(h_val, list):
                            if p_branch in h_val: inter_rels.append("형(刑)")
                        elif h_val == p_branch: inter_rels.append("형(刑)")
                    
                    if BRANCH_RELATIONS['파'].get(d_branch) == p_branch: inter_rels.append("파(破)")
                    if BRANCH_RELATIONS['해'].get(d_branch) == p_branch: inter_rels.append("해(害)")
                    
                    # 원진, 귀문은 신살 영역으로 분류
                    if BRANCH_RELATIONS['원진'].get(d_branch) == p_branch: sinsal_rels.append("원진(元嗔)")
                    if BRANCH_RELATIONS['귀문'].get(d_branch) == p_branch: sinsal_rels.append("귀문(鬼門)")
                    
                    # 12신살 추가 (년지 기준)
                    year_branch = pillars['year']['branch']
                    from saju_utils import get_sinsal_list
                    twelve_sinsal = get_sinsal_list(year_branch, d_branch)
                    if twelve_sinsal and twelve_sinsal not in sinsal_rels:
                        sinsal_rels.append(twelve_sinsal)
                    
                    return {
                        "ganzhi": p['pillar'],
                        "ten_god": GAN_TEN_GODS.get(day_gan, {}).get(p_stem, '-'),
                        "growth": TWELVE_GROWTH.get(d_stem, {}).get(p_branch, '-'),
                        "sinsal": ", ".join(sinsal_rels) if sinsal_rels else "-",
                        "interaction": ", ".join(inter_rels) if inter_rels else "평온"
                    }

                # 시각화 표 구성
                i_cols = st.columns(5)
                labels = ["분석 항목", "시주(時)", "일주(日)", "월주(月)", "연주(년)"]
                for i, l in enumerate(labels):
                    i_cols[i].markdown(f"<div style='text-align:center; font-weight:bold; background-color:#f0f2f6; padding:8px; border-radius:5px;'>{l}</div>", unsafe_allow_html=True)
                
                p_keys = ['hour', 'day', 'month', 'year']
                p_data = {k: get_pillar_relation(k) for k in p_keys}
                
                row_items = [
                    ("원국 간지", [p_data[k]['ganzhi'] for k in p_keys]),
                    ("해당 기둥 십성", [p_data[k]['ten_god'] for k in p_keys]),
                    ("대운 기준 운성", [p_data[k]['growth'] for k in p_keys]),
                    ("적용 신살", [p_data[k]['sinsal'] for k in p_keys]),
                    ("합·충·형·파·해", [p_data[k]['interaction'] for k in p_keys])
                ]
                
                for label, vals in row_items:
                    r_cols = st.columns(5)
                    r_cols[0].markdown(f"<div style='text-align:center; padding:12px; font-weight:700; color:#444; border-bottom:1px solid #eee;'>{label}</div>", unsafe_allow_html=True)
                    for c_idx, val in enumerate(vals):
                        with r_cols[c_idx+1]:
                            term_popover(label, val, f"daeun_{label}_{c_idx}")
                
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
                    
                    border_color = "#d63384" if is_sel_year else ("#ffc107" if is_now else "#e0e0e0")
                    bg_color = "#fff0f6" if is_sel_year else ("#fffdf0" if is_now else "#ffffff")
                    
                    with s_cols[idx]:
                        st.markdown(f"""
                        <div style='border:2px solid {border_color}; padding:10px; border-radius:12px; text-align:center; background-color:{bg_color}; margin-bottom:5px; min-height:180px;'>
                            <div style='font-size:0.8rem; font-weight:bold; color:#666;'>{s_year}년 {"(현재)" if is_now else ""}</div>
                            <div style='font-size:1.4rem; font-weight:bold; color:{border_color}; margin:3px 0;'>{s_item['ganzhi']}</div>
                            <div style='font-size:0.8rem; color:#d32f2f;'>{s_item['stem_ten_god']} | {s_item['branch_ten_god']}</div>
                            <div style='font-size:0.75rem; color:#1976d2;'>{s_item['twelve_growth']}</div>
                            <div style='font-size:0.7rem; color:#388e3c; margin-top:3px;'>✨ {s_item['sinsal']}</div>
                            <div style='font-size:0.65rem; color:#7b1fa2;'>🔗 {s_item['relations']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"{s_year}년 선택", key=f"btn_year_{s_year}"):
                            st.session_state['selected_seyun_year'] = s_year
                            st.rerun()

            # --- 세운 상세 상호작용 분석 섹션 (NEW) ---
            if 'selected_seyun_year' in st.session_state:
                sel_year = st.session_state['selected_seyun_year']
                sel_seyun = next((s for s in seyun_list if s['year'] == sel_year), None)
                sel_daeun_age = st.session_state.get('selected_daeun_age')
                sel_daeun = next((d for d in data['fortune']['list'] if d['age'] == sel_daeun_age), None)
                
                if sel_seyun:
                    st.markdown(f"### 🔍 {sel_year}년 세운({sel_seyun['ganzhi']}) 상세 분석")
                    st.info(f"선택하신 세운이 원국(4주) 및 현재 대운({sel_daeun['ganzhi'] if sel_daeun else '-'})과 맺는 복합 상호작용을 풀이합니다.")
                    
                    # 관계 산출 함수 (세운 기준)
                    def get_seyun_relation(target_pillar_val, target_name):
                        if not target_pillar_val or len(target_pillar_val) < 2: return {}
                        s_ganzhi = sel_seyun['ganzhi']
                        s_stem, s_branch = s_ganzhi[0], s_ganzhi[1]
                        t_stem, t_branch = target_pillar_val[0], target_pillar_val[1]
                        
                        from saju_utils import GAN_TEN_GODS, TWELVE_GROWTH, STEM_RELATIONS, BRANCH_RELATIONS
                        day_gan = pillars['day']['stem']
                        
                        # 관계 산출 (합충형파해 vs 신살 분리)
                        inter_rels = []
                        sinsal_rels = []
                        
                        if STEM_RELATIONS['충'].get(s_stem) == t_stem: inter_rels.append("충(沖)")
                        if STEM_RELATIONS['합'].get(s_stem) == t_stem: inter_rels.append("합(合)")
                        if BRANCH_RELATIONS['충'].get(s_branch) == t_branch: inter_rels.append("충(沖)")
                        if BRANCH_RELATIONS['합'].get(s_branch) == t_branch: inter_rels.append("합(合)")
                        
                        h_val = BRANCH_RELATIONS['형'].get(s_branch)
                        if h_val:
                            if isinstance(h_val, list):
                                if t_branch in h_val: inter_rels.append("형(刑)")
                            elif h_val == t_branch: inter_rels.append("형(刑)")
                        
                        if BRANCH_RELATIONS['파'].get(s_branch) == t_branch: inter_rels.append("파(破)")
                        if BRANCH_RELATIONS['해'].get(s_branch) == t_branch: inter_rels.append("해(害)")
                        
                        # 원진, 귀문은 신살 영역으로 분류
                        if BRANCH_RELATIONS['원진'].get(s_branch) == t_branch: sinsal_rels.append("원진(元嗔)")
                        if BRANCH_RELATIONS['귀문'].get(s_branch) == t_branch: sinsal_rels.append("귀문(鬼門)")
                        
                        # 12신살 (년지 기준)
                        year_branch = pillars['year']['branch']
                        from saju_utils import get_sinsal_list
                        twelve_sinsal = get_sinsal_list(year_branch, s_branch)
                        if twelve_sinsal and twelve_sinsal not in sinsal_rels:
                            sinsal_rels.append(twelve_sinsal)
                        
                        return {
                            "name": target_name,
                            "ganzhi": target_pillar_val,
                            "ten_god": GAN_TEN_GODS.get(day_gan, {}).get(t_stem, '-'),
                            "growth": TWELVE_GROWTH.get(s_stem, {}).get(t_branch, '-'),
                            "sinsal": ", ".join(sinsal_rels) if sinsal_rels else "-",
                            "interaction": ", ".join(inter_rels) if inter_rels else "평온"
                        }

                    # 분석 대상 설정: 4주 원국 + 대운
                    targets = [
                        ('hour', pillars['hour']['pillar'], "시주"),
                        ('day', pillars['day']['pillar'], "일주"),
                        ('month', pillars['month']['pillar'], "월주"),
                        ('year', pillars['year']['pillar'], "연주"),
                        ('daeun', sel_daeun['ganzhi'] if sel_daeun else None, "대운")
                    ]
                    
                    sy_data = [get_seyun_relation(t[1], t[2]) for t in targets if t[1]]
                    
                    # 5-6열 테이블 (항목 + 분석 대상 수만큼)
                    num_cols = len(sy_data) + 1
                    syc_cols = st.columns(num_cols)
                    
                    syc_labels = ["분석 항목"] + [d['name'] for d in sy_data]
                    for i, l in enumerate(syc_labels):
                        syc_cols[i].markdown(f"<div style='text-align:center; font-weight:bold; background-color:#fff0f6; padding:8px; border-radius:5px; font-size:0.85rem;'>{l}</div>", unsafe_allow_html=True)
                    
                    sy_row_items = [
                        ("대상 간지", [d['ganzhi'] for d in sy_data]),
                        ("대상 십성", [d['ten_god'] for d in sy_data]),
                        ("세운 기준 운성", [d['growth'] for d in sy_data]),
                        ("적용 신살", [d['sinsal'] for d in sy_data]),
                        ("상호 관계", [d['interaction'] for d in sy_data])
                    ]
                    
                    for label, vals in sy_row_items:
                        r_cols = st.columns(num_cols)
                        r_cols[0].markdown(f"<div style='text-align:center; padding:10px; font-weight:700; color:#444; border-bottom:1px solid #eee; font-size:0.8rem;'>{label}</div>", unsafe_allow_html=True)
                        for c_idx, val in enumerate(vals):
                            with r_cols[c_idx+1]:
                                term_popover(label, val, f"seyun_{label}_{c_idx}")
                    
                    st.markdown("---")

            # 월운(Wolun) 시각화 - 선택된 연도 기준
            from saju_utils import get_wolun_data
            sel_year = st.session_state.get('selected_seyun_year', now_year)
            st.subheader(f"📅 {sel_year}년 월별 운세 흐름")
            
            # 선택된 연도 세운 정보 찾기
            cur_seyun = next((s for s in seyun_list if s['year'] == sel_year), seyun_list[0] if seyun_list else {})
            
            w_cols = st.columns(4)
            for m in range(1, 13):
                wolun = get_wolun_data(pillars.get('day', {}).get('stem', '甲'), 
                                     pillars.get('year', {}).get('branch', '子'), 
                                     cur_seyun.get('ganzhi', '甲子'), m, 
                                     pillars=pillars, 
                                     day_branch=pillars.get('day', {}).get('branch', '丑'))
                with w_cols[(m-1) % 4]:
                    st.markdown(f"""
                    <div style='border:1px solid #f0f0f0; padding:10px; border-radius:12px; text-align:center; background-color:#fff; margin-bottom:10px; border-left:4px solid #ffc107;'>
                        <div style='font-size:0.85rem; font-weight:bold; color:#666;'>{m}월</div>
                        <div style='font-size:1.3rem; font-weight:bold; color:#2c3e50;'>{wolun.get('ganzhi', '-')}</div>
                        <div style='font-size:0.8rem; color:#d63384;'>{wolun.get('stem_ten_god', '-')} | {wolun.get('branch_ten_god', '-')}</div>
                        <div style='font-size:0.7rem; color:#1976d2;'>{wolun.get('twelve_growth', '-')}</div>
                        <div style='font-size:0.7rem; color:#198754;'>{wolun.get('sinsal', '-')}</div>
                    </div>
                    """, unsafe_allow_html=True)

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
                    selected_daeun_info = next((d for d in data['fortune']['list'] if d['age'] == st.session_state.get('selected_daeun_age')), data['fortune']['list'][0])
                    
                    saju_summary = f"""
                    [대상자] {name_str} ({gender_str}), 현재 나이: {now_year - int(data['birth_date'].split('-')[0]) + 1}세
                    [양력 생일] {data['birth_date']} {data['birth_time']}
                    [사주 4주] 연:{pillars['year']['pillar']}, 월:{pillars['month']['pillar']}, 일:{pillars['day']['pillar']}, 시:{pillars['hour']['pillar']}
                    [오행분포] {elems}
                    [공망] 년:{data['gongmang']['year']}, 일:{data['gongmang']['day']}
                    [신살 및 관계] {data['sinsal']}, {data['relations']}
                    
                    [핵심 분석 대상 - 임의 선택 또는 현재 대운] {selected_daeun_info['age']}세 대운 ({selected_daeun_info['ganzhi']})
                    [현재 분석 기준 연도] {sel_year}년 ({cur_seyun['ganzhi'] if cur_seyun else 'N/A'})
                    
                    **분석 가이드:**
                    1. 과거 대운보다는 **현재 나이({now_year - int(data['birth_date'].split('-')[0]) + 1}세)**와 **현재 진행 중인 대운({selected_daeun_info['ganzhi']})**의 관계를 최우선적으로 해석하십시오.
                    2. 특히 선택된 분석 기준 연도({sel_year}년)의 세운과 월별 흐름이 사용자의 인생 여정에서 어떤 의미를 갖는지 구체적으로 조언하십시오.
                    """
                    
                    prompt = f"""
                    {saju_summary}
                    [사용자 추가 질문] {add_query if add_query else '전체적인 인생의 흐름과 운세 분석 부탁드립니다.'}
                    
                    위 사주 명식을 바탕으로 당신이 가진 전문 명리 지식(PDF)을 활용하여 분석하되, 
                    **일반인도 한눈에 이해할 수 있도록 친절하고 쉬운 비유**를 사용하여 보고서를 작성해 주세요.
                    
                    보고서 구성 필수 항목:
                    1. 🖼️ **운명의 풍경**: 이 사주의 구성을 한 폭의 그림이나 풍경으로 묘사해 주세요.
                    2. 🌱 **나의 본 모습**: 비유를 통해 타고난 성정과 기질, 장단점을 쉽게 설명해 주세요.
                    3. 🎢 **대운과 세운의 흐름**: 현재 대운(10년 주기)과 올해 세운, 그리고 월별 흐름을 종합하여 날씨나 계절 변화에 비유하여 알려주세요.
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



if __name__ == "__main__":
    main()
