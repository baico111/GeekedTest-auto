import os
import time
import datetime
import requests
import re
import random
import math
from seleniumbase import SB

# --- 导入原作者的解算模块 ---
try:
    from geeked.slide import SlideSolver
except ImportError:
    print("[-] 模块导入失败")

CHECKIN_URL = "https://gpt.qt.cool/checkin"

def get_human_track(distance):
    track = []
    current = 0
    # 模拟真人的“先快后慢”轨迹，步数多更拟人
    steps = random.randint(75, 95)
    for i in range(1, steps + 1):
        t = i / steps
        move = round(distance * (1 - math.pow(1 - t, 4)))
        track.append(move - current)
        current = move
    # 终点抖动微调
    track.extend([1, 1, 0, -1, -1]) 
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
    
    # 指纹抹除 (保持)
    sb.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("[*] 正在载入晴辰云...")
    sb.open(CHECKIN_URL)
    sb.sleep(5)
    
    # 登录 (保持原功能)
    sb.type('input#renewKey', sk)
    sb.click('button[onclick*="doRenewLogin"]')
    sb.sleep(8)
    
    # 处理可能的算术题 (保持原功能)
    if sb.is_element_visible("#renewCaptchaQ"):
        q = sb.get_text("#renewCaptchaQ")
        nums = [int(n) for n in re.findall(r'\d+', q)]
        ans = (nums[0] - nums[1]) if "-" in q else (nums[0] + nums[1])
        sb.type("#renewCaptchaA", str(ans))
        sb.sleep(2)

    # 点击签到
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    print("[*] 正在捕获验证码 (使用模糊定位)...")
    sb.sleep(8) 
    
    try:
        # --- 这里的逻辑是根据你的截图量身定制的 ---
        # 利用 CSS 的属性通配符（*=）来匹配包含关键词的动态类名
        bg_element = 'div[class*="geetest_bg_"]'
        slice_element = 'div[class*="geetest_slice_bg_"]'
        
        # 等待元素在 DOM 中出现（present 即可，不强制 visible，防 WAF）
        sb.wait_for_element_present(bg_element, timeout=20)
        print("[+] 探测到图片容器，开始通过 JS 提取图片...")

        # 核心 JS：利用 getComputedStyle 强行扣出背景图 URL，无视任何 CSS 隐藏
        js_get_bg = 'return getComputedStyle(document.querySelector(\'div[class*="geetest_bg_"]\')).backgroundImage'
        js_get_slice = 'return getComputedStyle(document.querySelector(\'div[class*="geetest_slice_bg_"]\')).backgroundImage'
        
        raw_bg = sb.execute_script(js_get_bg)
        raw_slice = sb.execute_script(js_get_slice)
        
        # 清洗 URL
        bg_url = re.search(r'url\("?(.*?)"?\)', raw_bg).group(1)
        slice_url = re.search(r'url\("?(.*?)"?\)', raw_slice).group(1)

        print(f"[+] 提取成功！背景图: {bg_url[:60]}...")
        
        # 下载图片
        bg_content = requests.get(bg_url).content
        slice_content = requests.get(slice_url).content
        
        # 调用作者的 SlideSolver (这里假设你的 geeked.slide 写法正确)
        solver = SlideSolver(slice_content, bg_content)
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别成功，计算距离: {distance}px")
        
        # 定位滑动按钮 (也用模糊匹配)
        slider_btn = sb.find_element('div[class*="slider_button"]')
        
        # 执行拟人化滑动
        tracks = get_human_track(distance)
        ActionChains(sb.driver).click_and_hold(slider_btn).perform()
        for x in tracks:
            # 加入 Y 轴随机抖动，欺骗极验后端特征检测
            ActionChains(sb.driver).move_by_offset(x, random.choice([-1, 0, 1])).perform()
            time.sleep(random.uniform(0.01, 0.02))
        
        sb.sleep(1)
        ActionChains(sb.driver).release().perform()
        print("[+] 滑动动作已完成")
        sb.sleep(12) # 等待校验结果

    except Exception as e:
        print(f"[*] 滑块环节异常: {e}")
        sb.save_screenshot("debug_error.png")

    # 最终结果报告
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "Unknown"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "Process End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
