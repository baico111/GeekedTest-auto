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
    caption = f"📸 <b>Qt-Cool 物理强攻报告</b>\n---\n👤 状态: {status}\n📅 到期: {expiry}\n🕒 时间: {now}"
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
    
    print("[*] 正在等待验证码加载...")
    sb.sleep(10) 
    
    try:
        # 1. 提取图片并计算位移
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
        
        # 2. 【核心修复】参考 bot-hosting 的物理派发逻辑
        # 我们直接把按钮对象传给 JS，在 JS 内部完成位置锁定和滑动
        print("[*] 正在执行 Canvas 物理层级强攻...")
        
        js_physical_drag = f"""
        (function(distance) {{
            var btn = document.querySelector('div[class*="geetest_btn"]');
            if (!btn) return "BUTTON_NOT_FOUND";
            
            var rect = btn.getBoundingClientRect();
            var sx = rect.left + rect.width / 2;
            var sy = rect.top + rect.height / 2;
            var ex = sx + distance;

            function fire(type, x, y) {{
                var e = new MouseEvent(type, {{
                    bubbles: true, cancelable: true, view: window,
                    clientX: x, clientY: y, buttons: 1
                }});
                btn.dispatchEvent(e);
            }}

            // 执行物理三段式滑动
            fire('mousedown', sx, sy);
            
            // 模拟分段平滑移动（参考你提供的代码逻辑）
            setTimeout(function() {{
                fire('mousemove', (sx + ex) / 2, sy + (Math.random() * 4 - 2));
                setTimeout(function() {{
                    fire('mousemove', ex, sy);
                    setTimeout(function() {{
                        fire('mouseup', ex, sy);
                    }}, 200);
                }}, 150);
            }}, 150);
            
            return "SUCCESS: Dragged " + distance + "px";
        }})({distance});
        """
        
        result = sb.execute_script(js_physical_drag)
        print(f"[*] JS 执行反馈: {result}")
        
        # 动作执行完后即刻抓拍（秒截）
        sb.sleep(1) 
        photo = "debug_action.png"
        sb.save_screenshot(photo)
        print(f"[+] 现场抓拍已保存: {photo}")
        
        sb.sleep(10)

    except Exception as e:
        print(f"[*] 流程异常: {e}")
        photo = "debug_error.png"
        sb.save_screenshot(photo)

    # 最终报告
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "Wait..."
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
