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
    print("正在启动 CLOB 引擎监控...")
    
    # 🔥 修正点：使用官方 CLOB 接口
    # 域名是 clob.polymarket.com，路径是 /data/trades
    url = f"https://clob.polymarket.com/data/trades?taker_address={TARGET_ADDRESS}&limit=20"
    
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url, timeout=15)
        
        # 打印状态码，方便调试
        if response.status_code != 200:
            print(f"接口报错 (CLOB): {response.status_code}")
            # 如果 CLOB 也不行，可能是 Cloudflare 拦截，我们打印出来
            print(f"错误信息: {response.text[:100]}")
            return
            
        trades = response.json()
        # CLOB 接口有时候返回的是个列表，有时候在大字典里，这里做个兼容
        if isinstance(trades, dict) and 'data' in trades:
            trades = trades['data']
            
    except Exception as e:
        print(f"连接报错: {e}")
        return

    # 获取当前时间
    now = time.time()
    found_count = 0
    check_window = 60 * 60 # 60分钟

    print(f"✅ CLOB 连接成功！获取到 {len(trades)} 条成交记录，开始分析...")

    for item in trades:
        try:
            # 1. 筛选买入 (BUY)
            # CLOB 接口里，买入通常 side = 'BUY'
            if item.get('side') != 'BUY':
                continue
            
            # 2. 时间处理 (CLOB 返回的是 13 位毫秒时间戳)
            ts = int(item.get('timestamp', 0))
            if ts > 9999999999:
                ts = ts / 1000
            
            if now - ts > check_window:
                continue

            # 3. 获取信息
            price = float(item.get('price', 0) or 0)
            size = float(item.get('size', 0) or 0)
            amount = price * size
            
            # CLOB 接口返回的是 asset_id (资产ID)，不是人话 slug
            # 但是！我们可以把 asset_id 显示出来，你点链接去看
            asset_id = item.get('asset_id', 'Unknown')
            
            time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
            
            # 4. 发送通知
            # 因为 CLOB 也是机器码，我们这里无法过滤 "NBA" 字样
            # 策略：只要有买入，就先推给你，你点链接确认
            # (为了不让你被骚扰，我们只推金额大于 10U 的)
            if amount > 10:
                msg = (
                    f"🚨 **监控到新买入! (CLOB)**\n\n"
                    f"💰 **金额**: ${amount:,.0f} USD\n"
                    f"🎯 **价格**: ${price:.2f}\n"
                    f"⌚ **时间**: {time_str}\n"
                    f"🔗 [👉 点击查看详情](https://polymarket.com/profile/{TARGET_ADDRESS})"
                )
                send_telegram_message(msg)
                found_count += 1
                print(f"✅ 已推送: ${amount}")

        except Exception as e:
            print(f"处理单条数据出错: {e}")
            continue

    if found_count == 0:
        print("过去 60 分钟内无有效买入。")

if __name__ == "__main__":
    check_trades()
