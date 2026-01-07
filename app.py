import streamlit as st
import feedparser
import google.generativeai as genai
from datetime import datetime
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI News Insight", page_icon="⚡", layout="wide")

# 2. 고급 CSS 스타일 (AI Studio 느낌 재현)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
        background-color: #050505;
    }
    
    .main { background-color: #050505; }
    
    /* 뉴스 카드 스타일 */
    .news-card {
        background: #111111;
        border: 1px solid #222222;
        border-radius: 12px;
        padding: 24px;
        transition: all 0.3s ease;
        height: 100%;
        margin-bottom: 10px;
    }
    
    .news-card:hover {
        border-color: #3b82f6;
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.4);
    }
    
    .source-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 12px;
        letter-spacing: 0.5px;
    }
    
    .news-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.4;
        margin-bottom: 12px;
    }
    
    .news-date {
        font-size: 0.85rem;
        color: #666666;
        margin-bottom: 15px;
    }
    
    .analysis-box {
        background: #0a0a0a;
        border-left: 3px solid #3b82f6;
        padding: 15px;
        border-radius: 4px;
        margin-top: 15px;
        font-size: 0.95rem;
        color: #cccccc;
        line-height: 1.6;
    }

    /* 버튼 스타일 커스텀 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background-color: #1a1a1a;
        color: white;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# 3. API 설정
api_key = st.secrets.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# 4. 뉴스 수집 및 분석 함수
def get_ai_news():
    feeds = [
        {'id': 'TechCrunch', 'url': 'https://techcrunch.com/category/artificial-intelligence/feed/', 'color': '#00a354'},
        {'id': 'OpenAI', 'url': 'https://openai.com/index.xml', 'color': '#ffffff'},
        {'id': 'DeepMind', 'url': 'https://deepmind.google/rss/blog', 'color': '#4285F4'}
    ]
    
    all_news = []
    for f in feeds:
        parsed = feedparser.parse(f['url'])
        for entry in parsed.entries[:5]: # 각 소스당 5개씩
            all_news.append({
                'source': f['id'],
                'color': f['color'],
                'title': entry.title,
                'link': entry.link,
                'date': entry.get('published', ''),
                'summary': entry.get('summary', '')
            })
    return all_news

def translate_and_summarize(title, text):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash') # 속도가 빠른 flash 모델 사용
        prompt = f"번역 및 요약: 제목 '{title}'과 내용 '{text[:400]}'을 한국어로 번역하고 핵심 3줄 요약해줘."
        response = model.generate_content(prompt)
        return response.text
    except:
        return "분석 중 오류가 발생했습니다."

# 5. UI 구성
st.title("⚡ AI News Insight")
st.markdown("전 세계 AI 트렌드를 실시간으로 모니터링합니다.")

if 'news_data' not in st.session_state:
    st.session_state.news_data = get_ai_news()

# 뉴스 카드 그리드 배치 (3열)
rows = [st.session_state.news_data[i:i+3] for i in range(0, len(st.session_state.news_data), 3)]

for row in rows:
    cols = st.columns(3)
    for i, item in enumerate(row):
        with cols[i]:
            st.markdown(f"""
                <div class="news-card">
                    <span class="source-badge" style="background-color: {item['color']}; color: {'#000' if item['color']=='#ffffff' else '#fff'}">
                        {item['source']}
                    </span>
                    <div class="news-title">{item['title']}</div>
                    <div class="news-date">{item['date'][:16]}</div>
                    <a href="{item['link']}" target="_blank" style="color: #3b82f6; font-size: 0.9rem;">Original Post →</a>
                </div>
            """, unsafe_allow_html=True)
            
            # 번역 버튼
            if st.button("한국어 요약 보기", key=item['link']):
                with st.spinner('Gemini AI 분석 중...'):
                    result = translate_and_summarize(item['title'], item['summary'])
                    st.markdown(f'<div class="analysis-box">{result}</div>', unsafe_allow_html=True)

st.sidebar.button("데이터 새로고침", on_click=lambda: st.session_state.pop('news_data'))
