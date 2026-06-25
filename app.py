#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持股追蹤 Streamlit 應用程式
資料來源：台灣證券交易所 (TWSE) 官方 API
"""

import streamlit as st
import json
import urllib.request
import urllib.error
from datetime import datetime
import pandas as pd

# 頁面設定
st.set_page_config(
    page_title="持股追蹤資訊",
    page_icon="📊",
    layout="wide"
)

# ==================== 密碼保護設定 ====================
# 請修改為您想要的密碼
APP_PASSWORD = "740704"
# =====================================================

# ==================== AI 功能設定 ====================
# AI API 設定 (需在 Streamlit Cloud 設定 secrets)
def get_ai_config():
    """取得 AI API 設定"""
    gemini_key = None
    groq_key = None
    
    try:
        gemini_key = st.secrets["GEMINI_API_KEY"]
    except:
        pass
    
    try:
        groq_key = st.secrets["GROQ_API_KEY"]
    except:
        pass
    
    return gemini_key, groq_key

def ask_ai_with_gemini(question, portfolio_context, api_key):
    """使用 Google Gemini 3.5 Flash 回答"""
    system_prompt = """你是一位專業的投資理財顧問，專精台灣股市分析。
請根據用戶的持股資料，提供專業的投資建議和分析。
回答時請使用繁體中文，並保持客觀、專業的態度。
請注意：你的回答僅供參考，不構成投資建議。"""
    
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

用戶的問題：{question}

請根據以上資料回答用戶的問題。"""
    
    try:
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=f"{system_prompt}\n\n{user_prompt}"
        )
        return response.text
    except ImportError:
        return "⚠️ 需要安裝 google-genai 套件。"
    except Exception as e:
        return None  # 回傳 None 讓呼叫端嘗試下一個 API

def ask_ai_with_groq(question, portfolio_context, api_key):
    """使用 Groq (Llama 3) 回答"""
    system_prompt = """你是一位專業的投資理財顧問，專精台灣股市分析。
請根據用戶的持股資料，提供專業的投資建議和分析。
回答時請使用繁體中文，並保持客觀、專業的態度。
請注意：你的回答僅供參考，不構成投資建議。"""
    
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

用戶的問題：{question}

請根據以上資料回答用戶的問題。"""
    
    try:
        from groq import Groq
        
        client = Groq(api_key=api_key)
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except ImportError:
        return "⚠️ 需要安裝 groq 套件。"
    except Exception as e:
        return None  # 回傳 None 讓呼叫端嘗試下一個 API

def ask_ai(question, portfolio_context):
    """使用 AI 回答投資相關問題 (支援多個 API 嘗試)"""
    gemini_key, groq_key = get_ai_config()
    
    # 1. 嘗試使用 Gemini 3.5 Flash (首要)
    if gemini_key:
        result = ask_ai_with_gemini(question, portfolio_context, gemini_key)
        if result and not result.startswith("⚠️"):
            return result
    
    # 2. 嘗試使用 Groq (備援)
    if groq_key:
        result = ask_ai_with_groq(question, portfolio_context, groq_key)
        if result and not result.startswith("⚠️"):
            return result
    
    # 3. 都無法使用時，顯示設定說明
    return """⚠️ AI 功能尚未設定或已达使用上限。

請在 Streamlit Cloud 的 Secrets 中設定以下任一 API Key：

**1. Google Gemini 3.5 Flash (推薦，免費額度有限)**
- 取得：https://aistudio.google.com/apikey
- 加入：`GEMINI_API_KEY = "您的Key"`

