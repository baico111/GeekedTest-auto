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
    print("[-] 警告: 未找到 geeked 模块")

CHECKIN_URL = "https://gpt.qt.cool/checkin"

def get_human_track(distance):
    track = []
    current = 0
    steps = random.randint(50, 70) # 进一步放慢速度
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
    
    # --- 抹除 WebDriver 特征 (防封核心) ---
    sb.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("[*] 正在载入晴辰云...")
    sb.open(CHECKIN_URL)
    sb.sleep(5)
    
    # 填入 SK 并登录
    sb.type('input#renewKey', sk)
    sb.click('button[onclick*="doRenewLogin"]')
    sb.sleep(5)
    
    # 处理算术题
    if sb.is_element_visible("#renewCaptchaQ"):
        q = sb.get_text("#renewCaptchaQ")
        nums = [int(n) for n in re.findall(r'\d+', q)]
        ans = (nums[0] - nums[1]) if "-" in q else (nums[0] + nums[1])
        sb.type("#renewCaptchaA", str(ans))
        sb.sleep(2)

    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    sb.sleep(8) # 强制多等一会儿，确保 iframe 加载
    
    print("[*] 正在穿透 iFrame 寻找滑块...")
    try:
        # 自动搜索所有 iframe 并寻找包含 geetest 关键字的内容
        iframes = sb.find_elements('iframe')
        found_frame = False
        for i, frame in enumerate(iframes):
            try:
                sb.switch_to_frame(frame)
                if sb.is_element_present('div[class*="geetest_canvas_img"]', timeout=2):
                    print(f"[+] 在第 {i+1} 个 iframe 中找到了滑块")
                    found_frame = True
                    break
                sb.switch_to_default_content()
            except:
                sb.switch_to_default_content()
                continue
        
        if not found_frame:
            # 如果没找到 iframe，尝试直接在主页面找 (有些版本不带 iframe)
            print("[*] 未在 iframe 发现目标，尝试直接在主页面查找...")

        # 定位并破解
        target_selector = 'div[class*="geetest_canvas_img"]'
        sb.wait_for_element_visible(target_selector, timeout=15)
        
        bg_style = sb.get_attribute('div[class*="geetest_canvas_img"]', 'style')
        slice_style = sb.get_attribute('div[class*="geetest_slice_bg"]', 'style')
        bg_url = re.search(r'url\("(.*?)"\)', bg_style).group(1)
        slice_url = re.search(r'url\("(.*?)"\)', slice_style).group(1)
        
        solver = SlideSolver(
            puzzle_piece=SlideSolver.load_image(slice_url),
            background=SlideSolver.load_image(bg_url)
        )
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别成功: {distance}px")
        
        slider_btn = sb.find_element('div[class*="slider_button"]')
        tracks = get_human_track(distance)
        
        ActionChains(sb.driver).click_and_hold(slider_btn).perform()
        for x in tracks:
            # 加入微小随机停顿，增加拟人度
            ActionChains(sb.driver).move_by_offset(x, random.choice([-1, 0, 1])).perform()
            if random.random() > 0.7: sb.sleep(0.01)
        
        sb.sleep(1)
        ActionChains(sb.driver).release().perform()
        print("[+] 滑动完成")
        
    except Exception as e:
        print(f"[*] 破解环节失败: {e}")
    finally:
        try:
            sb.switch_to_default_content()
        except:
            pass

    sb.sleep(10)
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "N/A"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    # 强制启用 UC 模式和禁用法制特征
    with SB(uc=True, test=True, ad_block=True, locale="zh_CN") as sb:
        run_checkin(sb)
