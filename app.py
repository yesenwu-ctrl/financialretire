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
from datetime import datetime, timedelta
import pandas as pd

# ==================== 產業知識庫 ====================
INDUSTRY_KNOWLEDGE = {
    "金融業": {
        "公股行庫": {
            "特性": ["股價穩定", "配息穩定", "政策敏感", "防禦型標的"],
            "關鍵指標": ["殖利率", "ROE", "放款成長", "逾放比"],
            "風險": ["利差收窄", "政策干預", "呆帳風險"],
            "分析重點": "關注股利穩定性、殖利率、配息率、填息能力",
            "比較對象": "其他公股行庫，但要注意業務差異（純銀行vs金控）"
        },
        "公股金控": {
            "特性": ["業務多元", "獲利成長", "配息穩定", "綜合金融"],
            "關鍵指標": ["EPS", "股利政策", "子公司獲利", "ROE"],
            "風險": ["業務整合", "競爭壓力", "政策風險"],
            "分析重點": "關注各子公司獲利貢獻、整體成長性、股利政策",
            "比較對象": "其他公股金控"
        },
        "民營行庫": {
            "特性": ["市場導向", "獲利成長", "配息穩定", "競爭力強"],
            "關鍵指標": ["EPS", "ROE", "放款成長", "市占率"],
            "風險": ["經濟循環", "信用風險", "競爭壓力"],
            "分析重點": "關注獲利成長性、市占率、資產品質",
            "比較對象": "其他民營行庫"
        }
    },
    "電子業": {
        "電子代工": {
            "特性": ["營收大", "利潤薄", "規模經濟", "科技趨勢"],
            "關鍵指標": ["營收成長", "毛利率", "訂單能見度", "AI伺服器佔比"],
            "風險": ["科技迭代", "客戶集中", "成本壓力"],
            "分析重點": "關注營收趨勢、毛利率變化、新業務成長",
            "比較對象": "電子5哥（廣達、仁寶、英業達、和碩）"
        },
        "IC設計": {
            "特性": ["高毛利", "研發密集", "週期性強"],
            "關鍵指標": ["營收成長", "毛利率", "研發投入"],
            "風險": ["庫存風險", "技術迭代", "客戶集中"],
            "分析重點": "關注營收成長、毛利率、技術領先性",
            "比較對象": "其他IC設計公司"
        }
    },
    "ETF": {
        "大盤型": {
            "特性": ["分散風險", "追蹤大盤", "低管理費"],
            "關鍵指標": ["追蹤誤差", "報酬率", "股利"],
            "風險": ["市場風險", "流動性風險"],
            "分析重點": "關注追蹤效果、配息穩定性、管理費",
            "比較對象": "其他大盤型ETF"
        }
    }
}

# ==================== 個股定義 ====================
STOCK_DEFINITIONS = {
    "2801": {
        "name": "彰銀",
        "type": "dividend",
        "industry": "金融業",
        "sub_industry": "公股行庫",
        "description": "純銀行業務，股價穩定，配息穩定，防禦型標的",
        "competitors": ["第一金", "合庫金", "兆豐金"],
        "analysis_focus": "殖利率、股利穩定性、填息能力",
        "key_metrics": ["殖利率", "EPS", "配息率", "ROE"]
    },
    "5880": {
        "name": "合庫金",
        "type": "dividend",
        "industry": "金融業",
        "sub_industry": "公股金控",
        "description": "金控業務（銀行+保險+證券），業務多元，配息穩定",
        "competitors": ["彰銀", "第一金", "兆豐金"],
        "analysis_focus": "各子公司獲利貢獻、整體成長性、股利政策",
        "key_metrics": ["EPS", "股利政策", "子公司獲利", "ROE"]
    },
    "3231": {
        "name": "緯創",
        "type": "growth",
        "industry": "電子業",
        "sub_industry": "電子代工",
        "description": "電子代工，營收大，利潤薄，受科技趨勢影響",
        "competitors": ["廣達", "仁寶", "英業達", "和碩"],
        "analysis_focus": "營收趨勢、毛利率變化、AI伺服器訂單",
        "key_metrics": ["營收成長", "毛利率", "AI伺服器佔比"]
    },
    "009816": {
        "name": "凱基台灣TOP50",
        "type": "etf",
        "industry": "ETF",
        "sub_industry": "大盤型",
        "description": "追蹤台灣前50大企業，分散風險",
        "competitors": ["0050 元大台灣50", "0051 中100"],
        "analysis_focus": "追蹤效果、配息穩定性、管理費",
        "key_metrics": ["追蹤誤差", "報酬率", "股利"]
    }
}

