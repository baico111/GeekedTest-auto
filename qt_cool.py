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
    # 模拟真人的“先快后慢”轨迹
    steps = random.randint(75, 95)
    for i in range(1, steps + 1):
        t = i / steps
        move = round(distance * (1 - math.pow(1 - t, 4)))
        track.append(move - current)
        current = move
    # 终点微调抖动
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
        requests.post(url, data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}, files={'photo': open(photo, 'rb')}, timeout=15)
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
    sb.sleep(10)
    
    # 点击签到
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    print("[*] 正在捕获动态验证码...")
    sb.sleep(8) 
    
    try:
        # --- 这里的逻辑是根据你的截图量身定制的 ---
        # 我们寻找任何包含 geetest 字样且可见的 div 或 canvas
        print("[*] 正在利用通配符定位元素...")
        
        # 1. 寻找背景图 URL (利用通配符查找包含 geetest 的 div，并取其计算样式)
        # 极验4.0 必定会请求包含 gcaptcha4 的图片地址
        js_capture = """
        function findGtUrl(keyword) {
            var els = document.querySelectorAll('div[class*="geetest_"], canvas[class*="geetest_"]');
            for (var el of els) {
                var style = getComputedStyle(el).backgroundImage;
                if (style.includes(keyword)) return style.match(/url\\(["']?(.*?)["']?\\)/)[1];
            }
            return null;
        }
        return [findGtUrl('bg'), findGtUrl('slice')];
        """
        urls = sb.execute_script(js_capture)
        bg_url, slice_url = urls[0], urls[1]

        if not bg_url:
            # 备选方案：如果 style 里没有，尝试直接从 canvas 抓取 (有些版本是直接画上去的)
            print("[*] 无法从样式提取 URL，尝试截图定位...")
            # 这里如果不成功，下面的 solver 会报错，我们加个保险
            if not sb.is_element_present('canvas[class*="geetest_"]'):
                 raise Exception("未找到极验相关 Canvas 元素")

        print(f"[+] 提取成功！背景图: {bg_url[:50]}...")
        
        # 2. 下载并解算
        bg_content = requests.get(bg_url).content
        slice_content = requests.get(slice_url).content
        
        solver = SlideSolver(slice_content, bg_content)
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别成功，距离: {distance}px")
        
        # 3. 定位滑动按钮 (利用包含 slider 关键字的模糊匹配)
        slider_btn = sb.find_element('div[class*="geetest_slider"]')
        
        # 4. 滑动
        tracks = get_human_track(distance)
        ActionChains(sb.driver).click_and_hold(slider_btn).perform()
        for x in tracks:
            # 模拟人手抖动 (Y轴随机位移)
            ActionChains(sb.driver).move_by_offset(x, random.uniform(-1, 1)).perform()
            time.sleep(random.uniform(0.008, 0.015))
        
        sb.sleep(1)
        ActionChains(sb.driver).release().perform()
        print("[+] 滑动结束")
        sb.sleep(8)

    except Exception as e:
        print(f"[*] 最终破解失败: {e}")
        sb.save_screenshot("debug.png")

    # 结果抓取
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "N/A"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
