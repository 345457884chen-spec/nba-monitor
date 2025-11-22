import cloudscraper
import datetime
import time
import os
import json

# ================== 配置区域 ==================
# GitHub Actions 环境变量读取
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

# 🔥 核心升级 v2.1：双重查询机制 + 异常处理
def resolve_market_details(slug, event_slug, token_id):
    """
    输入：slug (小标题), event_slug (大标题), token_id (身份证号)
    输出：(具体选项, 盘口名称)
    """
    print(f"🕵️‍♂️ 正在解析 ID: {token_id} ...")

    # 定义内部函数，复用查询逻辑
    def fetch_from_api(search_slug_key):
        if not search_slug_key: return None, None
        
        # print(f"   🔍 尝试查询 slug: {search_slug_key} ...") 
        url = f"https://gamma-api.polymarket.com/events?slug={search_slug_key}"
        scraper = cloudscraper.create_scraper()
        try:
            resp = scraper.get(url, timeout=10)
            if resp.status_code != 200: return None, None
            
            data = resp.json()
            # 遍历该事件下的所有市场 (胜负/让分/大小分都在这里)
            for market in data.get('markets', []):
                clob_ids = market.get('clobTokenIds', [])
                target_id = str(token_id)
                
                if target_id in clob_ids:
                    index = clob_ids.index(target_id)
                    outcomes = market.get('outcomes', [])
                    
                    # 获取选项名字 (如 'Lakers' 或 'Over')
                    outcome_name = outcomes[index] if index < len(outcomes) else "Unknown"
                    # 获取盘口具体问题 (如 'Lakers vs Warriors Spread')
                    question = market.get('question', '未知盘口')
                    
                    return outcome_name, question
        except Exception:
            pass
        return None, None

    # 方案 A: 先试 event_slug (通常是大事件集合)
    res_out, res_quest = fetch_from_api(event_slug)
    if res_out: 
        return res_out, res_quest

    # 方案 B: 如果 A 失败，试 slug (通常是具体单一市场)
    res_out, res_quest = fetch_from_api(slug)
    if res_out: 
        return res_out, res_quest
        
    print("   ❌ 双重查询均失败")
    return None, None

def check_trades():
    print("🚀 正在启动 NBA 全盘口监控 (智能回溯版)...")
    
    # ⚠️ 测试配置：limit=100 (抓取最近100条)
    url = f"https://data-api.polymarket.com/activity?user={TARGET_ADDRESS}&limit=100"
    
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
    
    # ⚠️ 测试配置：回溯过去 24 小时 (60*60*24)
    # 正式运行时建议改为 60*60 (1小时) 或 60*10 (10分钟)
    check_window = 60 * 60 * 24 

    print(f"📊 获取到 {len(activities)} 条记录，正在分析...")

    for item in activities:
        try:
            # 1. 基础信息过滤
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
            # 时间检查
            if now - ts > check_window:
                continue

            # 2. 金额计算
            price = float(item.get('price', 0) or 0)
            size = float(item.get('size', 0) or 0)
            usdc_size = float(item.get('usdcSize', 0) or 0)
            value = float(item.get('value', 0) or 0)
            amount = value if value > 0 else (price * size if price * size > 0 else usdc_size)

            # =========================================
            # 🔥 智能解析逻辑 (核心)
            # =========================================
            raw_asset = str(item.get('asset', ''))      
            raw_outcome = str(item.get('outcome', ''))  
            
            # 判断是否存在 Token ID (纯数字且长度>5)
            token_id = None
            if raw_asset.isdigit() and len(raw_asset) > 5:
                token_id = raw_asset
            elif raw_outcome.isdigit() and len(raw_outcome) > 5:
                token_id = raw_outcome

            real_outcome = raw_outcome # 默认使用原始数据
            market_question = title    # 默认使用标题

            # 情况 A: 有 Token ID -> 强制查后台获取最准确的盘口详情
            if token_id:
                res_outcome, res_question = resolve_market_details(slug, event_slug, token_id)
                if res_outcome:
                    real_outcome = res_outcome
                    market_question = res_question # 这里的 question 通常包含 "Spread -2.5" 等细节
            
            # 情况 B: 无 Token ID (API直接给了名字) -> 尝试通过标题猜测类型
            else:
                # 如果没查到，保留原始标题，后续通过关键词识别 Tag
                pass

            # 兜底显示
            if not real_outcome or real_outcome == "解析中...":
                real_outcome = raw_outcome if raw_outcome else "未知选项"

            # 3. 构建盘口 Tag (Emoji 分类)
            market_tag = "🏀 胜负盘 (Moneyline)"
            # 将所有可能包含信息的文本拼在一起检查
            check_str = (market_question + " " + title + " " + slug).upper()
            
            if "SPREAD" in check_str or "HANDICAP" in check_str:
                market_tag = "⚖️ 让分盘 (Spread)"
            elif "TOTAL" in check_str or "OVER" in check_str or "UNDER" in check_str:
                market_tag = "🔢 大小分 (Total)"
            elif "QUARTER" in check_str:
                market_tag = "1️⃣ 单节 (Quarter)"
            elif "HALF" in check_str:
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
            print(f"✅ 已推送: {real_outcome} | {market_tag}")

        except Exception as e:
            print(f"处理单条数据出错: {e}")
            continue

    if found_count == 0:
        print("过去 24 小时内无 NBA 开单操作。")

if __name__ == "__main__":
    check_trades()
