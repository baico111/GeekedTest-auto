import os
import time
import sys
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

def get_human_track(distance):
    track = []
    current = 0
    # 模拟真人的“先快后慢”轨迹
    steps = random.randint(55, 75)
    for i in range(1, steps + 1):
        t = i / steps
        move = round(distance * (1 - math.pow(1 - t, 3)))
        track.append(move - current)
        current = move
    # 停顿与回退
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
    
    # 强制抹除自动化指纹
    sb.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("[*] 正在载入晴辰云...")
    sb.open(CHECKIN_URL)
    sb.sleep(4)
    
    # 登录流程
    sb.type('input#renewKey', sk)
    sb.click('button[onclick*="doRenewLogin"]')
    sb.sleep(6)
    
    # 点击签到
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    print("[*] 正在捕获动态验证码容器...")
    sb.sleep(5)
    
    try:
        # --- 根据你的截图修改的定位逻辑 ---
        # 寻找当前可见的那个极验容器
        all_containers = sb.find_elements('div[class*="geetest_captcha"]')
        active_container = None
        for container in all_containers:
            if container.is_displayed():
                active_container = container
                break
        
        if not active_container:
            # 备选方案：通过 canvas 标签直接定位
            print("[*] 未找到显式容器，尝试直接定位 Canvas...")
            sb.wait_for_element_visible('canvas.geetest_canvas_bg', timeout=15)
        
        # 提取背景和滑块图片
        # 注意：使用 execute_script 抓取 computed style 最稳
        bg_url = sb.execute_script('return getComputedStyle(document.querySelector("div[class*=\'geetest_canvas_img\']")).backgroundImage').split('"')[1]
        slice_url = sb.execute_script('return getComputedStyle(document.querySelector("div[class*=\'geetest_slice_bg\']")).backgroundImage').split('"')[1]
        
        print(f"[+] 抓取图片成功，启动 OpenCV...")
        solver = SlideSolver(
            puzzle_piece=SlideSolver.load_image(slice_url),
            background=SlideSolver.load_image(bg_url)
        )
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别距离: {distance}px")
        
        # 定位滑动按钮
        slider_btn = sb.find_element('div[class*="slider_button"]')
        tracks = get_human_track(distance)
        
        ActionChains(sb.driver).click_and_hold(slider_btn).perform()
        for x in tracks:
            # 模拟人手抖动，增加随机微小位移
            ActionChains(sb.driver).move_by_offset(x, random.uniform(-1, 1)).perform()
            time.sleep(random.uniform(0.005, 0.015))
        
        sb.sleep(1)
        ActionChains(sb.driver).release().perform()
        print("[+] 滑动动作已完成")
        sb.sleep(8)

    except Exception as e:
        print(f"[*] 破解失败详情: {e}")

    # 结果截图与发送
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "Unknown"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "Finished"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