# ==================== 分析函數 ====================
def get_stock_definition(stock_code):
    """取得個股定義"""
    return STOCK_DEFINITIONS.get(stock_code, None)

def get_stock_type(stock_code):
    """取得個股類型"""
    stock_def = get_stock_definition(stock_code)
    if stock_def:
        return stock_def["type"]
    return "unknown"

def get_analysis_framework(stock_code):
    """取得分析框架"""
    stock_def = get_stock_definition(stock_code)
    if not stock_def:
        return None
    
    stock_type = stock_def["type"]
    
    if stock_type == "dividend":
        return {
            "type": "配息型",
            "analysis_items": [
                "股利穩定性（近5年現金股利、股票股利）",
                "殖利率（近10年平均殖利率）",
                "EPS成長率（年增率）",
                "配息率（股利/盈餘）",
                "填息能力（除息後填息天數）"
            ],
            "comparison_items": [
                "殖利率比較",
                "股利穩定性比較",
                "獲利成長比較"
            ],
            "risk_factors": stock_def.get("description", "")
        }
    elif stock_type == "growth":
        return {
            "type": "價差型",
            "analysis_items": [
                "價格位置（日/週/月最高最低）",
                "量能變化（日/週/月成交量）",
                "技術指標（均線、RSI、KD）",
                "趨勢判斷（上升/下降/盤整）",
                "支撐壓力（近期支撐價和壓力價）"
            ],
            "comparison_items": [
                "營收成長比較",
                "毛利率比較",
                "AI伺服器訂單比較"
            ],
            "risk_factors": stock_def.get("description", "")
        }
    elif stock_type == "etf":
        return {
            "type": "ETF",
            "analysis_items": [
                "追蹤誤差",
                "報酬率",
                "配息穩定性",
                "管理費"
            ],
            "comparison_items": [
                "與大盤表現比較",
                "與同類型ETF比較"
            ],
            "risk_factors": stock_def.get("description", "")
        }
    return None

def format_analysis_context(portfolio_data):
    """格式化分析上下文"""
    context_lines = []
    
    for stock in portfolio_data:
        code = stock['code']
        stock_def = get_stock_definition(code)
        if stock_def:
            context_lines.append(f"\n### {code} {stock_def['name']}")
            context_lines.append(f"- 類型：{stock_def['type']}（{stock_def['sub_industry']}）")
            context_lines.append(f"- 說明：{stock_def['description']}")
            context_lines.append(f"- 比較對象：{', '.join(stock_def['competitors'])}")
            context_lines.append(f"- 分析重點：{stock_def['analysis_focus']}")
            
            # 取得分析框架
            framework = get_analysis_framework(code)
            if framework:
                context_lines.append(f"- 分析項目：")
                for item in framework["analysis_items"]:
                    context_lines.append(f"  * {item}")
    
    return "\n".join(context_lines)

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

## 分析框架
### 配息型股票（金融股、電信股、公用事業）
分析項目：
- 股利穩定性（近5年現金股利、股票股利）
- 殖利率（近10年平均殖利率）
- EPS成長率（年增率）
- 配息率（股利/盈餘）
- 填息能力（除息後填息天數）

比較對象：
- 公股行庫：彰銀、第一金、合庫金、兆豐金
- 注意：彰銀是純銀行，合庫金是金控，業務結構不同
- 公股行庫特性：股價穩定、配息穩定、政策敏感
- 民營行庫特性：市場導向、獲利成長、競爭力強

### 價差型股票（電子股、成長股）
分析項目：
- 價格位置（日/週/月最高最低）
- 量能變化（日/週/月成交量）
- 技術指標（均線、RSI、KD）
- 趨勢判斷（上升/下降/盤整）
- 支撐壓力（近期支撐價和壓力價）

比較對象：
- 電子5哥：緯創、廣達、仁寶、英業達、和碩
- 分析重點：營收成長、毛利率、AI伺服器訂單

## 宏觀環境分析
- 利率：Fed升息/降息、台灣央行
- 匯率：台幣/美元、人民幣
- 物價：CPI、通膨預景
- 景氣：PMI、外銷訂單
- 國際：美中關係、地緣政治

## 風險評估
- 個股風險：公司獲利、產業競爭、管理層風險
- 產業風險：技術迭代、政策變化、市場需求
- 宏觀風險：經濟衰退、通膨、利率變動"""

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

def ask_ai_with_gemini(question, portfolio_context, api_key, model="gemini-3.5-flash", news_context="", analysis_context=""):
    """使用 Google Gemini 回答"""
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

{analysis_context}

{news_context}

用戶的問題：{question}

請根據以上資料，按照分析框架回答用戶的問題。"""
    
    try:
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model=model,
            contents=f"{AI_SYSTEM_PROMPT}\n\n{user_prompt}"
        )
        return response.text
    except ImportError:
        return "⚠️ 需要安裝 google-genai 套件"
    except Exception as e:
        return f"⚠️ Gemini 錯誤：{str(e)}"

