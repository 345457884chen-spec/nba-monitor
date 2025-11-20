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
    print("正在启动 NBA 监控 (Data API 修复版)...")
    
    # 使用 Data API (虽然旧，但不用 Key，且我们现在知道字段名了)
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
    check_window = 60 * 60 # 60分钟回看窗口

    print(f"获取到 {len(activities)} 条记录，正在分析...")

    for item in activities:
        try:
            # 1. 提取关键字段 (根据你提供的 JSON 修正)
            # 优先找 'slug'，如果没找到再找 'market_slug'
            slug = item.get('slug') or item.get('market_slug') or ''
            title = item.get('title') or ''
            event_slug = item.get('eventSlug') or ''
            
            # 把所有可能包含名字的地方拼起来检查
            full_text = (slug + " " + title + " " + event_slug).upper()
            
            # 2. 筛选 NBA 关键词
            if "NBA" not in full_text and "BASKETBALL" not in full_text:
                continue

            # 3. 筛选动作类型
            # 我们只关心买入操作 (BUY 或 TRADE)
            # REDEEM 是领奖，WITHDRAW 是提现，这些跳过
            action_type = item.get('type', '').upper()
            if action_type not in ['BUY', 'TRADE']:
                continue

            # 4. 时间处理
            ts = float(item.get('timestamp', 0))
            if ts > 9999999999: ts = ts / 1000
            
            if now - ts > check_window:
                continue

            # 5. 计算金额
            price = float(item.get('price', 0) or 0)
            size = float(item.get('size', 0) or 0)
            usdc_size = float(item.get('usdcSize', 0) or 0) # 有时候叫 usdcSize
            value = float(item.get('value', 0) or 0)
            
            # 智能计算金额：优先用 value，其次用 price*size，最后用 usdcSize
            amount = value
            if amount == 0:
                amount = price * size
            if amount == 0:
                amount = usdc_size

            # 6. 准备推送内容
            # 既然找到了 title (比如 Wizards vs. Timberwolves)，我们就显示它
            display_title = title if title else slug
            
            time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
            
            msg = (
                f"🚨 **监控到 NBA 下单!**\n\n"
                f"🏀 **比赛**: {display_title}\n"
                f"💰 **金额**: ${amount:,.0f} USD\n"
                f"📝 **动作**: {action_type}\n"
                f"⌚ **时间**: {time_str}\n"
                f"🔗 [👉 查看地址详情](https://polymarket.com/profile/{TARGET_ADDRESS})"
            )
            
            send_telegram_message(msg)
            found_count += 1
            print(f"✅ 已推送 NBA 订单: {display_title}")

        except Exception as e:
            print(f"处理单条数据出错: {e}")
            continue

    if found_count == 0:
        print("过去 60 分钟内无 NBA 开单操作。")

if __name__ == "__main__":
    check_trades()