**2. Groq (備援，速度快)**
- 取得：https://console.groq.com/keys
- 加入：`GROQ_API_KEY = "您的Key"`"""

# ==================== 網路搜尋功能 ====================
def search_stock_news(query, max_results=5):
    """使用 SerpAPI 搜尋股票相關新聞"""
    try:
        from serpapi import GoogleSearch
        
        # 取得 SerpAPI Key
        serpapi_key = None
        try:
            serpapi_key = st.secrets["SERPAPI_API_KEY"]
        except:
            pass
        
        if not serpapi_key:
            return []
        
        params = {
            "api_key": serpapi_key,
            "engine": "google",
            "q": query,
            "gl": "tw",
            "hl": "zh-tw",
            "tbm": "nws",  # 新聞搜尋
            "num": max_results
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        news_results = results.get("news_results", [])
        return news_results[:max_results]
    except Exception as e:
        return []

def search_web(query, max_results=5):
    """使用 SerpAPI 搜尋網路資訊"""
    try:
        from serpapi import GoogleSearch
        
        serpapi_key = None
        try:
            serpapi_key = st.secrets["SERPAPI_API_KEY"]
        except:
            pass
        
        if not serpapi_key:
            return []
        
        params = {
            "api_key": serpapi_key,
            "engine": "google",
            "q": query,
            "gl": "tw",
            "hl": "zh-tw",
            "num": max_results
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        organic_results = results.get("organic_results", [])
        return organic_results[:max_results]
    except Exception as e:
        return []

def format_news_for_ai(news_list):
    """將新聞格式化為 AI 可讀的格式"""
    if not news_list:
        return "無法取得最新新聞。"
    
    lines = ["以下是搜尋到的相關資訊：\n"]
    for i, news in enumerate(news_list, 1):
        title = news.get('title', '無標題')
        snippet = news.get('snippet', '無摘要')
        link = news.get('link', '')
        source = news.get('source', '')
        date = news.get('date', '')
        lines.append(f"{i}. **{title}**")
        lines.append(f"   來源：{source} | 時間：{date}")
        lines.append(f"   摘要：{snippet}")
        lines.append(f"   連結：{link}\n")
    
    return "\n".join(lines)

def ask_ai_with_news(question, portfolio_context, api_key, news_context=""):
    """使用 AI 回答投資問題（包含最新新聞）"""
    system_prompt = """你是一位專業的投資理財顧問，專精台灣股市分析。
請根據用戶的持股資料和最新新聞，提供專業的投資建議和分析。
回答時請使用繁體中文，並保持客觀、專業的態度。
請注意：你的回答僅供參考，不構成投資建議。"""
    
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

{news_context}

用戶的問題：{question}

請根據以上資料（包含最新新聞）回答用戶的問題。"""
    
    try:
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=f"{system_prompt}\n\n{user_prompt}"
        )
        return response.text
    except Exception as e:
        return None

def ask_ai_with_groq_news(question, portfolio_context, api_key, news_context=""):
    """使用 Groq 回答投資問題（包含最新新聞）"""
    system_prompt = """你是一位專業的投資理財顧問，專精台灣股市分析。
請根據用戶的持股資料和最新新聞，提供專業的投資建議和分析。
回答時請使用繁體中文，並保持客觀、專業的態度。
請注意：你的回答僅供參考，不構成投資建議。"""
    
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

{news_context}

用戶的問題：{question}

請根據以上資料（包含最新新聞）回答用戶的問題。"""
    
    try:
        from groq import Groq
        
        client = Groq(api_key=api_key)
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return None

def format_portfolio_for_ai(portfolio_data):
    """將持股資料格式化為 AI 可讀的格式"""
    lines = []
    for stock in portfolio_data:
        lines.append(f"- {stock['code']} {stock['name']}：持有 {stock['shares']:,} 股，成本 {stock['cost']:,} 元，目前價格 {stock['currentPrice']:.2f} 元，損益 {stock['unrealizedPnl']:+,.0f} 元 ({stock['unrealizedPnlPct']:+.2f}%)")
    
    total_cost = sum(s['cost'] for s in portfolio_data)
    total_market = sum(s['marketValue'] for s in portfolio_data)
    total_pnl = total_market - total_cost
    
    lines.append(f"\n總計：成本 {total_cost:,} 元，市值 {total_market:,.0f} 元，未實現損益 {total_pnl:+,.0f} 元 ({total_pnl/total_cost*100:+.2f}%)")
    
    return "\n".join(lines)

# 持股資料
PORTFOLIO = [
    {'code': '2801', 'name': '彰銀', 'shares': 2000, 'cost': 41950, 'prevClose': 23.20},
    {'code': '5880', 'name': '合庫金', 'shares': 2000, 'cost': 45800, 'prevClose': 24.55},
    {'code': '3231', 'name': '緯創', 'shares': 100, 'cost': 15900, 'prevClose': 158.50},
    {'code': '009816', 'name': '凱基台灣TOP50', 'shares': 4000, 'cost': 53690, 'prevClose': 15.97},
]

REALIZED_PNL = 1698

def check_password():
    """密碼驗證函數"""
    # 初始化 session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    # 如果已驗證，直接返回
    if st.session_state.authenticated:
        return True
    
    # 顯示登入頁面
    st.markdown("""
    <style>
    .main {display: flex; justify-content: center; align-items: center; min-height: 60vh;}
    .stLogin {text-align: center;}
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🔒 持股追蹤資訊")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 請輸入密碼")
        password = st.text_input("密碼", type="password", placeholder="請輸入密碼", label_visibility="collapsed")
        
        if st.button("登入", use_container_width=True, type="primary"):
            if password == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("密碼錯誤，請重新輸入")
                return False
    
    return False