def ask_ai_with_groq(question, portfolio_context, api_key, model="llama-3.3-70b-versatile", news_context="", analysis_context=""):
    """使用 Groq 回答"""
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

{analysis_context}

{news_context}

用戶的問題：{question}

請根據以上資料，按照分析框架回答用戶的問題。"""
    
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

def ask_ai_with_openrouter(question, portfolio_context, api_key, model="deepseek/deepseek-v4-flash", news_context="", analysis_context=""):
    """使用 OpenRouter 回答"""
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

{analysis_context}

{news_context}

用戶的問題：{question}

請根據以上資料，按照分析框架回答用戶的問題。"""
    
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

def ask_ai_with_anthropic(question, portfolio_context, api_key, model="claude-sonnet-4-20250514", news_context="", analysis_context=""):
    """使用 Anthropic Claude 回答"""
    user_prompt = f"""以下是用戶目前的持股資料：

{portfolio_context}

{analysis_context}

{news_context}

用戶的問題：{question}

請根據以上資料，按照分析框架回答用戶的問題。"""
    
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

def ask_ai(question, portfolio_context, provider_name, model_name, news_context="", analysis_context=""):
    """使用選定的 AI 供應商回答"""
    api_key = get_provider_key(provider_name)
    
    if not api_key:
        return f"⚠️ {provider_name} API Key 未設定"
    
    # 根據供應商選擇對應的函數
    if provider_name == "Google Gemini":
        result = ask_ai_with_gemini(question, portfolio_context, api_key, model_name, news_context, analysis_context)
    elif provider_name == "Groq":
        result = ask_ai_with_groq(question, portfolio_context, api_key, model_name, news_context, analysis_context)
    elif provider_name == "OpenRouter":
        result = ask_ai_with_openrouter(question, portfolio_context, api_key, model_name, news_context, analysis_context)
    elif provider_name == "Anthropic":
        result = ask_ai_with_anthropic(question, portfolio_context, api_key, model_name, news_context, analysis_context)
    else:
        result = None
    
    if result:
        return result
    
    return f"⚠️ {provider_name} 請求失敗，請稍後再試"

