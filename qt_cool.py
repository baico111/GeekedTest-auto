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
    # 距离 209px 较长，增加步数模拟真实加速感
    steps = random.randint(85, 110)
    for i in range(1, steps + 1):
        t = i / steps
        move = round(distance * (1 - math.pow(1 - t, 5)))
        track.append(move - current)
        current = move
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
    
    # 签到
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    print("[*] 正在捕获验证码...")
    sb.sleep(10) 
    
    try:
        # 1. 提取图片 (已验证成功的逻辑)
        js_get_imgs = """
        var bg = getComputedStyle(document.querySelector('div[class*="geetest_bg_"]')).backgroundImage;
        var slice = getComputedStyle(document.querySelector('div[class*="geetest_slice_bg_"]')).backgroundImage;
        return [bg, slice];
        """
        urls = sb.execute_script(js_get_imgs)
        bg_url = re.search(r'url\("?(.*?)"?\)', urls[0]).group(1)
        slice_url = re.search(r'url\("?(.*?)"?\)', urls[1]).group(1)

        print(f"[+] 图片抓取成功，计算距离...")
        bg_content = requests.get(bg_url, timeout=10).content
        slice_content = requests.get(slice_url, timeout=10).content
        
        solver = SlideSolver(slice_content, bg_content)
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别成功: {distance}px")
        
        # 2. 定位按钮 (增加稳定性处理)
        btn_selector = 'div[class*="geetest_btn"]'
        sb.wait_for_element_visible(btn_selector, timeout=15)
        
        # 获取原始的 WebDriver 元素对象，防止 SeleniumBase 包装类导致的兼容问题
        slider_btn = sb.driver.find_element("css selector", btn_selector)
        print(f"[+] 成功锁定底层按钮元素")

        # 3. 滑动动作
        tracks = get_human_track(distance)
        
        # 使用标准的 ActionChains 并直接作用于 driver
        actions = ActionChains(sb.driver, duration=0)
        actions.click_and_hold(slider_btn).perform()
        
        for x in tracks:
            # 模拟 X 轴位移和 Y 轴抖动
            actions.move_by_offset(x, random.choice([-1, 0, 1])).perform()
            # 极短的随机延迟，增加拟人度
            time.sleep(random.uniform(0.005, 0.015))
        
        time.sleep(0.8)
        actions.release().perform()
        print("[+] 滑动动作已释放，等待校验...")
        sb.sleep(12)

    except Exception as e:
        print(f"[*] 流程异常: {e}")
        sb.save_screenshot("debug_error.png")

    # 结果报告
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "N/A"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "Done"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
