import os
import time
import datetime
import requests
import re
import random
import math
from seleniumbase import SB

# 保持原作者模块导入逻辑
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
    caption = f"📸 <b>Qt-Cool 调试报告</b>\n---\n👤 状态: {status}\n📅 到期: {expiry}\n🕒 时间: {now}"
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
    
    # 登录
    sb.type('input#renewKey', sk)
    sb.click('button[onclick*="doRenewLogin"]')
    sb.sleep(8)
    
    # 点击签到
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    print("[*] 正在捕获动态验证码...")
    sb.sleep(10) 
    
    try:
        # 1. 提取图片 (JS 穿透)
        js_get_imgs = """
        var bg = getComputedStyle(document.querySelector('div[class*="geetest_bg_"]')).backgroundImage;
        var slice = getComputedStyle(document.querySelector('div[class*="geetest_slice_bg_"]')).backgroundImage;
        return [bg, slice];
        """
        urls = sb.execute_script(js_get_imgs)
        bg_url = re.search(r'url\("?(.*?)"?\)', urls[0]).group(1)
        slice_url = re.search(r'url\("?(.*?)"?\)', urls[1]).group(1)

        bg_content = requests.get(bg_url, timeout=10).content
        slice_content = requests.get(slice_url, timeout=10).content
        
        solver = SlideSolver(slice_content, bg_content)
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别距离: {distance}px")
        
        # 2. 拟人化 JS 滑动指令
        print("[*] 正在执行 JS 动作并准备秒截...")
        js_slide_debug = f"""
        (async () => {{
            var btn = document.querySelector('div[class*="geetest_btn"]');
            var box = btn.getBoundingClientRect();
            var startX = box.left + box.width / 2;
            var startY = box.top + box.height / 2;
            
            btn.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true, clientX: startX, clientY: startY}}));
            await new Promise(r => setTimeout(r, {random.randint(100, 200)}));

            let steps = 60;
            for(let i=1; i<=steps; i++) {{
                let progress = i / steps;
                let moveX = startX + ({distance} * (1 - Math.pow(1 - progress, 5)));
                btn.dispatchEvent(new MouseEvent('mousemove', {{
                    bubbles: true, 
                    clientX: moveX, 
                    clientY: startY + (Math.random() * 2 - 1)
                }}));
                if (i % 2 === 0) await new Promise(r => setTimeout(r, 10));
            }}
            
            await new Promise(r => setTimeout(r, 200));
            btn.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true, clientX: startX + {distance}, clientY: startY}}));
        }})();
        """
        sb.execute_script(js_slide_debug)
        
        # --- 核心修改：滑动结束后立即截图 ---
        print("[!] 动作执行完毕，立即抓拍...")
        sb.sleep(0.5) # 极短缓冲，确保 mouseup 动作被浏览器处理完
        photo = "debug_action.png"
        sb.save_screenshot(photo)
        print(f"[+] 现场截图已保存: {photo}")
        
        # 接下来再等校验结果
        sb.sleep(10)

    except Exception as e:
        print(f"[*] 流程异常: {e}")
        photo = "debug_error.png"
        sb.save_screenshot(photo)

    # 结果抓取（最终报告）
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "Wait for check..."
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "Action Captured"
    
    # 发送刚才那张“秒截”的图
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
