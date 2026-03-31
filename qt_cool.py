import os
import time
import datetime
import requests
import re
import random
import math
from seleniumbase import SB

# 保持原作者模块导入
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
    caption = f"✅ <b>Qt-Cool 穿透强攻报告</b>\n---\n👤 状态: {status}\n📅 到期: {expiry}\n🕒 时间: {now}"
    try:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo, 'rb') as f:
            requests.post(url, data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}, files={'photo': f}, timeout=15)
    except: pass

def run_checkin(sb):
    sk = os.environ.get("QTCOOL_SK")
    
    # 指纹抹除
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
        # 1. 提取图片并计算距离
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
        
        # 2. 【核心修复】针对你截图中的 Canvas 架构进行物理穿透
        # 我们寻找类名包含 geetest_btn 的 div，但在其内部进行坐标派发
        print("[*] 正在执行 Canvas 物理穿透滑动...")
        
        js_canvas_drag = f"""
        (async () => {{
            var slider = document.querySelector('div[class*="geetest_btn"]');
            var canvas = document.querySelector('canvas[class*="geetest_slice_"]'); // 穿透到 Canvas
            if (!slider || !canvas) return "ELEMENT_NOT_FOUND";
            
            var rect = slider.getBoundingClientRect();
            var x = rect.left + rect.width / 2;
            var y = rect.top + rect.height / 2;
            var targetX = x + {distance};

            // 派发按下事件到 Canvas 层
            var mousedown = new MouseEvent('mousedown', {{ bubbles: true, clientX: x, clientY: y, buttons: 1 }});
            slider.dispatchEvent(mousedown); 

            // 模拟 50 步物理滑动
            let steps = 50;
            for(let i=1; i<=steps; i++) {{
                let t = i / steps;
                let moveX = x + ({distance} * (1 - Math.pow(1 - t, 4)));
                let moveY = y + (Math.random() * 2 - 1);
                
                var mousemove = new MouseEvent('mousemove', {{
                    bubbles: true, 
                    clientX: moveX, 
                    clientY: moveY,
                    buttons: 1
                }});
                slider.dispatchEvent(mousemove);
                // 必须微量延迟，让渲染引擎有时间反应
                if (i % 2 === 0) await new Promise(r => setTimeout(r, 10));
            }}
            
            // 停顿对准
            await new Promise(r => setTimeout(r, 200));
            
            // 派发释放
            var mouseup = new MouseEvent('mouseup', {{ bubbles: true, clientX: targetX, clientY: y }});
            slider.dispatchEvent(mouseup);
            
            return "SUCCESS: Dragged " + {distance} + "px";
        }})();
        """
        
        # 使用 execute_script 执行这个异步穿透脚本
        sb.execute_script(js_canvas_drag)
        
        # 3. 动作后立即抓拍证据
        print("[!] 指令已穿透下发，1.5秒后抓拍...")
        sb.sleep(1.5) 
        photo = "debug_action.png"
        sb.save_screenshot(photo)
        print(f"[+] 现场截图已保存: {photo}")
        
        sb.sleep(10)

    except Exception as e:
        print(f"[*] 流程异常: {e}")
        photo = "debug_error.png"
        sb.save_screenshot(photo)

    # 结果获取
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "N/A"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
