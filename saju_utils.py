
"""
사주 명리학 계산을 위한 유틸리티 모듈
- 오행, 십성, 12운성, 대운, 세운, 신살, 형충회합 매핑 및 계산 로직 포함
"""
import pandas as pd
from datetime import datetime

# 천간 및 지지
HEAVENLY_STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
EARTHLY_BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 60갑자 리스트 (오타 전수 수정)
GANZHI_LIST = [
    '甲子', '乙丑', '丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉',
    '甲戌', '乙亥', '丙子', '丁丑', '戊寅', '己卯', '庚辰', '辛巳', '壬午', '癸未',
    '甲申', '乙酉', '丙戌', '丁亥', '戊子', '己丑', '庚寅', '辛卯', '壬辰', '癸巳',
    '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑', '壬寅', '癸卯',
    '甲辰', '乙巳', '丙午', '丁未', '戊申', '己酉', '庚戌', '辛亥', '壬子', '癸丑',
    '甲寅', '乙卯', '丙辰', '丁巳', '戊午', '己未', '庚申', '辛酉', '壬戌', '癸亥'
]
# 오타 최종 확인 및 강제 수정
GANZHI_LIST[19] = '癸未'
GANZHI_LIST[31] = '乙未'
GANZHI_LIST[36] = '庚子'
GANZHI_LIST[48] = '壬子'

# 오행 매핑
ELEMENTS_MAP = {
    '甲': '목', '乙': '목', '丙': '화', '丁': '화', '戊': '토', '己': '토', '庚': '금', '辛': '금', '壬': '수', '癸': '수',
    '寅': '목', '卯': '목', '巳': '화', '午': '화', '辰': '토', '戌': '토', '丑': '토', '未': '토', '申': '금', '酉': '금', '亥': '수', '子': '수'
}

# 십성 매핑 (오타 교정: 己 - 丁)
GAN_TEN_GODS = {
    '甲': {'甲':'비견','乙':'겁재','丙':'식신','丁':'상관','戊':'편재','己':'정재','庚':'편관','辛':'정관','壬':'편인','癸':'정인'},
    '乙': {'甲':'겁재','乙':'비견','丙':'상관','丁':'식신','戊':'정재','己':'편재','庚':'정관','辛':'편관','壬':'정인','癸':'편인'},
    '丙': {'甲':'편인','乙':'정인','丙':'비견','丁':'겁재','戊':'식신','己':'상관','庚':'편재','辛':'정재','壬':'편관','癸':'정관'},
    '丁': {'甲':'정인','乙':'편인','丙':'겁재','丁':'비견','戊':'상관','己':'식신','庚':'정재','辛':'편재','壬':'정관','癸':'편관'},
    '戊': {'甲':'편관','乙':'정관','丙':'편인','丁':'정인','戊':'비견','己':'겁재','庚':'식신','辛':'상관','壬':'편재','癸':'정재'},
    '己': {'甲':'정관','乙':'편관','丙':'정인','丁':'편인','戊':'겁재','己':'비견','庚':'상관','辛':'식신','壬':'정재','癸':'편재'},
    '庚': {'甲':'편재','乙':'정재','丙':'편관','丁':'정관','戊':'편인','己':'정인','庚':'비견','辛':'겁재','壬':'식신','癸':'상관'},
    '辛': {'甲':'정재','乙':'편재','丙':'정관','丁':'편관','戊':'정인','己':'편인','庚':'겁재','辛':'비견','壬':'상관','癸':'식신'},
    '壬': {'甲':'식신','乙':'상관','丙':'편재','丁':'정재','戊':'편관','己':'정관','庚':'편인','辛':'정인','壬':'비견','癸':'겁재'},
    '癸': {'甲':'상관','乙':'식신','丙':'정재','丁':'편재','戊':'정관','己':'정관','庚':'정인','辛':'편인','壬':'겁재','癸':'비견'}
}

