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
    caption = f"📸 <b>Qt-Cool 现场抓拍报告</b>\n---\n👤 状态: {status}\n📅 到期: {expiry}\n🕒 时间: {now}"
    try:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo, 'rb') as f:
            requests.post(url, data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}, files={'photo': f}, timeout=15)
    except: pass

def run_checkin(sb):
    sk = os.environ.get("QTCOOL_SK")
    
    # 彻底抹除 WebDriver 特征，防止被识别为机器人
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
        print(f"[+] 识别成功，目标位移: {distance}px")
        
        # 2. 真人模拟滑动逻辑 (核心修改)
        # 我们不再使用 async/await，而是使用同步循环，确保 Python 在这一行执行完时，滑动已经完成
        print("[*] 正在模拟真人“按下-滑动-松开”过程...")
        js_human_action = f"""
        (function() {{
            var btn = document.querySelector('div[class*="geetest_btn"]');
            var box = btn.getBoundingClientRect();
            var startX = box.left + box.width / 2;
            var startY = box.top + box.height / 2;
            
            // A. 模拟鼠标按下
            btn.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true, clientX: startX, clientY: startY}}));
            
            let steps = 60;
            let targetX = startX + {distance};
            
            // B. 模拟滑动轨迹：采用五次方缓动曲线（先快后慢）
            for(let i=1; i<=steps; i++) {{
                let progress = i / steps;
                // 缓动算法：模拟人类接近终点时的减速对准动作
                let moveX = startX + ({distance} * (1 - Math.pow(1 - progress, 5)));
                // 模拟手抖：垂直方向随机产生 -1 到 1 像素的偏移
                let moveY = startY + (Math.random() * 2 - 1);
                
                btn.dispatchEvent(new MouseEvent('mousemove', {{
                    bubbles: true, 
                    clientX: moveX, 
                    clientY: moveY
                }}));
            }}
            
            // C. 模拟鼠标释放
            btn.dispatchEvent(new MouseEvent('mouseup', {{
                bubbles: true, 
                clientX: targetX, 
                clientY: startY
            }}));
        }})();
        """
        # 同步执行 JS，此时 Python 会阻塞在这里直到浏览器完成滑动
        sb.execute_script(js_human_action)
        
        # 3. 抓拍证据：滑动完立即等 1 秒（给浏览器渲染 UI 结果的时间）就截图
        print("[!] 动作已执行，1秒后进行现场抓拍...")
        sb.sleep(1) 
        photo = "debug_action.png"
        sb.save_screenshot(photo)
        print(f"[+] 现场截图已保存: {photo}")
        
        # 接下来再等 10 秒看校验结果（是否出现勾选或跳转）
        sb.sleep(10)

    except Exception as e:
        print(f"[*] 破解流程异常: {e}")
        photo = "debug_error.png"
        sb.save_screenshot(photo)

    # 最终状态检查
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "Wait result..."
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End of Action"
    
    # 将现场抓拍的图发送到 Telegram
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
