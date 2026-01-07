import streamlit as st
import feedparser
import google.generativeai as genai
from datetime import datetime
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI News Insight", page_icon="⚡", layout="wide")

# 2. CSS 스타일
st.markdown("""
<style>
    .news-card {
        background: #111111;
        border: 1px solid #222222;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 10px;
        height: 100%;
    }
    .analysis-box {
        background: #0a0a0a;
        border-left: 3px solid #3b82f6;
        padding: 15px;
        margin-top: 10px;
        color: #cccccc;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# 3. API 설정
api_key = st.secrets.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("API Key가 설정되지 않았습니다. Secrets를 확인해주세요.")

# 4. 뉴스 수집 함수 (최신순 정렬 강화)
def get_ai_news():
    feeds = [
        {'id': 'TechCrunch', 'url': 'https://techcrunch.com/category/artificial-intelligence/feed/'},
        {'id': 'OpenAI', 'url': 'https://openai.com/index.xml'},
        {'id': 'DeepMind', 'url': 'https://deepmind.google/rss/blog'}
    ]
    
    all_news = []
    for f in feeds:
        try:
            parsed = feedparser.parse(f['url'])
            for entry in parsed.entries[:10]: # 더 많은 기사를 가져온 뒤 정렬
                all_news.append({
                    'source': f['id'],
                    'title': entry.title,
                    'link': entry.link,
                    'date': entry.get('published', entry.get('updated', 'No Date')),
                    'summary': entry.get('summary', entry.get('description', '내용 없음'))
                })
        except Exception as e:
            st.warning(f"{f['id']} 로드 실패")
    
    return all_news

# 5. UI 구성
st.title("⚡ 실시간 AI 뉴스 브리핑")

if 'news_data' not in st.session_state:
    st.session_state.news_data = get_ai_news()

# 뉴스 출력
for item in st.session_state.news_data[:12]: # 최신 12개만 표시
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(item['title'])
            st.caption(f"{item['source']} | {item['date']}")
        with col2:
            # 버튼 클릭 시 해당 뉴스만 분석하도록 로직 단순화
            if st.button("요약하기", key=item['link']):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"다음 AI 뉴스를 한국어로 아주 친절하게 요약해줘.\n제목: {item['title']}\n내용: {item['summary'][:500]}"
                    response = model.generate_content(prompt)
                    st.session_state[f"result_{item['link']}"] = response.text
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")

        # 결과가 세션에 있으면 표시
        if f"result_{item['link']}" in st.session_state:
            st.info(st.session_state[f"result_{item['link']}"])
        
        st.divider()

st.sidebar.button("새 뉴스 가져오기", on_click=lambda: st.session_state.clear())
