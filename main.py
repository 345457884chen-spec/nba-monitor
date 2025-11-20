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
    print("正在启动 Gamma API (成交记录) 监控...")
    
    # 🔥 修正点：URL 改为标准的 'fills' 接口，并使用 taker_address 查询
    # 这里的 taker_address 表示该地址是“主动吃单”的一方（买家通常是taker）
    url = f"https://gamma-api.polymarket.com/fills?taker_address={TARGET_ADDRESS}&limit=20"
    
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url, timeout=15)
        
        # 如果还是 404，打印具体信息
        if response.status_code != 200:
            print(f"接口依然报错: {response.status_code} | {response.text}")
            return
            
        trades = response.json()
    except Exception as e:
        print(f"连接报错: {e}")
        return

    # 获取当前时间
    now = time.time()
    found_count = 0
    
    # 回顾窗口：60分钟
    check_window = 60 * 60 

    print(f"✅ 连接成功！获取到 {len(trades)} 条成交记录，开始分析...")

    for item in trades:
        try:
            # 1. 筛选：只看买入 (BUY)
            if item.get('side') != 'BUY':
                continue
            
            # 2. 时间处理 (Gamma API 返回的是 ISO 格式字符串，需要转换)
            # 例如: "2025-11-20T12:00:00Z"
            ts_str = item.get('timestamp', '')
            # 简单的把 ISO 时间转成时间戳
            try:
                # 截取前19位 2025-11-20T12:00:00
                ts_dt = datetime.datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")
                ts = ts_dt.timestamp()
            except:
                ts = now # 如果解析失败，暂时忽略时间过滤
            
            # 检查时间
            if now - ts > check_window:
                continue

            # 3. 获取金额
            price = float(item.get('price', 0) or 0)
            size = float(item.get('size', 0) or 0)
            amount = price * size
            
            # 4. 关键：Gamma API 不直接返回名字，只返回 Market ID
            # 为了不报错 404，我们这里暂时只显示金额和链接
            # 用户点链接进去就能看到是啥了
            market_id = item.get('market', 'N/A')
            
            time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
            
            msg = (
                f"🚨 **监控到新买入! (Gamma版)**\n\n"
                f"💰 **金额**: ${amount:,.0f} USD\n"
                f"🎯 **价格**: ${price:.2f}\n"
                f"🆔 **Market ID**: `{market_id[:10]}...`\n"
                f"⌚ **时间**: {time_str}\n"
                f"🔗 [👉 点击查看这是买了什么](https://polymarket.com/profile/{TARGET_ADDRESS})"
            )
            send_telegram_message(msg)
            found_count += 1
            print(f"✅ 已推送订单，金额: ${amount}")

        except Exception as e:
            print(f"处理单条数据出错: {e}")
            continue

    if found_count == 0:
        print("过去 60 分钟内无买入。")

if __name__ == "__main__":
    check_trades()