# 지장간 정기
BRANCH_HIDDEN_GANS = {
    '子': '癸', '丑': '己', '寅': '甲', '卯': '乙',
    '辰': '戊', '巳': '丙', '午': '丁', '未': '己',
    '申': '庚', '酉': '辛', '戌': '戊', '亥': '壬'
}

# 12운성 (오타 전수 수정)
TWELVE_GROWTH = {
    '甲': { '亥': '장생', '子': '목욕', '丑': '관대', '寅': '건록', '卯': '제왕', '辰': '쇠', '巳': '병', '午': '사', '未': '묘', '申': '절', '酉': '태', '戌': '양' },
    '乙': { '午': '장생', '巳': '목욕', '辰': '관대', '卯': '건록', '寅': '제왕', '丑': '쇠', '子': '병', '亥': '사', '戌': '묘', '酉': '절', '申': '태', '未': '양' },
    '丙': { '寅': '장생', '卯': '목욕', '辰': '관대', '巳': '건록', '午': '제왕', '未': '쇠', '申': '병', '酉': '사', '戌': '묘', '亥': '절', '子': '태', '丑': '양' },
    '丁': { '酉': '장생', '申': '목욕', '未': '관대', '午': '건록', '巳': '제왕', '辰': '쇠', '卯': '병', '寅': '사', '丑': '묘', '子': '절', '亥': '태', '戌': '양' },
    '戊': { '寅': '장생', '卯': '목욕', '辰': '관대', '巳': '건록', '午': '제왕', '未': '쇠', '申': '병', '酉': '사', '戌': '묘', '亥': '절', '子': '태', '丑': '양' },
    '己': { '酉': '장생', '申': '목욕', '未': '관대', '午': '건록', '巳': '제왕', '辰': '쇠', '卯': '병', '寅': '사', '丑': '묘', '子': '절', '亥': '태', '戌': '양' },
    '庚': { '巳': '장생', '辰': '목욕', '卯': '관대', '寅': '건록', '丑': '제왕', '子': '쇠', '亥': '병', '戌': '사', '酉': '묘', '申': '절', '未': '태', '午': '양' },
    '辛': { '子': '장생', '亥': '목욕', '戌': '관대', '酉': '건록', '申': '제왕', '未': '쇠', '午': '병', '巳': '사', '辰': '묘', '卯': '절', '寅': '태', '丑': '양' },
    '壬': { '申': '장생', '酉': '목욕', '戌': '관대', '亥': '건록', '子': '제왕', '丑': '쇠', '寅': '병', '卯': '사', '辰': '묘', '巳': '절', '午': '태', '未': '양' },
    '癸': { '卯': '장생', '寅': '목욕', '丑': '관대', '子': '건록', '亥': '제왕', '戌': '쇠', '酉': '병', '申': '사', '未': '묘', '午': '절', '巳': '태', '辰': '양' }
}

# 천간 합/충 매핑
STEM_RELATIONS = {
    '합': {'甲':'己', '己':'甲', '乙':'庚', '庚':'乙', '丙':'辛', '辛':'丙', '丁':'壬', '壬':'丁', '戊':'癸', '癸':'戊'},
    '충': {'甲':'庚', '庚':'甲', '乙':'辛', '辛':'乙', '丙':'壬', '壬':'丙', '丁':'癸', '癸':'丁'}
}

# 지지 형충회합 매핑
BRANCH_RELATIONS = {
    '합': {'子':'丑', '丑':'子', '寅':'亥', '亥':'寅', '卯':'戌', '戌':'卯', '辰':'酉', '酉':'辰', '巳':'申', '申':'巳', '午':'未', '未':'午'},
    '충': {'子':'午', '午':'子', '丑':'未', '未':'丑', '寅':'申', '申':'寅', '卯':'酉', '酉':'卯', '辰':'戌', '戌':'辰', '巳':'亥', '亥':'巳'},
}

def get_ganzhi_index(ganzhi):
    try: return GANZHI_LIST.index(ganzhi)
    except: return -1

