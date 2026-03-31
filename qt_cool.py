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

def run_checkin(sb):
    sk = os.environ.get("QTCOOL_SK")
    
    # 1. 深度隐藏：抹除所有自动化标记
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
        sb.click("#checkinBtn")
    
    print("[*] 正在捕获动态验证码...")
    sb.sleep(10) 
    
    try:
        # 提取图片位移
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
        
        # 2. 【核心】真·拟人滑动 JS 注入
        # 这段脚本在浏览器内部同步运行，不会导致连接断开
        print("[*] 注入人类行为算法...")
        js_human_move = f"""
        (async () => {{
            var btn = document.querySelector('div[class*="geetest_btn"]');
            var box = btn.getBoundingClientRect();
            var x = box.left + box.width / 2;
            var y = box.top + box.height / 2;
            
            // A. 按下：模拟手指接触，停留一小会儿
            btn.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true, clientX: x, clientY: y}}));
            await new Promise(r => setTimeout(r, {random.randint(150, 300)}));

            // B. 滑动：模拟肌肉反应，先快后慢，带抖动
            let targetX = x + {distance};
            let currentX = x;
            let steps = 80; 
            
            for(let i=1; i<=steps; i++) {{
                let t = i / steps;
                // 五次方缓动曲线 (Ease-Out)
                let moveX = x + ({distance} * (1 - Math.pow(1 - t, 5)));
                // 模拟手抖：Y轴微小随机偏移
                let moveY = y + (Math.random() * 2 - 1);
                
                btn.dispatchEvent(new MouseEvent('mousemove', {{
                    bubbles: true, 
                    clientX: moveX, 
                    clientY: moveY
                }}));
                
                // 模拟物理阻力：每几步停顿几毫秒
                if (i % 4 === 0) await new Promise(r => setTimeout(r, 10));
            }}
            
            // C. 确认：在终点微调对准，停留 0.5 秒
            await new Promise(r => setTimeout(r, 500));
            
            // D. 释放
            btn.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true, clientX: targetX, clientY: y}}));
        }})();
        """
        # 注意：这里我们不用普通的 execute_script，因为它会卡住等待 JS 完成
        # 我们让它异步执行，然后 Python 层同步等待
        sb.execute_script(js_human_move)
        
        # 3. 实时抓拍：在 JS 预计执行完的时间点抓拍
        print("[!] 动作进行中，3秒后抓拍...")
        sb.sleep(3) 
        sb.save_screenshot("action_result.png")
        
        sb.sleep(10) # 等待校验结果

    except Exception as e:
        print(f"[*] 异常: {e}")

    # 报告与截图发送
    photo = "action_result.png"
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