@st.cache_data(ttl=300)  # 快取5分鐘
def fetch_twse_data(stock_code):
    """從 TWSE API 抓取個股成交資訊"""
    now = datetime.now()
    roc_year = now.year - 1911
    date_str = f"{roc_year}{now.strftime('%m')}"
    
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_code}"
    
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        st.error(f"抓取 {stock_code} 失敗: {e}")
        return None

def get_latest_close_price(data):
    """從 TWSE 回傳資料中取得最新收盤價"""
    if data and data.get('stat') == 'OK' and data.get('data'):
        latest = data['data'][-1]
        close_price = float(latest[6].replace(',', ''))
        trade_date = latest[0]
        return close_price, trade_date
    return None, None

def get_stock_info(stock_code):
    """取得個股基本資訊"""
    url = f"https://www.twse.com.tw/zh/api/codeQuery?query={stock_code}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('suggestions'):
                return data['suggestions'][0]
    except:
        pass
    return None

def main():
    # 密碼驗證
    if not check_password():
        return
    
    # 側邊欄 - 登出按鈕
    with st.sidebar:
        st.markdown("### ⚙️ 設定")
        if st.button("🚪 登出", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
        st.markdown("---")
        st.caption("資料來源：TWSE")
    
    # 標題
    st.title("📊 持股追蹤資訊")
    
    # 更新時間
    st.caption(f"資料更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 資料來源：台灣證券交易所 (TWSE)")
    
    # 手動更新按鈕
    if st.button("🔄 立即更新資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    # 載入資料
    portfolio_data = []
    
    with st.spinner("正在從 TWSE 抓取最新資料..."):
        for stock in PORTFOLIO:
            data = fetch_twse_data(stock['code'])
            close_price, trade_date = get_latest_close_price(data)
            
            if close_price is not None:
                current_price = close_price
            else:
                current_price = stock['prevClose']
                trade_date = '--'
            
            market_value = stock['shares'] * current_price
            unrealized_pnl = market_value - stock['cost']
            unrealized_pnl_pct = (unrealized_pnl / stock['cost']) * 100
            
            portfolio_data.append({
                'code': stock['code'],
                'name': stock['name'],
                'shares': stock['shares'],
                'cost': stock['cost'],
                'cost_per_share': stock['cost'] / stock['shares'],
                'prevClose': stock['prevClose'],
                'currentPrice': current_price,
                'marketValue': market_value,
                'unrealizedPnl': unrealized_pnl,
                'unrealizedPnlPct': unrealized_pnl_pct,
                'tradeDate': trade_date
            })
    
    # 計算總計
    total_cost = sum(s['cost'] for s in portfolio_data)
    total_market_value = sum(s['marketValue'] for s in portfolio_data)
    total_unrealized_pnl = total_market_value - total_cost
    total_pnl = total_unrealized_pnl + REALIZED_PNL
    total_return = (total_pnl / total_cost) * 100
    
    # 摘要卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("持股成本", f"NT${total_cost:,.0f}")
    with col2:
        st.metric("目前市值", f"NT${total_market_value:,.0f}")
    with col3:
        st.metric("未實現損益", 
                   f"NT${total_unrealized_pnl:+,.0f}",
                   f"{total_unrealized_pnl/total_cost*100:+.2f}%")
    with col4:
        st.metric("整體報酬率", 
                   f"{total_return:+.2f}%",
                   delta=f"NT${total_pnl:+,.0f}")
    
    st.divider()
    
    # 持股明細表格
    st.subheader("📋 持股明細")
    
    df = pd.DataFrame(portfolio_data)
    
    # 格式化顯示
    display_df = pd.DataFrame({
        '標的': df.apply(lambda x: f"**{x['code']}** {x['name']}", axis=1),
        '持股': df['shares'].apply(lambda x: f"{x:,} 股"),
        '成本': df['cost'].apply(lambda x: f"{x:,.0f}"),
        '均價': df['cost_per_share'].apply(lambda x: f"{x:,.1f}"),
        '前日收盤': df['prevClose'].apply(lambda x: f"{x:,.2f}"),
        '最新收盤': df['currentPrice'].apply(lambda x: f"{x:,.2f}"),
        '損益金額': df['unrealizedPnl'].apply(lambda x: f"{x:+,.0f}"),
        '損益%': df['unrealizedPnlPct'].apply(lambda x: f"{x:+.2f}%"),
    })
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # 個股詳細資訊
    st.divider()
    st.subheader("📈 個股走勢")
    
    tabs = st.tabs([f"{s['code']} {s['name']}" for s in portfolio_data])
    
    for tab, stock in zip(tabs, portfolio_data):
        with tab:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                price_change = stock['currentPrice'] - stock['prevClose']
                price_change_pct = (price_change / stock['prevClose']) * 100
                st.metric("今日漲跌", 
                          f"{stock['currentPrice']:.2f}",
                          f"{price_change:+.2f} ({price_change_pct:+.2f}%)")
            
            with col2:
                st.metric("持股數量", f"{stock['shares']:,} 股")
            
            with col3:
                st.metric("損益", 
                          f"NT${stock['unrealizedPnl']:+,.0f}",
                          f"{stock['unrealizedPnlPct']:+.2f}%")
    
    # 免責聲明
    st.divider()
    st.caption("⚠️ 免責聲明：本資訊僅供參考，不構成任何投資建議。投資有風險，請自行判斷。")
    
    # ==================== AI 投資助手 ====================
    st.divider()
    st.subheader("🤖 AI 投資助手")
    st.caption("有任何投資問題，可以直接在下方提問，AI 會根據您的持股資料進行分析")
    
    # 新聞搜尋選項
    use_news_search = st.checkbox("📰 搜尋最新新聞輔助分析", value=True, 
                                  help="開啟後 AI 會自動搜尋相關新聞來提供更即時的分析")
    
    # 初始化聊天記錄
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # 顯示歷史訊息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 使用者輸入
    if prompt := st.chat_input("請輸入您的投資問題..."):
        # 顯示使用者訊息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 生成 AI 回答
        with st.chat_message("assistant"):
            with st.spinner("AI 正在分析中..."):
                portfolio_context = format_portfolio_for_ai(portfolio_data)
                
                # 根據用戶問題搜尋相關新聞
                news_context = ""
                if use_news_search:
                    # 根據問題和持股建立搜尋關鍵字
                    search_keywords = prompt
                    # 如果問題中提到特定股票，加入該股票名稱
                    for stock in portfolio_data:
                        if stock["code"] in prompt or stock["name"] in prompt:
                            search_keywords = f"{stock['code']} {stock['name']} 股票 新聞"
                            break
                    # 如果沒有特定股票，加上「台股」關鍵字
                    if search_keywords == prompt:
                        search_keywords = f"台股 {prompt}"
                    
                    with st.spinner("🔍 搜尋最新新聞..."):
                        news_results = search_stock_news(search_keywords, max_results=3)
                        news_context = format_news_for_ai(news_results)
                        
                        # 顯示搜尋到的新聞來源
                        if news_results:
                            st.info(f"📰 找到 {len(news_results)} 則相關資訊")
                            # 顯示新聞摘要供用戶查看
                            with st.expander("📋 查看搜尋到的新聞內容", expanded=False):
                                for i, news in enumerate(news_results, 1):
                                    title = news.get('title', '無標題')
                                    body = news.get('body', '無摘要')[:200]  # 限制長度
                                    st.write(f"**{i}. {title}**")
                                    st.write(f"   {body}...")
                                    st.write("")
                        else:
                            st.warning("⚠️ 無法取得最新新聞，將使用歷史資料分析")
                
                # 嘗試使用 AI 回答（包含新聞）
                gemini_key, groq_key = get_ai_config()
                
                response = None
                # 1. 嘗試 Gemini (首要)
                if gemini_key:
                    response = ask_ai_with_news(prompt, portfolio_context, gemini_key, news_context)
                
                # 2. 嘗試 Groq (備援)
                if not response and groq_key:
                    response = ask_ai_with_groq_news(prompt, portfolio_context, groq_key, news_context)
                
                # 3. 都失敗則顯示設定說明
                if not response:
                    response = """⚠️ AI 功能尚未設定或已达使用上限。

請在 Streamlit Cloud 的 Secrets 中設定以下 API Keys：

**1. Google Gemini 3.5 Flash (AI 主要)**
- 取得：https://aistudio.google.com/apikey
- 加入：`GEMINI_API_KEY = "您的Key"`

**2. Groq (AI 備援)**
- 取得：https://console.groq.com/keys
- 加入：`GROQ_API_KEY = "您的Key"`

**3. SerpAPI (新聞搜尋)**
- 取得：https://serpapi.com/users/sign_up (免費 250 次/月)
- 加入：`SERPAPI_API_KEY = "您的Key"`"""
                
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == '__main__':
    main()
