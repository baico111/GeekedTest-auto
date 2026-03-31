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

def get_human_track(distance):
    track = []
    current = 0
    # 模拟真人滑动，步数控制在 80-100
    steps = random.randint(80, 100)
    for i in range(1, steps + 1):
        t = i / steps
        # 五次方曲线：开始快，后面极慢对准
        move = round(distance * (1 - math.pow(1 - t, 5)))
        track.append(move - current)
        current = move
    # 终点微调
    track.extend([1, 0, -1, 0]) 
    return track

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
    from selenium.webdriver.common.action_chains import ActionChains
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
    
    # 签到
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    print("[*] 正在捕获验证码...")
    sb.sleep(10) 
    
    try:
        # 1. 提取图片 (使用模糊匹配 + JS 强取)
        # 根据你的截图，类名包含 geetest_bg_ 和 geetest_slice_bg_
        js_get_imgs = """
        var bg = getComputedStyle(document.querySelector('div[class*="geetest_bg_"]')).backgroundImage;
        var slice = getComputedStyle(document.querySelector('div[class*="geetest_slice_bg_"]')).backgroundImage;
        return [bg, slice];
        """
        urls = sb.execute_script(js_get_imgs)
        bg_url = re.search(r'url\("?(.*?)"?\)', urls[0]).group(1)
        slice_url = re.search(r'url\("?(.*?)"?\)', urls[1]).group(1)

        print(f"[+] 图片抓取成功，准备计算...")
        bg_content = requests.get(bg_url, timeout=10).content
        slice_content = requests.get(slice_url, timeout=10).content
        
        solver = SlideSolver(slice_content, bg_content)
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别成功，计算距离: {distance}px")
        
        # 2. 定位滑动按钮 (根据你截图中的 geetest_btn 关键类名)
        btn_selectors = [
            'div[class*="geetest_btn"]', # 你的截图明确显示了这个类名
            'div[class*="slider_button"]',
            '.geetest_slider_button'
        ]
        
        slider_btn = None
        for sel in btn_selectors:
            if sb.is_element_present(sel):
                slider_btn = sb.find_element(sel)
                print(f"[+] 成功锁定按钮: {sel}")
                break
        
        if not slider_btn:
            raise Exception("无法定位滑动按钮")

        # 3. 滑动动作 (ActionChains)
        tracks = get_human_track(distance)
        ActionChains(sb.driver).click_and_hold(slider_btn).perform()
        
        for x in tracks:
            # 必须加入 Y 轴随机偏移，模拟真人手抖
            y_offset = random.choice([-1, 0, 1]) if random.random() > 0.8 else 0
            ActionChains(sb.driver).move_by_offset(x, y_offset).perform()
            time.sleep(random.uniform(0.01, 0.02))
        
        sb.sleep(1)
        ActionChains(sb.driver).release().perform()
        print("[+] 滑动流程结束")
        sb.sleep(12)

    except Exception as e:
        print(f"[*] 流程异常: {e}")
        sb.save_screenshot("debug_final.png")

    # 报告发送
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "N/A"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
