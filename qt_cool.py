import os
import time
import sys
import datetime
import requests
import re
import random
import math
from seleniumbase import SB

# 严格保持原作者模块导入
try:
    from geeked.slide import SlideSolver
except ImportError:
    print("[-] 警告: 未找到 geeked 模块")

CHECKIN_URL = "https://gpt.qt.cool/checkin"

def get_human_track(distance):
    track = []
    current = 0
    steps = random.randint(60, 80) # 进一步放慢，模拟精细对准
    for i in range(1, steps + 1):
        t = i / steps
        move = round(distance * (1 - math.pow(1 - t, 3)))
        track.append(move - current)
        current = move
    track.extend([1, 0, -1]) 
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
    
    # 抹除自动化特征
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
    
    print("[*] 正在捕获动态验证码容器...")
    sb.sleep(6)
    
    try:
        # 定位滑块图片元素
        bg_element = 'div[class*="geetest_canvas_img"]'
        slice_element = 'div[class*="geetest_slice_bg"]'
        
        sb.wait_for_element_visible(bg_element, timeout=15)
        
        # 提取 URL 的保险逻辑
        def get_url(selector):
            style = sb.get_attribute(selector, "style")
            match = re.search(r'url\("?(.*?)"?\)', style)
            return match.group(1) if match else None

        bg_url = get_url(bg_element)
        slice_url = get_url(slice_element)

        if not bg_url or not slice_url:
            raise Exception("无法提取验证码图片 URL")

        print(f"[+] 抓取图片成功: {bg_url[:50]}...")
        
        # 下载图片内容
        bg_content = requests.get(bg_url).content
        slice_content = requests.get(slice_url).content
        
        # 正确调用原作者的 SlideSolver
        # 注意：这里直接传入图片二进制内容，由 SlideSolver 内部处理
        solver = SlideSolver(slice_content, bg_content)
        distance = solver.find_puzzle_piece_position()
        
        print(f"[+] 识别距离: {distance}px")
        
        # 执行滑动
        slider_btn = sb.find_element('div[class*="slider_button"]')
        tracks = get_human_track(distance)
        
        ActionChains(sb.driver).click_and_hold(slider_btn).perform()
        for x in tracks:
            ActionChains(sb.driver).move_by_offset(x, random.choice([-1, 0, 1])).perform()
            time.sleep(random.uniform(0.01, 0.02))
        
        sb.sleep(1)
        ActionChains(sb.driver).release().perform()
        print("[+] 滑动动作已完成")
        sb.sleep(10)

    except Exception as e:
        print(f"[*] 破解失败详情: {e}")

    # 截图报告
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "Unknown"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
