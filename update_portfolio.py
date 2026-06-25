#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持股追蹤自動更新腳本
從台灣證券交易所 (TWSE) 抓取最新收盤價，並更新 HTML 資料檔
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import os
import sys

# 設定檔案路徑
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, 'portfolio_data.json')

# 持股資料
PORTFOLIO = [
    {'code': '2801', 'name': '彰銀', 'shares': 2000, 'cost': 41950, 'prevClose': 23.20},
    {'code': '5880', 'name': '合庫金', 'shares': 2000, 'cost': 45800, 'prevClose': 24.55},
    {'code': '3231', 'name': '緯創', 'shares': 100, 'cost': 15900, 'prevClose': 158.50},
    {'code': '009816', 'name': '凱基台灣TOP50', 'shares': 4000, 'cost': 53690, 'prevClose': 15.97},
]

REALIZED_PNL = 1698

def fetch_twse_data(stock_code, date_str=None):
    """從 TWSE API 抓取個股成交資訊"""
    if date_str is None:
        # 使用民國年格式
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
        print(f"  ❌ 抓取 {stock_code} 失敗: {e}")
        return None

def get_latest_close_price(data):
    """從 TWSE 回傳資料中取得最新收盤價"""
    if data and data.get('stat') == 'OK' and data.get('data'):
        latest = data['data'][-1]  # 取最後一筆（最新）
        # 資料格式: [日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數]
        close_price = float(latest[6].replace(',', ''))
        trade_date = latest[0]
        return close_price, trade_date
    return None, None

def update_portfolio_data():
    """更新所有持股資料"""
    print("=" * 50)
    print(f"📊 持股追蹤自動更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    updated_data = []
    
    for stock in PORTFOLIO:
        print(f"\n🔍 正在查詢 {stock['code']} {stock['name']}...")
        
        data = fetch_twse_data(stock['code'])
        close_price, trade_date = get_latest_close_price(data)
        
        if close_price is not None:
            print(f"  ✅ 最新收盤價: {close_price} (日期: {trade_date})")
            updated_stock = {
                'code': stock['code'],
                'name': stock['name'],
                'shares': stock['shares'],
                'cost': stock['cost'],
                'prevClose': stock['prevClose'],
                'currentPrice': close_price,
                'tradeDate': trade_date
            }
        else:
            print(f"  ⚠️ 無法取得最新價格，使用前次收盤價")
            updated_stock = {
                'code': stock['code'],
                'name': stock['name'],
                'shares': stock['shares'],
                'cost': stock['cost'],
                'prevClose': stock['prevClose'],
                'currentPrice': stock['prevClose'],
                'tradeDate': '--'
            }
        
        updated_data.append(updated_stock)
    
    # 寫入 JSON 檔案
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 資料已更新至: {DATA_FILE}")
    
    # 顯示摘要
    print("\n" + "=" * 50)
    print("📋 持股摘要")
    print("=" * 50)
    
    total_cost = 0
    total_market_value = 0
    
    for stock in updated_data:
        market_value = stock['shares'] * stock['currentPrice']
        unrealized_pnl = market_value - stock['cost']
        pnl_sign = '+' if unrealized_pnl >= 0 else ''
        total_cost += stock['cost']
        total_market_value += market_value
        
        print(f"{stock['code']} {stock['name']}: {stock['currentPrice']:.2f} | 損益: {pnl_sign}{unrealized_pnl:,.0f}")
    
    unrealized_pnl_total = total_market_value - total_cost
    total_pnl = unrealized_pnl_total + REALIZED_PNL
    total_return = (total_pnl / total_cost * 100)
    
    print("-" * 50)
    print(f"持股成本: {total_cost:,.0f}")
    print(f"目前市值: {total_market_value:,.0f}")
    print(f"未實現損益: {'+' if unrealized_pnl_total >= 0 else ''}{unrealized_pnl_total:,.0f}")
    print(f"已實現損益: +{REALIZED_PNL:,.0f}")
    print(f"合計損益: {'+' if total_pnl >= 0 else ''}{total_pnl:,.0f}")
    print(f"整體報酬率: {'+' if total_return >= 0 else ''}{total_return:.2f}%")
    print("=" * 50)
    print("✅ 更新完成！")

if __name__ == '__main__':
    update_portfolio_data()
