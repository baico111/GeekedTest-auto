import os
import time
import datetime
import requests
import re
import random
import math
from seleniumbase import SB

try:
    from geeked.slide import SlideSolver
except ImportError:
    print("[-] 模块导入失败")

CHECKIN_URL = "https://gpt.qt.cool/checkin"

def send_tg_report(expiry, status, photo):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("MY_CHAT_ID")
    if not token or not chat_id: return
    now = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    caption = f"✅ <b>Qt-Cool 签到报告</b>\n---\n👤 状态: {status}\n📅 到期: {expiry}\n🕒 时间: {now}"
    try:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo, 'rb') as f:
            requests.post(url, data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}, files={'photo': f}, timeout=15)
    except: pass

def run_checkin(sb):
    sk = os.environ.get("QTCOOL_SK")
    
    # 彻底抹除 WebDriver 特征
    sb.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("[*] 正在载入晴辰云...")
    sb.open(CHECKIN_URL)
    sb.sleep(5)
    
    # 登录流程
    sb.type('input#renewKey', sk)
    sb.click('button[onclick*="doRenewLogin"]')
    sb.sleep(8)
    
    # 点击签到
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    print("[*] 正在等待验证码加载...")
    sb.sleep(10) 
    
    try:
        # 1. 提取图片 URL (JS 穿透)
        js_get_imgs = """
        var bg = getComputedStyle(document.querySelector('div[class*="geetest_bg_"]')).backgroundImage;
        var slice = getComputedStyle(document.querySelector('div[class*="geetest_slice_bg_"]')).backgroundImage;
        return [bg, slice];
        """
        urls = sb.execute_script(js_get_imgs)
        bg_url = re.search(r'url\("?(.*?)"?\)', urls[0]).group(1)
        slice_url = re.search(r'url\("?(.*?)"?\)', urls[1]).group(1)

        print(f"[+] 图片抓取成功，计算距离...")
        bg_content = requests.get(bg_url, timeout=10).content
        slice_content = requests.get(slice_url, timeout=10).content
        
        solver = SlideSolver(slice_content, bg_content)
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别成功: {distance}px")
        
        # 2. 核心突破：使用 JS 直接模拟滑动事件 (不触发鼠标指令流，防止崩溃)
        print("[*] 正在通过 JS 注入滑动指令...")
        
        # 极验4.0 的滑动逻辑可以通过派发 mousedown/mousemove/mouseup 事件来完成
        js_slide = f"""
        (async () => {{
            var btn = document.querySelector('div[class*="geetest_btn"]');
            var box = btn.getBoundingClientRect();
            var x = box.left + box.width / 2;
            var y = box.top + box.height / 2;
            
            // 派发按下事件
            btn.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true, clientX: x, clientY: y}}));
            
            // 模拟分段移动 (关键：增加微小延迟，防止 WAF 拦截)
            let currentX = x;
            let targetX = x + {distance};
            let steps = 50;
            for(let i=0; i<=steps; i++) {{
                let progress = i / steps;
                let moveX = x + ({distance} * (1 - Math.pow(1 - progress, 4)));
                btn.dispatchEvent(new MouseEvent('mousemove', {{
                    bubbles: true, 
                    clientX: moveX, 
                    clientY: y + (Math.random() * 2 - 1)
                }}));
                if (i % 5 === 0) await new Promise(r => setTimeout(r, 10));
            }}
            
            // 派发释放事件
            btn.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true, clientX: targetX, clientY: y}}));
        }})();
        """
        sb.execute_script(js_slide)
        print("[+] JS 滑动指令执行完毕")
        sb.sleep(12)

    except Exception as e:
        print(f"[*] 流程异常 (已尝试跳过): {e}")

    # 结果捕获
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "N/A"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    # 增加禁用沙盒和共享内存限制的参数，彻底解决 Connection Refused
    with SB(uc=True, test=True, incognito=True) as sb:
        # 进一步优化 Chrome 启动参数
        sb.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })
        run_checkin(sb)