def get_next_ganzhi(ganzhi, step=1):
    idx = get_ganzhi_index(ganzhi)
    if idx == -1: return ""
    return GANZHI_LIST[(idx + step) % 60]

def get_prev_ganzhi(ganzhi, step=1):
    idx = get_ganzhi_index(ganzhi)
    if idx == -1: return ""
    return GANZHI_LIST[(idx - step) % 60]

def calculate_daeun_number(year, month, day, hour, minute, is_forward):
    """대운수 계산"""
    try:
        from sajupy import get_saju_calculator
        calc = get_saju_calculator()
        df = calc.data
        birth_dt = datetime(year, month, day, hour, minute)
        term_df = df[df['term_time'].notna() & (df['term_time'] != '')].copy()
        term_df['term_dt'] = pd.to_datetime(term_df['term_time'].astype(str).str.split('.').str[0], format='%Y%m%d%H%M')
        
        if is_forward:
            future_terms = term_df[term_df['term_dt'] >= birth_dt]
            if future_terms.empty: return 1
            target_term = future_terms.iloc[0]['term_dt']
        else:
            past_terms = term_df[term_df['term_dt'] <= birth_dt]
            if past_terms.empty: return 1
            target_term = past_terms.iloc[-1]['term_dt']
            
        diff = abs((target_term - birth_dt).total_seconds())
        daeun_num = round(diff / (24 * 3600) / 3)
        return max(1, daeun_num)
    except: return 1

def calculate_daeun(details, gender):
    """대운 정보 산출"""
    pillars = details['pillars']
    year_stem = pillars['year']['stem']
    month_pillar = pillars['month']['pillar']
    day_gan = pillars['day']['stem']
    is_yang_year = year_stem in ['甲', '丙', '戊', '庚', '壬']
    is_forward = (is_yang_year and gender == '남') or (not is_yang_year and gender == '여')
    
    y, m, d = map(int, details['birth_date'].split('-'))
    hh, mm = map(int, details['birth_time'].split(':'))
    daeun_num = calculate_daeun_number(y, m, d, hh, mm, is_forward)
    
    daeun_list = []
    curr = month_pillar
    for i in range(10):
        curr = get_next_ganzhi(curr) if is_forward else get_prev_ganzhi(curr)
        daeun_list.append({
            'age': daeun_num + (i * 10),
            'ganzhi': curr,
            'stem_ten_god': GAN_TEN_GODS[day_gan].get(curr[0], '-'),
            'branch_ten_god': GAN_TEN_GODS[day_gan].get(BRANCH_HIDDEN_GANS.get(curr[1]), '-'),
            'twelve_growth': TWELVE_GROWTH[day_gan].get(curr[1], '-')
        })
    return {'num': daeun_num, 'list': daeun_list}

def get_seyun_data(day_gan, year):
    """세운 정보"""
    try:
        from sajupy import get_saju_calculator
        calc = get_saju_calculator()
        res = calc.calculate_saju(year, 2, 15, 12, 0)
        p = res['year_pillar']
        return {
            'year': year, 'ganzhi': p,
            'stem_ten_god': GAN_TEN_GODS[day_gan].get(p[0], '-'),
            'branch_ten_god': GAN_TEN_GODS[day_gan].get(BRANCH_HIDDEN_GANS.get(p[1]), '-'),
            'twelve_growth': TWELVE_GROWTH[day_gan].get(p[1], '-')
        }
    except: return {}

