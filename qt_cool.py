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

def send_tg_report(status, photo):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("MY_CHAT_ID")
    if not token or not chat_id: return
    now = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%H:%M:%S')
    try:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo, 'rb') as f:
            requests.post(url, data={'chat_id': chat_id, 'caption': f"📸 现场抓拍: {status}\n时间: {now}"}, files={'photo': f})
    except: pass

def run_checkin(sb):
    sk = os.environ.get("QTCOOL_SK")
    
    # 指纹深度抹除
    sb.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("[*] 正在载入晴辰云...")
    sb.open("https://gpt.qt.cool/checkin")
    sb.sleep(5)
    
    # 登录
    sb.type('#renewKey', sk)
    sb.click('button.renew')
    sb.sleep(8)
    
    # 点击签到
    print("[*] 触发签到验证码...")
    sb.click("#checkinBtn")
    sb.sleep(10) # 给极验充足的加载时间

    try:
        # 假设识别距离为 168 (请根据你的 Solver 实际调用)
        distance = 168 
        print(f"[*] 启动同步物理强攻滑动: {distance}px")
        
        # 核心：去异步化 JS 逻辑，确保 Python 阻塞等待
        js_sync_attack = f"""
        (function(dist) {{
            var btn = document.querySelector('div[class*="geetest_btn"]');
            var slice = document.querySelector('div[class*="geetest_slice_"]');
            if (!btn) return "BTN_NOT_FOUND";

            var rect = btn.getBoundingClientRect();
            var startX = rect.left + rect.width / 2;
            var startY = rect.top + rect.height / 2;

            function fire(type, cx) {{
                var e = new MouseEvent(type, {{
                    bubbles: true, cancelable: true, view: window,
                    clientX: cx, clientY: startY, buttons: 1
                }});
                btn.dispatchEvent(e);
            }}

            // 1. 按下
            fire('mousedown', startX);
            
            // 2. 同步滑动 (不再使用 await，利用 CPU 循环)
            var steps = 100; 
            for (var i = 1; i <= steps; i++) {{
                var progress = i / steps;
                var moveX = startX + (dist * (1 - Math.pow(1 - progress, 4)));
                var currentOffset = moveX - startX;

                // 强制同步修改 CSS Transform
                var transformStr = "translate(" + currentOffset + "px, 0px)";
                btn.style.setProperty("transform", transformStr, "important");
                if (slice) slice.style.setProperty("transform", transformStr, "important");

                fire('mousemove', moveX);
                
                // 极短的忙等，模拟滑动耗时 (约 1.5 秒总长)
                var start = Date.now();
                while (Date.now() - start < 15) {{}} 
            }}

            // 3. 释放
            fire('mouseup', startX + dist);
            return "SUCCESS_MOVED_" + dist + "px";
        }})({distance});
        """
        
        # 执行同步脚本
        result = sb.execute_script(js_sync_attack)
        print(f"[*] JS 动作反馈: {result}")
        
        # 滑完后立马截图
        print("[!] 动作结束，1秒后进行现场抓拍...")
        sb.sleep(1) 
        photo = "action_snap.png"
        sb.save_screenshot(photo)
        
        # 发送报告
        send_tg_report(result, photo)
        sb.sleep(10)

    except Exception as e:
        print(f"[*] 流程异常: {e}")
        sb.save_screenshot("error.png")

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
