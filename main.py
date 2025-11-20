import cloudscraper
import datetime
import time
import os
import json

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
    print("正在启动 NBA 监控 (显示球队版)...")
    
    # 使用稳定的 Data API
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

    now = time.time()
    found_count = 0
    check_window = 60 * 60  # 60分钟回顾窗口

    print(f"获取到 {len(activities)} 条记录，正在分析...")

    for item in activities:
        try:
            # 1. 提取名字
            slug = item.get('slug') or item.get('market_slug') or ''
            title = item.get('title') or ''
            event_slug = item.get('eventSlug') or ''
            full_text = (slug + " " + title + " " + event_slug).upper()
            
            # 2. 筛选 NBA
            if "NBA" not in full_text and "BASKETBALL" not in full_text:
                continue

            # 3. 筛选动作 (只看买入)
            action_type = item.get('type', '').upper()
            if action_type not in ['BUY', 'TRADE']:
                continue

            # 4. 时间过滤
            ts = float(item.get('timestamp', 0))
            if ts > 9999999999: ts = ts / 1000
            if now - ts > check_window:
                continue

            # 5. 计算金额
            price = float(item.get('price', 0) or 0)
            size = float(item.get('size', 0) or 0)
            usdc_size = float(item.get('usdcSize', 0) or 0)
            value = float(item.get('value', 0) or 0)
            amount = value if value > 0 else (price * size if price * size > 0 else usdc_size)

            # 6. 🔥 关键新增：获取他买了哪支队伍
            # 'asset' 字段通常存着 "Lakers" 或 "Celtics"
            # 如果是 "Yes/No" 类型，这里就会显示 "Yes" 或 "No"
            picked_team = item.get('asset', '')
            
            # 如果 asset 是空的，尝试用 outcome 字段兜底
            if not picked_team:
                picked_team = item.get('outcome', 'N/A')

            # 准备显示标题
            display_title = title if title else slug
            time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
            
            # 7. 发送消息
            msg = (
                f"🚨 **监控到 NBA 下单!**\n\n"
                f"🏀 **比赛**: {display_title}\n"
                f"🏆 **买入**: {picked_team}\n"  # <--- 这里会显示球队名
                f"💰 **金额**: ${amount:,.0f} USD\n"
                f"⌚ **时间**: {time_str}\n"
                f"🔗 [👉 查看地址详情](https://polymarket.com/profile/{TARGET_ADDRESS})"
            )
            
            send_telegram_message(msg)
            found_count += 1
            print(f"✅ 已推送: {display_title} - {picked_team}")

        except Exception as e:
            print(f"处理单条数据出错: {e}")
            continue

    if found_count == 0:
        print("过去 60 分钟内无 NBA 开单操作。")

if __name__ == "__main__":
    check_trades()
