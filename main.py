import cloudscraper
import datetime
import time
import os

# ================== 配置区域 ==================
TARGET_ADDRESS = '0xf5d9a163cb1a6865cd2a1854cef609ab29b2a6e1'.lower()
# ============================================

def debug_trades():
    print("🔍 正在启动【深度诊断】模式...")
    print(f"正在抓取地址: {TARGET_ADDRESS} 的最近交易...")
    
    url = f"https://data-api.polymarket.com/activity?user={TARGET_ADDRESS}&limit=20"
    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(url, timeout=15)
        activities = response.json()
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return

    print(f"✅ 成功获取到 {len(activities)} 条记录，正在逐条分析：")
    print("-" * 50)

    for item in activities:
        # 1. 提取基本信息
        action_type = item.get('type') # buy 或 sell
        slug = item.get('market_slug', 'N/A')
        timestamp = int(item.get('timestamp', 0))
        if timestamp > 9999999999: timestamp /= 1000
        
        time_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        # 2. 打印这条交易的“原始身份证”
        print(f"🕒 时间: {time_str}")
        print(f"🏷️ 内容(Slug): {slug}")
        print(f"ww 动作: {action_type}")
        
        # 3. 模拟机器人的判断逻辑
        title = slug.replace('-', ' ').upper()
        is_nba = "NBA" in title or "BASKETBALL" in title
        
        if is_nba:
            print(f"🤖 机器人判定: ✅ 是 NBA 订单")
        else:
            print(f"🤖 机器人判定: ❌ 不是 NBA (关键词不匹配)")
            
        print("-" * 50)

if __name__ == "__main__":
    debug_trades()
