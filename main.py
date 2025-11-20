import cloudscraper
import datetime
import time
import os

# ================== 配置区域 ==================
# 这里我们不再直接填 Token，而是让代码去系统里读取，这样最安全
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TARGET_ADDRESS = '0xf5d9a163cb1a6865cd2a1854cef609ab29b2a6e1'.lower()
# ============================================

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ 错误：未检测到 Token 或 Chat ID，请在 GitHub Secrets 中配置！")
        return
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    scraper = cloudscraper.create_scraper()
    try:
        scraper.post(url, data=data)
    except Exception as e:
        print(f"TG推送失败: {e}")

def check_trades():
    print("正在启动监控检查...")
    
    # 获取最近20条记录
    url = f"https://data-api.polymarket.com/activity?user={TARGET_ADDRESS}&limit=20"
    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(url, timeout=15)
        if response.status_code != 200:
            print(f"接口报错: {response.status_code}")
            return
        activities = response.json()
    except Exception as e:
        print(f"连接报错: {e}")
        return

    # 获取当前时间
    now = time.time()
    found_count = 0
    
    # 我们设定的检查频率是每15分钟运行一次
    # 所以我们只筛选“过去 16 分钟内”的订单（多1分钟防止漏单）
    check_window = 30 * 60 

    for item in activities:
        # 1. 只看买入
        if item.get('type') != 'buy':
            continue
            
        # 2. 处理时间
        ts = int(item.get('timestamp', 0))
        if ts > 9999999999: ts = ts / 1000 # 处理毫秒
            
        # 3. 核心判断：如果这个订单发生的时间，距离现在超过了16分钟，就忽略
        # 这样就避免了重复推送旧的订单
        if now - ts > check_window:
            continue
            
        # 4. 获取信息
        slug = item.get('market_slug', '')
        asset = item.get('asset_name', '')
        title = slug.replace('-', ' ').upper()
        
        # 5. 筛选 NBA
        if "NBA" in title or "BASKETBALL" in title:
            # 计算金额
            price = float(item.get('price', 0) or 0)
            size = float(item.get('size', 0) or 0)
            value = float(item.get('value', 0) or 0)
            amount = value if value > 0 else price * size
            
            time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
            
            msg = (
                f"🚨 **监控到新下单!**\n\n"
                f"🏀 **内容**: {slug}\n"
                f"💰 **金额**: ${amount:,.0f} USD\n"
                f"🎯 **方向**: {asset} (价格: {price:.2f})\n"
                f"⌚ **时间**: {time_str}\n"
                f"🔗 [查看详情](https://polymarket.com/profile/{TARGET_ADDRESS})"
            )
            send_telegram_message(msg)
            found_count += 1
            print(f"已推送: {slug}")

    if found_count == 0:
        print("过去 15 分钟无 NBA 买入操作。")

if __name__ == "__main__":
    check_trades()
