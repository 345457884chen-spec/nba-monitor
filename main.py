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

# 🔥 核心升级：获取盘口完整信息
def resolve_market_details(slug, token_id):
    """
    输入：比赛代码(slug) 和 Token ID
    输出：(具体选项, 盘口名称) 
    例如：('Lakers -2.5', 'Spread') 或 ('Over', 'Total Points: 228.5')
    """
    print(f"🕵️‍♂️ 正在深度解析 ID: {token_id} ...")
    
    url = f"https://gamma-api.polymarket.com/events?slug={slug}"
    scraper = cloudscraper.create_scraper()
    
    try:
        resp = scraper.get(url, timeout=10)
        if resp.status_code != 200:
            return None, None
        
        data = resp.json()
        
        # 遍历该比赛下的所有盘口（胜负、让分、大小分等都在这里面）
        for market in data.get('markets', []):
            clob_ids = market.get('clobTokenIds', [])
            outcomes = market.get('outcomes', [])
            question = market.get('question', '未知盘口') # 获取盘口标题
            
            target_id = str(token_id)
            
            if target_id in clob_ids:
                index = clob_ids.index(target_id)
                outcome_name = outcomes[index]
                
                # 💡 特殊处理：如果是大小分，盘口标题通常包含分数 (Total: 228.5)
                # 我们把 outcome 和 question 结合一下，看起来更直观
                return outcome_name, question
                
    except Exception as e:
        print(f"解析出错: {e}")
    
    return None, None

def check_trades():
    print("正在启动 NBA 全盘口监控...")
    
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
    check_window = 60 * 60  # 检查过去1小时

    print(f"获取到 {len(activities)} 条记录，正在分析...")

    for item in activities:
        try:
            # 1. 基础过滤
            slug = item.get('slug') or item.get('market_slug') or ''
            title = item.get('title') or ''
            event_slug = item.get('eventSlug') or ''
            
            full_text = (slug + " " + title + " " + event_slug).upper()
            
            # 只看篮球/NBA
            if "NBA" not in full_text and "BASKETBALL" not in full_text:
                continue

            action_type = item.get('type', '').upper()
            if action_type not in ['BUY', 'TRADE']:
                continue

            ts = float(item.get('timestamp', 0))
            if ts > 9999999999: ts = ts / 1000
            if now - ts > check_window:
                continue

            # 2. 计算金额
            price = float(item.get('price', 0) or 0)
            size = float(item.get('size', 0) or 0)
            usdc_size = float(item.get('usdcSize', 0) or 0)
            value = float(item.get('value', 0) or 0)
            amount = value if value > 0 else (price * size if price * size > 0 else usdc_size)

            # =========================================
            # 🔥 核心修改：无论显示什么，都强制进行深度解析
            # =========================================
            raw_asset = str(item.get('asset', ''))      # Token ID
            raw_outcome = str(item.get('outcome', ''))  # 有时候是 ID，有时候是名字
            
            # 优先使用 Asset ID (Token ID) 去查，因为最准
            token_id_to_check = raw_asset if (raw_asset and len(raw_asset) > 5) else raw_outcome
            search_slug = event_slug if event_slug else slug

            real_outcome = "解析中..."
            market_question = "未知盘口"

            if token_id_to_check and len(str(token_id_to_check)) > 5:
                res_outcome, res_question = resolve_market_details(search_slug, token_id_to_check)
                if res_outcome:
                    real_outcome = res_outcome
                    market_question = res_question
            else:
                # 如果没有ID，只能用原始名称
                real_outcome = raw_outcome

            # 3. 构建更清晰的显示文案
            # 判断盘口类型，加一些 Emoji 方便快速识别
            market_tag = "🏀 胜负盘"
            if "Spread" in market_question or "Handicap" in market_question:
                market_tag = "⚖️ 让分盘 (Spread)"
            elif "Total" in market_question or "Over" in market_question or "Under" in market_question:
                market_tag = "🔢 大小分 (Total)"
            elif "Quarter" in market_question:
                market_tag = "1️⃣ 单节 (Quarter)"
            elif "Half" in market_question:
                market_tag = "🌗 半场 (Half)"

            time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
            
            msg = (
                f"🚨 **监控到 NBA 下单!**\n"
                f"➖➖➖➖➖➖➖➖➖\n"
                f"🏟️ **比赛**: {title}\n"
                f"📌 **盘口**: {market_tag}\n"
                f"📝 **详情**: {market_question}\n"
                f"🎯 **买入**: `{real_outcome}`\n" 
                f"💰 **金额**: ${amount:,.0f} USD\n"
                f"⌚ **时间**: {time_str}\n"
                f"🔗 [👉 查看地址详情](https://polymarket.com/profile/{TARGET_ADDRESS})"
            )
            
            send_telegram_message(msg)
            found_count += 1
            print(f"✅ 已推送: {real_outcome} [{market_question}]")

        except Exception as e:
            print(f"处理单条数据出错: {e}")
            continue

    if found_count == 0:
        print("过去 60 分钟内无 NBA 开单操作。")

if __name__ == "__main__":
    check_trades()
