import streamlit as st
import feedparser
import google.generativeai as genai
import time
from datetime import datetime
import os

# 1. 페이지 설정 (가장 위에 있어야 함)
st.set_page_config(
    page_title="AI News Curator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. 스타일 설정 (다크모드 & 카드 스타일)
st.markdown("""
<style>
    .stApp {
        background-color: #0f172a;
        color: #e2e8f0;
    }
    .news-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #334155;
    }
    .source-tag {
        font-size: 0.8em;
        padding: 4px 8px;
        border-radius: 15px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    .highlight {
        color: #38bdf8;
        font-weight: bold;
    }
    a {
        text-decoration: none;
        color: #38bdf8;
    }
</style>
""", unsafe_allow_html=True)

# 3. API 키 설정 (Streamlit Secrets에서 가져오기)
# 로컬 테스트용: 만약 secrets가 없으면 환경변수나 직접 입력 (주의: 배포시엔 secrets 사용 권장)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    # 임시: 로컬에서 테스트할 때만 아래에 키를 직접 넣으세요. 배포할 땐 지워야 합니다.
    api_key = os.getenv("GOOGLE_API_KEY", "") 

if not api_key:
    st.error("API 키가 설정되지 않았습니다. Streamlit Secrets에 GOOGLE_API_KEY를 설정해주세요.")
    st.stop()

genai.configure(api_key=api_key)

# 4. 뉴스 소스 설정
FEEDS = [
    {'id': 'techcrunch', 'name': 'TechCrunch AI', 'url': 'https://techcrunch.com/category/artificial-intelligence/feed/', 'color': '#16a34a'},
    {'id': 'openai', 'name': 'OpenAI Blog', 'url': 'https://openai.com/index.xml', 'color': '#ffffff'}, # 글자색 가독성을 위해 흰색으로 조정
    {'id': 'deepmind', 'name': 'Google DeepMind', 'url': 'https://deepmind.google/rss/blog', 'color': '#4285F4'},
]

# 5. Gemini 번역 함수
def analyze_news(title, content):
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    당신은 전문 AI 뉴스 큐레이터입니다. 아래 영문 뉴스 제목과 내용을 한국어로 번역하고 요약해주세요.
    
    [원문 제목]: {title}
    [원문 내용 일부]: {content[:500]}...

    [출력 형식]:
    제목: (한국어 제목)
    요약: (핵심 내용 3줄 요약)
    한줄평: (이 뉴스의 업계 영향력 한 줄)
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"분석 실패: {str(e)}"

# 6. 세션 상태 초기화 (새로고침 해도 데이터 유지)
if 'news_items' not in st.session_state:
    st.session_state.news_items = []
if 'last_updated' not in st.session_state:
    st.session_state.last_updated = None

# 7. 메인 로직
def main():
    st.title("🤖 Global AI News Curator")
    st.caption("TechCrunch, OpenAI, DeepMind의 최신 뉴스를 실시간으로 번역/요약합니다.")

    # 사이드바에 새로고침 버튼
    with st.sidebar:
        st.header("설정")
        if st.button("뉴스 새로고침"):
            st.session_state.news_items = [] # 초기화 후 다시 로드
            st.rerun()

    # 뉴스 데이터 로드 (캐시되지 않았거나 비어있을 때)
    if not st.session_state.news_items:
        all_items = []
        with st.spinner('최신 AI 뉴스를 수집하고 있습니다...'):
            for feed in FEEDS:
                try:
                    parsed_feed = feedparser.parse(feed['url'])
                    # 각 피드에서 최신 3개만 가져오기 (속도 위해)
                    for entry in parsed_feed.entries[:3]:
                        item = {
                            'source_id': feed['id'],
                            'source_name': feed['name'],
                            'color': feed['color'],
                            'title': entry.title,
                            'link': entry.link,
                            'published': entry.get('published', 'N/A'),
                            'summary_raw': entry.get('summary', '') or entry.get('description', ''),
                            'analysis': None # 아직 번역 안됨
                        }
                        all_items.append(item)
                except Exception as e:
                    st.error(f"{feed['name']} 로드 실패: {e}")
            
            # 최신순 정렬
            # (날짜 파싱이 복잡할 수 있어 단순 구현. 필요시 파싱 로직 추가 가능)
            st.session_state.news_items = all_items
            st.session_state.last_updated = datetime.now()

    # 마지막 업데이트 시간 표시
    if st.session_state.last_updated:
        st.write(f"Last updated: {st.session_state.last_updated.strftime('%H:%M:%S')}")

    # 뉴스 카드 출력
    news_container = st.container()
    
    with news_container:
        # 3열 그리드 생성
        cols = st.columns(3)
        
        for idx, item in enumerate(st.session_state.news_items):
            col = cols[idx % 3] # 0,1,2 열에 번갈아 배치
            
            with col:
                # 카드 HTML/CSS 구조
                st.markdown(f"""
                <div class="news-card">
                    <div style="color:{item['color']}; font-weight:bold; margin-bottom:5px;">
                        • {item['source_name']}
                    </div>
                    <h3 style="color:white; font-size:1.1em; height: 60px; overflow:hidden;">{item['title']}</h3>
                    <div style="font-size:0.8em; color:#94a3b8; margin-bottom:10px;">{item['published'][:16]}</div>
                </div>
                """, unsafe_allow_html=True)

                # 번역/요약 버튼 (개별 실행으로 API 비용 절약)
                btn_key = f"btn_{idx}"
                if st.button(f"🇰🇷 번역 및 요약 보기", key=btn_key):
                    if not item['analysis']:
                        with st.spinner('Gemini가 읽고 있습니다...'):
                            analysis = analyze_news(item['title'], item['summary_raw'])
                            st.session_state.news_items[idx]['analysis'] = analysis
                            st.rerun() # 화면 갱신
                
                # 번역 결과 표시
                if item['analysis']:
                    st.info(item['analysis'])
                
                st.markdown(f"[원문 보러가기 →]({item['link']})")
                st.markdown("---")

if __name__ == "__main__":
    main()
