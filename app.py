#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持股追蹤 Streamlit 應用程式
資料來源：台灣證券交易所 (TWSE) 官方 API
支援多個 AI 供應商：Gemini、Groq、OpenRouter、Anthropic
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
APP_PASSWORD = "740704"

# ==================== AI 供應商設定 ====================
AI_PROVIDERS = {
    "Google Gemini": {
        "id": "gemini",
        "secret": "GEMINI_API_KEY",
        "models": [
            {"value": "gemini-3.5-flash", "label": "Gemini 3.5 Flash (推薦)"},
            {"value": "gemini-2.5-flash", "label": "Gemini 2.5 Flash"},
            {"value": "gemini-2.5-pro", "label": "Gemini 2.5 Pro"},
        ]
    },
    "Groq": {
        "id": "groq",
        "secret": "GROQ_API_KEY",
        "models": [
            {"value": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B (推薦)"},
            {"value": "llama-3.1-8b-instant", "label": "Llama 3.1 8B (快速)"},
            {"value": "mixtral-8x7b-32768", "label": "Mixtral 8x7B"},
        ]
    },
    "OpenRouter": {
        "id": "openrouter",
        "secret": "OPENROUTER_API_KEY",
        "models": [
            {"value": "deepseek/deepseek-v4-flash", "label": "DeepSeek V4 Flash (推薦)"},
            {"value": "openai/gpt-oss-120b:free", "label": "GPT OSS 120B (免費)"},
            {"value": "moonshotai/kimi-k2.6:free", "label": "Kimi K2.6 (免費)"},
        ]
    },
    "Anthropic": {
        "id": "anthropic",
        "secret": "ANTHROPIC_API_KEY",
        "models": [
            {"value": "claude-sonnet-4-20250514", "label": "Claude Sonnet 4 (推薦)"},
            {"value": "claude-3-5-haiku-20241022", "label": "Claude 3.5 Haiku (快速)"},
        ]
    }
}

# ==================== 結構化 AI 行為規範 ====================
AI_SYSTEM_PROMPT = """你是一位專業的投資理財顧問，專精台灣股市分析。

## 行為規範
1. 使用繁體中文（台灣）回答
2. 回答要專業但易懂，避免過多術語
3. 根據用戶的持股資料提供具體分析
4. 如有搜尋到最新新聞，請結合新聞分析
5. 未完成分析時，不要問「下一步」，直接做到底
6. 回答聚焦：是否完成、具體建議、風險提醒
7. 請注意：你的回答僅供參考，不構成投資建議

## 分析重點
- 基本面：公司獲利、營收成長、產業地位
- 技術面：股價趨勢、支撐壓力
- 消息面：最新新聞、產業動態
- 風險評估：投資風險、建議策略"""

def get_available_providers():
    """取得可用的 AI 供應商"""
    available = []
    for name, config in AI_PROVIDERS.items():
        try:
            key = st.secrets[config["secret"]]
            if key:
                available.append(name)
        except:
            pass
    return available

def get_provider_key(provider_name):
    """取得供應商的 API Key"""
    config = AI_PROVIDERS.get(provider_name)
    if config:
        try:
            return st.secrets[config["secret"]]
        except:
            return None
    return None

def ask_ai_with_gemini(question, portfolio_context, api_key, model="gemini-3.5-flash", news_context=""):
    """使用 Google Gemini 回答"""
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

{news_context}

用戶的問題：{question}

請根據以上資料回答用戶的問題。"""
    
    try:
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model=model,
            contents=f"{AI_SYSTEM_PROMPT}\n\n{user_prompt}"
        )
        return response.text
    except Exception as e:
        return None

def ask_ai_with_groq(question, portfolio_context, api_key, model="llama-3.3-70b-versatile", news_context=""):
    """使用 Groq 回答"""
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

{news_context}

用戶的問題：{question}

請根據以上資料回答用戶的問題。"""
    
    try:
        from groq import Groq
        
        client = Groq(api_key=api_key)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return None

def ask_ai_with_openrouter(question, portfolio_context, api_key, model="deepseek/deepseek-v4-flash", news_context=""):
    """使用 OpenRouter 回答"""
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

{news_context}

用戶的問題：{question}

請根據以上資料回答用戶的問題。"""
    
    try:
        import openai
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return None

def ask_ai_with_anthropic(question, portfolio_context, api_key, model="claude-sonnet-4-20250514", news_context=""):
    """使用 Anthropic Claude 回答"""
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

{news_context}

用戶的問題：{question}

請根據以上資料回答用戶的問題。"""
    
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system=AI_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.content[0].text
    except Exception as e:
        return None

def ask_ai(question, portfolio_context, provider_name, model_name, news_context=""):
    """使用選定的 AI 供應商回答"""
    api_key = get_provider_key(provider_name)
    
    if not api_key:
        return f"⚠️ {provider_name} API Key 未設定"
    
    # 根據供應商選擇對應的函數
    if provider_name == "Google Gemini":
        result = ask_ai_with_gemini(question, portfolio_context, api_key, model_name, news_context)
    elif provider_name == "Groq":
        result = ask_ai_with_groq(question, portfolio_context, api_key, model_name, news_context)
    elif provider_name == "OpenRouter":
        result = ask_ai_with_openrouter(question, portfolio_context, api_key, model_name, news_context)
    elif provider_name == "Anthropic":
        result = ask_ai_with_anthropic(question, portfolio_context, api_key, model_name, news_context)
    else:
        result = None
    
    if result:
        return result
    
    return f"⚠️ {provider_name} 請求失敗，請稍後再試"

# ==================== 網路搜尋功能 ====================
def search_stock_news(query, max_results=5):
    """使用 SerpAPI 搜尋股票相關新聞"""
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
            "tbm": "nws",
            "num": max_results
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        news_results = results.get("news_results", [])
        return news_results[:max_results]
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
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
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

@st.cache_data(ttl=300)
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

def main():
    # 密碼驗證
    if not check_password():
        return
    
    # 側邊欄
    with st.sidebar:
        st.markdown("### ⚙️ 設定")
        if st.button("🚪 登出", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
        st.markdown("---")
        
        # AI 供應商選擇
        st.markdown("### 🤖 AI 設定")
        available_providers = get_available_providers()
        
        if available_providers:
            selected_provider = st.selectbox(
                "選擇 AI 供應商",
                available_providers,
                index=0
            )
            
            # 取得該供應商的模型列表
            provider_config = AI_PROVIDERS[selected_provider]
            model_options = [m["label"] for m in provider_config["models"]]
            selected_model_label = st.selectbox(
                "選擇模型",
                model_options,
                index=0
            )
            # 取得實際模型值
            selected_model = next(m["value"] for m in provider_config["models"] if m["label"] == selected_model_label)
            
            st.session_state.selected_provider = selected_provider
            st.session_state.selected_model = selected_model
            
            st.info(f"✅ 已選擇：{selected_provider} / {selected_model_label}")
        else:
            st.warning("⚠️ 未設定任何 AI API Key")
            st.markdown("""
            請在 Settings → Secrets 中加入：
            ```
            GEMINI_API_KEY = "你的Key"
            GROQ_API_KEY = "你的Key"
            OPENROUTER_API_KEY = "你的Key"
            ANTHROPIC_API_KEY = "你的Key"
            ```
            """)
        
        st.markdown("---")
        st.caption("資料來源：TWSE")
    
    # 標題
    st.title("📊 持股追蹤資訊")
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
    
    # 顯示持股表格
    st.subheader("📋 目前持股")
    
    df = pd.DataFrame(portfolio_data)
    df = df.rename(columns={
        'code': '股票代號',
        'name': '股票名稱',
        'shares': '持有股數',
        'cost': '成本',
        'cost_per_share': '每股成本',
        'currentPrice': '目前價格',
        'marketValue': '市值',
        'unrealizedPnl': '未實現損益',
        'unrealizedPnlPct': '損益%',
        'tradeDate': '交易日'
    })
    
    st.dataframe(
        df[['股票代號', '股票名稱', '持有股數', '成本', '目前價格', '市值', '未實現損益', '損益%', '交易日']],
        use_container_width=True,
        hide_index=True
    )
    
    # 總計
    total_cost = sum(s['cost'] for s in portfolio_data)
    total_market = sum(s['marketValue'] for s in portfolio_data)
    total_pnl = total_market - total_cost
    total_pnl_pct = (total_pnl / total_cost) * 100
    
    st.divider()
    
    # 關鍵指標
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總成本", f"NT${total_cost:,.0f}")
    with col2:
        st.metric("總市值", f"NT${total_market:,.0f}")
    with col3:
        st.metric("未實現損益", f"NT${total_pnl:+,.0f}", f"{total_pnl_pct:+.2f}%")
    with col4:
        st.metric("已實現損益", f"NT${REALIZED_PNL:+,.0f}")
    
    st.divider()
    
    # ==================== AI 投資助手 ====================
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
                    search_keywords = prompt
                    for stock in portfolio_data:
                        if stock["code"] in prompt or stock["name"] in prompt:
                            search_keywords = f"{stock['code']} {stock['name']} 股票 新聞"
                            break
                    if search_keywords == prompt:
                        search_keywords = f"台股 {prompt}"
                    
                    with st.spinner("🔍 搜尋最新新聞..."):
                        news_results = search_stock_news(search_keywords, max_results=3)
                        news_context = format_news_for_ai(news_results)
                        
                        if news_results:
                            st.info(f"📰 找到 {len(news_results)} 則相關資訊")
                            with st.expander("📋 查看搜尋到的新聞內容", expanded=False):
                                for i, news in enumerate(news_results, 1):
                                    title = news.get('title', '無標題')
                                    snippet = news.get('snippet', '無摘要')[:200]
                                    st.write(f"**{i}. {title}**")
                                    st.write(f"   {snippet}...")
                                    st.write("")
                        else:
                            st.warning("⚠️ 無法取得最新新聞，將使用歷史資料分析")
                
                # 使用選定的 AI 供應商
                provider_name = st.session_state.get("selected_provider", "Google Gemini")
                model_name = st.session_state.get("selected_model", "gemini-3.5-flash")
                
                response = ask_ai(prompt, portfolio_context, provider_name, model_name, news_context)
                
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == '__main__':
    main()
