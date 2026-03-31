import os
import time
import re
import requests
from seleniumbase import SB

def run_checkin(sb):
    sk = os.environ.get("QTCOOL_SK")
    
    # 彻底抹除 WebDriver 特征
    sb.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("[*] 正在载入晴辰云...")
    sb.open("https://gpt.qt.cool/checkin")
    sb.sleep(5)
    
    # 登录
    sb.type('input#renewKey', sk)
    sb.click('button[onclick*="doRenewLogin"]')
    sb.sleep(8)
    
    # 点击签到
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    print("[*] 等待验证码弹出...")
    sb.sleep(8) 
    
    try:
        # --- 核心调试逻辑：物理层级暴力同步移动 ---
        # 我们寻找你提供的 geetest_btn，并强行让它位移 50 像素
        print("[!] 正在尝试点击并小幅度位移...")
        
        js_force_move = """
        (function() {
            var btn = document.querySelector('div[class*="geetest_btn"]');
            var slice = document.querySelector('div[class*="geetest_slice_"]');
            if (!btn) return "NOT_FOUND";
            
            var rect = btn.getBoundingClientRect();
            var x = rect.left + rect.width / 2;
            var y = rect.top + rect.height / 2;
            
            // 1. 模拟物理按下
            btn.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, clientX: x, clientY: y, buttons: 1}));
            
            // 2. 强行修改 CSS Transform 使其在视觉上产生 50px 位移
            var offset = 50;
            var moveX = x + offset;
            
            btn.style.transform = "translate(" + offset + "px, 0px)";
            if(slice) slice.style.transform = "translate(" + offset + "px, 0px)";
            
            // 3. 模拟物理移动
            btn.dispatchEvent(new MouseEvent('mousemove', {bubbles: true, clientX: moveX, clientY: y, buttons: 1}));
            
            // 4. 立即释放
            btn.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, clientX: moveX, clientY: y}));
            
            return "DONE_MOVE_50PX";
        })();
        """
        
        result = sb.execute_script(js_force_move)
        print(f"[*] JS 动作反馈: {result}")
        
        # --- 关键：动作完成后立即截图，不留任何喘息机会 ---
        sb.sleep(0.1) 
        photo = "action_snap.png"
        sb.save_screenshot(photo)
        print(f"[+] 动作快照已保存: {photo}")

    except Exception as e:
        print(f"[*] 调试异常: {e}")
        sb.save_screenshot("debug_error.png")

    # 发送截图到 TG
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("MY_CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo, 'rb') as f:
            requests.post(url, data={'chat_id': chat_id, 'caption': f"📸 动作抓拍测试\n结果: {result}"}, files={'photo': f})

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
