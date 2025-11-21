import cloudscraper
import datetime
import time
import os
import json

# ================== 配置区域 ==================
# 本地跑请直接填 Token，GitHub跑请保持 os.environ
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

# 🔥 新增：强制翻译函数
def resolve_team_name(slug, token_id):
    """
    输入：比赛代码(slug) 和 那串乱码数字(token_id)
    输出：真正的球队名字 (例如 Hawks)
    """
    print(f"🕵️‍♂️ 正在去数据库反查 ID: {token_id} ...")
    
    # 这是一个很少人知道的高级接口，专门查市场详情
    url = f"https://gamma-api.polymarket.com/events?slug={slug}"
    scraper = cloudscraper.create_scraper()
    
    try:
        resp = scraper.get(url, timeout=10)
        if resp.status_code != 200:
            return "查询超时"
        
        data = resp.json()
        # 在返回的数据里，寻找哪个市场的 tokenID 和我们要找的一样
        for market in data.get('markets', []):
            clob_ids = market.get('clobTokenIds', []) # 这里的 ID 是字符串
            outcomes = market.get('outcomes', [])     # 这里是名字 ['Hawks', 'Spurs']
            
            # 把我们要找的数字转成字符串对比
            target_id = str(token_id)
            
            if target_id in clob_ids:
                # 找到了！获取对应的位置
                index = clob_ids.index(target_id)
                real_name = outcomes[index]
                print(f"✅ 破案了！ID {token_id} = {real_name}")
                return real_name
                
    except Exception as e:
        print(f"翻译出错: {e}")
    
    return "解析失败"

def check_trades():
    print("正在启动 NBA 监控 (智能翻译版)...")
    
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
    check_window = 60 * 60 

    print(f"获取到 {len(activities)} 条记录，正在分析...")

    for item in activities:
        try:
            # 1. 基础信息
            slug = item.get('slug') or item.get('market_slug') or ''
            title = item.get('title') or ''
            event_slug = item.get('eventSlug') or ''
            full_text = (slug + " " + title + " " + event_slug).upper()
            
            if "NBA" not in full_text and "BASKETBALL" not in full_text:
                continue

            action_type = item.get('type', '').upper()
            if action_type not in ['BUY', 'TRADE']:
                continue

            ts = float(item.get('timestamp', 0))
            if ts > 9999999999: ts = ts / 1000
            if now - ts > check_window:
                continue

            # 计算金额
            price = float(item.get('price', 0) or 0)
            size = float(item.get('size', 0) or 0)
            usdc_size = float(item.get('usdcSize', 0) or 0)
            value = float(item.get('value', 0) or 0)
            amount = value if value > 0 else (price * size if price * size > 0 else usdc_size)

            # =========================================
            # 🔥 核心修改：智能识别与强制翻译
            # =========================================
            raw_asset = str(item.get('asset', ''))
            raw_outcome = str(item.get('outcome', ''))
            
            picked_team = "未知"

            # 1. 先看是不是现成的名字
            if raw_outcome and not (raw_outcome.isdigit() and len(raw_outcome) > 5):
                picked_team = raw_outcome
            elif raw_asset and not (raw_asset.isdigit() and len(raw_asset) > 5):
                picked_team = raw_asset
            
            # 2. 如果发现是乱码数字，立刻启动【强制翻译】
            else:
                # 找到那个乱码数字
                token_id_to_check = raw_outcome if (raw_outcome.isdigit() and len(raw_outcome)>5) else raw_asset
                
                if token_id_to_check:
                    # ⚡️ 调用上面的翻译函数
                    # 我们用 event_slug 或 slug 去查数据库
                    search_slug = event_slug if event_slug else slug
                    translated_name = resolve_team_name(search_slug, token_id_to_check)
                    
                    if translated_name and translated_name != "解析失败":
                        picked_team = translated_name
                    else:
                        picked_team = "⏳ 等待官方更新..."

            display_title = title if title else slug
            time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
            
            msg = (
                f"🚨 **监控到 NBA 下单!**\n\n"
                f"🏀 **比赛**: {display_title}\n"
                f"🏆 **买入**: {picked_team}\n" 
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
