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
    
    # 彻底抹除 WebDriver 指纹
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
        # 1. 提取图片并计算距离 (JS 穿透)
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
        print(f"[+] 识别成功，位移: {distance}px")
        
        # 2. 获取按钮的绝对坐标
        print("[*] 正在获取物理坐标...")
        location = sb.get_element('div[class*="geetest_btn"]').location
        size = sb.get_element('div[class*="geetest_btn"]').size
        
        # 计算中心点
        x = location['x'] + size['width'] / 2
        y = location['y'] + size['height'] / 2
        
        # 3. 核心突破：直接调用 CDP 指令模拟最底层物理动作
        print("[*] 正在通过 CDP 模拟物理按压与滑动...")
        
        # 按下鼠标
        sb.execute_cdp_cmd("Input.dispatchMouseEvent", {
            "type": "mousePressed", "button": "left", "x": x, "y": y, "clickCount": 1
        })
        
        # 拟人化滑动：分步发送物理坐标
        steps = 50
        for i in range(1, steps + 1):
            progress = i / steps
            # 五次方缓动曲线
            move_x = x + (distance * (1 - math.pow(1 - progress, 5)))
            move_y = y + random.uniform(-1, 1)
            
            sb.execute_cdp_cmd("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": move_x, "y": move_y
            })
            # 每步微小的物理延迟
            time.sleep(random.uniform(0.01, 0.02))
            
        # 释放鼠标
        sb.execute_cdp_cmd("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "button": "left", "x": x + distance, "y": y, "clickCount": 1
        })
        
        # 动作执行完后即刻抓拍
        print("[!] 物理指令已下发，立即抓拍现场...")
        sb.sleep(1) 
        photo = "debug_final.png"
        sb.save_screenshot(photo)
        print(f"[+] 现场截图已保存: {photo}")
        
        sb.sleep(12)

    except Exception as e:
        print(f"[*] 破解异常: {e}")
        photo = "debug_error.png"
        sb.save_screenshot(photo)

    # 结果状态
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "N/A"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
