import cloudscraper
import datetime
import time
import os

# ================== 配置区域 ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TARGET_ADDRESS = '0xf5d9a163cb1a6865cd2a1854cef609ab29b2a6e1'.lower()
# ============================================

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ 错误：未配置 Token 或 Chat ID")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    scraper = cloudscraper.create_scraper()
    try:
        scraper.post(url, data=data)
    except Exception as e:
        print(f"TG推送失败: {e}")

def check_trades():
    print("正在启动 Gamma API 监控...")
    
    # 🔥 核心修改：切换到 Gamma API (Polymarket 的新版接口)
    # 这个接口返回的数据里，直接包含了 market 信息，不会是 N/A
    url = f"https://gamma-api.polymarket.com/accounts/{TARGET_ADDRESS}/trades?limit=20"
    
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url, timeout=15)
        if response.status_code != 200:
            print(f"接口报错: {response.status_code}")
            return
        trades = response.json()
    except Exception as e:
        print(f"连接报错: {e}")
        return

    # 获取当前时间
    now = time.time()
    found_count = 0
    
    # 设定回顾窗口：60分钟 (防止 GitHub 迟到)
    check_window = 60 * 60 

    print(f"获取到 {len(trades)} 条交易记录，开始分析...")

    for item in trades:
        try:
            # 1. 筛选：只看买入 (BUY)
            # 新接口里叫 'side': 'BUY'
            if item.get('side') != 'BUY':
                continue
            
            # 2. 时间处理 (Gamma API 返回的是秒级时间戳)
            ts = float(item.get('timestamp', 0))
            
            # 如果订单时间距离现在超过了 60 分钟，就跳过
            if now - ts > check_window:
                continue

            # 3. 获取关键信息 (重点！这里不会是 N/A 了)
            # 新接口把信息藏在 'market' 这个字典里
            market_info = item.get('market', {})
            slug = market_info.get('slug', 'N/A')      # 例如: nba-champion-2025
            question = market_info.get('question', '')  # 例如: NBA Champion 2025?
            
            # 组合一个标题用于检查
            full_title = (slug + " " + question).upper()
            
            # 4. 打印调试信息 (让你看清楚它读到了什么)
            print(f"检查订单: {slug} | 时间: {datetime.datetime.fromtimestamp(ts)}")

            # 5. 筛选 NBA 关键词
            if "NBA" in full_title or "BASKETBALL" in full_title:
                # 计算金额
                price = float(item.get('price', 0) or 0)
                size = float(item.get('size', 0) or 0)
                amount = price * size
                
                # 买了谁 (例如 Celtics)
                outcome = item.get('outcomeIndex', 'N/A') 
                # 有时候 Gamma API 不直接给 outcome 名字，我们用 Question 代替
                
                time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
                
                msg = (
                    f"🚨 **新买单监控 (Gamma版)**\n\n"
                    f"🏀 **问题**: {question}\n"
                    f"💰 **金额**: ${amount:,.0f} USD\n"
                    f"🎯 **价格**: ${price:.2f}\n"
                    f"⌚ **时间**: {time_str}\n"
                    f"🔗 [查看地址](https://polymarket.com/profile/{TARGET_ADDRESS})"
                )
                send_telegram_message(msg)
                found_count += 1
                print(f"✅ 已推送 NBA 订单: {slug}")
            else:
                print(f"❌ 忽略非 NBA 订单")

        except Exception as e:
            print(f"处理单条数据出错: {e}")
            continue

    if found_count == 0:
        print("过去 60 分钟内无 NBA 买入。")

if __name__ == "__main__":
    check_trades()
