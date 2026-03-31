import os
import time
import sys
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
    steps = random.randint(70, 90) # 极慢滑动，欺骗高强度检测
    for i in range(1, steps + 1):
        t = i / steps
        move = round(distance * (1 - math.pow(1 - t, 4))) # 更平滑的曲线
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
    
    # 核心：彻底屏蔽 Webdriver 检测
    sb.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("[*] 正在载入晴辰云...")
    sb.open(CHECKIN_URL)
    sb.sleep(5)
    
    # 登录
    sb.type('input#renewKey', sk)
    sb.click('button[onclick*="doRenewLogin"]')
    sb.sleep(10) # 增加登录后的缓冲
    
    # 点击签到
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    print("[*] 正在捕获动态验证码容器...")
    sb.sleep(8) # 强制等待验证码生成
    
    try:
        # 1. 暴力等待：只要 DOM 里出现了这个元素（即使还没显示），我们就动手
        target_bg = 'div[class*="geetest_canvas_img"]'
        sb.wait_for_element_present(target_bg, timeout=30) 
        
        # 2. 强力提取：利用 JS 直接从 Computed Style 提取，无视 CSS 隐藏
        js_get_bg = 'return getComputedStyle(document.querySelector("div[class*=\'geetest_canvas_img\']")).backgroundImage'
        js_get_slice = 'return getComputedStyle(document.querySelector("div[class*=\'geetest_slice_bg\']")).backgroundImage'
        
        raw_bg = sb.execute_script(js_get_bg)
        raw_slice = sb.execute_script(js_get_slice)
        
        # 清洗 URL
        bg_url = re.search(r'url\("?(.*?)"?\)', raw_bg).group(1)
        slice_url = re.search(r'url\("?(.*?)"?\)', raw_slice).group(1)

        print(f"[+] 强力提取成功: {bg_url[:60]}...")
        
        # 3. 下载并识别
        bg_content = requests.get(bg_url, timeout=10).content
        slice_content = requests.get(slice_url, timeout=10).content
        
        solver = SlideSolver(slice_content, bg_content)
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别距离: {distance}px")
        
        # 4. 定位滑动按钮并执行
        # 如果按钮不可见，强制用 JS 让它显示出来，防止 ActionChains 报错
        sb.execute_script('document.querySelector("div[class*=\'slider_button\']").style.visibility = "visible"')
        slider_btn = sb.find_element('div[class*="slider_button"]')
        
        tracks = get_human_track(distance)
        ActionChains(sb.driver).click_and_hold(slider_btn).perform()
        for x in tracks:
            ActionChains(sb.driver).move_by_offset(x, random.choice([-1, 0, 1])).perform()
            time.sleep(random.uniform(0.01, 0.02))
        
        sb.sleep(1)
        ActionChains(sb.driver).release().perform()
        print("[+] 滑动动作已完成")
        sb.sleep(12)

    except Exception as e:
        print(f"[*] 破解环节异常: {e}")

    # 最终报告
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "N/A"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "Process End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    # 使用增强版 UC 模式
    with SB(uc=True, test=True, ad_block=True, locale="zh_CN") as sb:
        run_checkin(sb)
