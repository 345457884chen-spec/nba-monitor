import cloudscraper
import json
import os

# ================== 配置区域 ==================
TARGET_ADDRESS = '0xf5d9a163cb1a6865cd2a1854cef609ab29b2a6e1'.lower()
# ============================================

def diagnose():
    print("👨‍⚕️ 正在启动【手术级】诊断...")
    
    # 回到那个唯一能连上的 Data API
    url = f"https://data-api.polymarket.com/activity?user={TARGET_ADDRESS}&limit=10"
    
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url, timeout=15)
        if response.status_code != 200:
            print(f"❌ 连不上: {response.status_code}")
            return
        activities = response.json()
    except Exception as e:
        print(f"❌ 报错: {e}")
        return

    print(f"✅ 获取到 {len(activities)} 条记录。")
    print("正在寻找那个 N/A 的订单...\n")

    found_na = False
    
    for i, item in enumerate(activities):
        # 简单的打印一下概要
        slug = item.get('market_slug')
        
        # 如果我们找到了一个 slug 是 None (N/A) 的订单，或者就是你刚才那个时间点的
        # 我们就把它的【全部内容】打印出来
        if slug is None or slug == "null" or slug == "":
            print(f"🚨 找到第 {i+1} 条是 N/A 订单！")
            print("=" * 30)
            print("👇 这个订单的完整原始数据 (请把下面这段截图或复制给我) 👇")
            print("=" * 30)
            
            # 这行代码会把所有隐藏的信息都打印出来
            print(json.dumps(item, indent=4, ensure_ascii=False))
            
            print("=" * 30)
            found_na = True
            # 为了不刷屏，只打第一个找到的 N/A
            break 
    
    if not found_na:
        print("🤔 奇怪，这次获取的前10条里没有发现 N/A 订单。")
        print("👇 为了保险，我打印第一条的完整数据给你看看：")
        if len(activities) > 0:
            print(json.dumps(activities[0], indent=4, ensure_ascii=False))

if __name__ == "__main__":
    diagnose()
