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
        # 1. 提取图片并计算位移 (JS 穿透)
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
        print(f"[+] 识别成功，目标位移: {distance}px")
        
        # 2. 【核心突破】针对 Transform 属性的同步强攻逻辑
        # 我们不仅派发事件，还强行修改 style 里的 translate 属性，让它“不得不动”
        print("[*] 执行 CSS Transform 强力同步滑动...")
        
        js_transform_attack = f"""
        (function(dist) {{
            var btn = document.querySelector('div[class*="geetest_btn"]');
            var slice = document.querySelector('div[class*="geetest_slice_bg_"]');
            if (!btn || !slice) return "ELEMENT_NOT_FOUND";
            
            var rect = btn.getBoundingClientRect();
            var x = rect.left + rect.width / 2;
            var y = rect.top + rect.height / 2;

            function fire(type, cx) {{
                var e = new MouseEvent(type, {{
                    bubbles: true, cancelable: true, view: window,
                    clientX: cx, clientY: y, buttons: 1
                }});
                btn.dispatchEvent(e);
            }}

            // A. 按下
            fire('mousedown', x);
            
            // B. 强制同步滑动：每一步都强行改写 style
            var steps = 30;
            for(var i=0; i<=steps; i++) {{
                var currentDist = dist * (i / steps);
                var moveX = x + currentDist;
                
                // 核心：强行修改你截图中的那个 transform 属性
                btn.style.transform = "translate(" + currentDist + "px, 0px)";
                slice.style.transform = "translate(" + currentDist + "px, 0px)";
                
                fire('mousemove', moveX);
            }}
            
            // C. 释放
            fire('mouseup', x + dist);
            return "SUCCESS: Forced " + dist + "px";
        }})({distance});
        """
        
        res = sb.execute_script(js_transform_attack)
        print(f"[*] 强攻执行结果: {res}")
        
        # 3. 动作后秒截
        sb.sleep(1) 
        photo = "debug_action.png"
        sb.save_screenshot(photo)
        print(f"[+] 现场抓拍已保存: {photo}")
        
        sb.sleep(10)

    except Exception as e:
        print(f"[*] 流程异常: {e}")
        photo = "debug_error.png"
        sb.save_screenshot(photo)

    # 发送报告
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "N/A"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("MY_CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo, 'rb') as f:
            requests.post(url, data={'chat_id': chat_id, 'caption': f"👤 {status}\n📅 {expiry}", 'parse_mode': 'HTML'}, files={'photo': f})

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