def get_wolun_data(day_gan, year_pillar, target_month):
    """특정 월의 월운 정보 산출 (연간 기준)"""
    year_stem = year_pillar[0]
    start_stem_map = {'甲': 2, '己': 2, '乙': 4, '庚': 4, '丙': 6, '辛': 6, '丁': 8, '壬': 8, '戊': 0, '癸': 0}
    start_stem_idx = start_stem_map.get(year_stem, 0)
    
    # 1월=寅, 2월=卯... (입춘 기준 간이 계산)
    month_branch_idx = (target_month + 1) % 12 
    month_stem_idx = (start_stem_idx + target_month - 1) % 10
    
    stem = HEAVENLY_STEMS[month_stem_idx]
    branch = EARTHLY_BRANCHES[month_branch_idx]
    pillar = stem + branch
    
    return {
        'month': target_month,
        'ganzhi': pillar,
        'stem': stem,
        'branch': branch,
        'stem_ten_god': GAN_TEN_GODS[day_gan].get(stem, '-'),
        'branch_ten_god': GAN_TEN_GODS[day_gan].get(BRANCH_HIDDEN_GANS.get(branch), '-'),
        'twelve_growth': TWELVE_GROWTH[day_gan].get(branch, '-')
    }

def get_extended_saju_data(details, gender='여'):
    """모든 확장 데이터(십성, 12운성, 오행, 대운, 신살 등) 통합"""
    pillars = details['pillars']
    day_gan = pillars['day']['stem']
    year_branch = pillars['year']['branch']
    
    # 십성, 12운성, 오행
    details['ten_gods'] = {p: GAN_TEN_GODS[day_gan].get(pillars[p]['stem'], '-') for p in ['year', 'month', 'hour']}
    details['ten_gods']['day'] = '본인'
    details['jiji_ten_gods'] = {p: GAN_TEN_GODS[day_gan].get(BRANCH_HIDDEN_GANS.get(pillars[p]['branch']), '-') for p in ['year', 'month', 'day', 'hour']}
    details['twelve_growth'] = {p: TWELVE_GROWTH[day_gan].get(pillars[p]['branch'], '-') for p in ['year', 'month', 'day', 'hour']}
    
    elems = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    for p in ['year', 'month', 'day', 'hour']:
        for k in [pillars[p]['stem'], pillars[p]['branch']]:
            e = ELEMENTS_MAP.get(k)
            if e: elems[e] += 1
    details['five_elements'] = elems
    
    # 신살 및 형충회합
    ref_idx = EARTHLY_BRANCHES.index(year_branch)
    order = ['지살', '년살', '월살', '망신살', '장성살', '반안살', '역마살', '육해살', '화개살', '겁살', '재살', '천살']
    details['sinsal'] = {p: order[(EARTHLY_BRANCHES.index(pillars[p]['branch']) - ref_idx + 12) % 12] for p in ['year', 'month', 'day', 'hour']}
    
    rels = []
    # 천간 관계 확인
    stems = [pillars[p]['stem'] for p in ['year', 'month', 'day', 'hour']]
    p_names = {'year':'년', 'month':'월', 'day':'일', 'hour':'시'}
    p_keys = ['year', 'month', 'day', 'hour']
    for i in range(4):
        for j in range(i+1, 4):
            s1, s2 = stems[i], stems[j]
            if STEM_RELATIONS['충'].get(s1) == s2: rels.append(f"천간 {p_names[p_keys[i]]}-{p_names[p_keys[j]]} 충({s1}-{s2})")
            if STEM_RELATIONS['합'].get(s1) == s2: rels.append(f"천간 {p_names[p_keys[i]]}-{p_names[p_keys[j]]} 합({s1}-{s2})")

    brs = [pillars[p]['branch'] for p in ['year', 'month', 'day', 'hour']]
    for i in range(4):
        for j in range(i+1, 4):
            b1, b2 = brs[i], brs[j]
            if BRANCH_RELATIONS['충'].get(b1) == b2: rels.append(f"지지 {p_names[p_keys[i]]}-{p_names[p_keys[j]]} 충({b1}-{b2})")
            if BRANCH_RELATIONS['합'].get(b1) == b2: rels.append(f"지지 {p_names[p_keys[i]]}-{p_names[p_keys[j]]} 합({b1}-{b2})")
    details['relations'] = rels
    
    # 대운
    details['fortune'] = calculate_daeun(details, gender)
    
    return details