# ==================== 網路搜尋功能 ====================
def search_stock_news(query, max_results=5):
    """暫時停用新聞搜尋 - 網站結構頻繁變動，需要定期維護"""
    # 回傳空列表，讓 AI 使用歷史資料分析
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
    
    # 分類持股
    dividend_stocks = []
    growth_stocks = []
    etf_stocks = []
    
    for stock in portfolio_data:
        stock_type = get_stock_type(stock['code'])
        if stock_type == "dividend":
            dividend_stocks.append(stock)
        elif stock_type == "growth":
            growth_stocks.append(stock)
        elif stock_type == "etf":
            etf_stocks.append(stock)
    
    # 顯示配息型股票
    if dividend_stocks:
        lines.append("## 配息型股票（金融股）")
        lines.append("特性：股價穩定、配息穩定、防禦型標的")
        lines.append("")
        for stock in dividend_stocks:
            stock_def = get_stock_definition(stock['code'])
            lines.append(f"### {stock['code']} {stock['name']}")
            lines.append(f"- 類型：{stock_def['sub_industry']}")
            lines.append(f"- 持有：{stock['shares']:,} 股")
            lines.append(f"- 成本：{stock['cost']:,} 元（每股 {stock['cost_per_share']:.2f} 元）")
            lines.append(f"- 目前價格：{stock['currentPrice']:.2f} 元")
            lines.append(f"- 市值：{stock['marketValue']:,.0f} 元")
            lines.append(f"- 未實現損益：{stock['unrealizedPnl']:+,.0f} 元 ({stock['unrealizedPnlPct']:+.2f}%)")
            lines.append(f"- 分析重點：{stock_def['analysis_focus']}")
            lines.append(f"- 比較對象：{', '.join(stock_def['competitors'])}")
            lines.append("")
    
    # 顯示價差型股票
    if growth_stocks:
        lines.append("## 價差型股票（電子股）")
        lines.append("特性：營收大、利潤薄、受科技趨勢影響")
        lines.append("")
        for stock in growth_stocks:
            stock_def = get_stock_definition(stock['code'])
            lines.append(f"### {stock['code']} {stock['name']}")
            lines.append(f"- 類型：{stock_def['sub_industry']}")
            lines.append(f"- 持有：{stock['shares']:,} 股")
            lines.append(f"- 成本：{stock['cost']:,} 元（每股 {stock['cost_per_share']:.2f} 元）")
            lines.append(f"- 目前價格：{stock['currentPrice']:.2f} 元")
            lines.append(f"- 市值：{stock['marketValue']:,.0f} 元")
            lines.append(f"- 未實現損益：{stock['unrealizedPnl']:+,.0f} 元 ({stock['unrealizedPnlPct']:+.2f}%)")
            lines.append(f"- 分析重點：{stock_def['analysis_focus']}")
            lines.append(f"- 比較對象：{', '.join(stock_def['competitors'])}")
            lines.append("")
    
    # 顯示ETF
    if etf_stocks:
        lines.append("## ETF")
        lines.append("特性：分散風險、追蹤大盤、低管理費")
        lines.append("")
        for stock in etf_stocks:
            stock_def = get_stock_definition(stock['code'])
            lines.append(f"### {stock['code']} {stock['name']}")
            lines.append(f"- 類型：{stock_def['sub_industry']}")
            lines.append(f"- 持有：{stock['shares']:,} 股")
            lines.append(f"- 成本：{stock['cost']:,} 元（每股 {stock['cost_per_share']:.2f} 元）")
            lines.append(f"- 目前價格：{stock['currentPrice']:.2f} 元")
            lines.append(f"- 市值：{stock['marketValue']:,.0f} 元")
            lines.append(f"- 未實現損益：{stock['unrealizedPnl']:+,.0f} 元 ({stock['unrealizedPnlPct']:+.2f}%)")
            lines.append(f"- 分析重點：{stock_def['analysis_focus']}")
            lines.append("")
    
    # 總計
    total_cost = sum(s['cost'] for s in portfolio_data)
    total_market = sum(s['marketValue'] for s in portfolio_data)
    total_pnl = total_market - total_cost
    
    lines.append("## 總計")
    lines.append(f"- 總成本：{total_cost:,} 元")
    lines.append(f"- 總市值：{total_market:,.0f} 元")
    lines.append(f"- 未實現損益：{total_pnl:+,.0f} 元 ({total_pnl/total_cost*100:+.2f}%)")
    
    return "\n".join(lines)

# 持股資料
PORTFOLIO = [
    {'code': '2801', 'name': '彰銀', 'shares': 2000, 'cost': 41950, 'prevClose': 23.20},
    {'code': '5880', 'name': '合庫金', 'shares': 2000, 'cost': 45800, 'prevClose': 24.55},
    {'code': '3231', 'name': '緯創', 'shares': 200, 'cost': 31400, 'prevClose': 155.00},
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
        
        # 顯示分析框架
        st.markdown("### 📊 分析框架")
        for stock in PORTFOLIO:
            stock_def = get_stock_definition(stock['code'])
            if stock_def:
                with st.expander(f"{stock['code']} {stock['name']}"):
                    st.markdown(f"**類型：** {stock_def['type']}（{stock_def['sub_industry']}）")
                    st.markdown(f"**分析重點：** {stock_def['analysis_focus']}")
                    st.markdown(f"**比較對象：** {', '.join(stock_def['competitors'])}")
        
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
    
    # 添加股票類型資訊
    for stock in portfolio_data:
        stock_def = get_stock_definition(stock['code'])
        if stock_def:
            stock['type'] = stock_def['type']
            stock['sub_industry'] = stock_def['sub_industry']
        else:
            stock['type'] = 'unknown'
            stock['sub_industry'] = 'unknown'
    
    df = pd.DataFrame(portfolio_data)
    df = df.rename(columns={
        'code': '股票代號',
        'name': '股票名稱',
        'type': '類型',
        'sub_industry': '產業',
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
        df[['股票代號', '股票名稱', '類型', '產業', '持有股數', '成本', '目前價格', '市值', '未實現損益', '損益%', '交易日']],
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
    
    # 新聞搜尋選項 (暫時停用)
    st.info("📰 新聞搜尋功能暫時停用中（網站結構變動，需要維護）。AI 將使用持股資料進行分析。")
    
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
                analysis_context = format_analysis_context(portfolio_data)
                
                # 使用選定的 AI 供應商 (暫時不使用新聞)
                provider_name = st.session_state.get("selected_provider", "Groq")
                model_name = st.session_state.get("selected_model", "llama-3.3-70b-versatile")
                
                response = ask_ai(prompt, portfolio_context, provider_name, model_name, "", analysis_context)
                
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == '__main__':
    main()
