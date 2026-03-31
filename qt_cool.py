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
    print("[-] 警告: 未找到 geeked 模块")

CHECKIN_URL = "https://gpt.qt.cool/checkin"

def get_human_track(distance):
    track = []
    current = 0
    # 针对长位移 (213px)，大幅增加步数以平摊请求压力
    steps = random.randint(90, 120)
    for i in range(1, steps + 1):
        t = i / steps
        # 五次方曲线：平滑减速
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
    
    # 彻底抹除 WebDriver 指纹 (核心防封)
    sb.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("[*] 正在载入晴辰云...")
    sb.open(CHECKIN_URL)
    sb.sleep(6) # 增加首屏加载缓冲
    
    # 登录
    sb.type('input#renewKey', sk)
    sb.click('button[onclick*="doRenewLogin"]')
    sb.sleep(10)
    
    # 签到
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    print("[*] 正在捕获验证码...")
    sb.sleep(12) # 给极验 4.0 充足的动画加载时间
    
    try:
        # 1. 提取图片 URL
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
        print(f"[+] 识别成功: {distance}px")
        
        # 2. 定位按钮 (增加稳定性处理)
        btn_selector = 'div[class*="geetest_btn"]'
        # 只要存在就操作，不强求 visible 以防 WAF 干扰
        sb.wait_for_element_present(btn_selector, timeout=20)
        slider_btn = sb.driver.find_element("css selector", btn_selector)

        # 3. 滑动动作 (ActionChains)
        tracks = get_human_track(distance)
        
        # 降低 ActionChains 的内部频率，防止 Connection refused
        actions = ActionChains(sb.driver)
        actions.click_and_hold(slider_btn).perform()
        
        for x in tracks:
            # 模拟随机抖动并执行
            actions.move_by_offset(x, random.choice([-1, 0, 1])).perform()
            # 关键：稍微增加每一步的等待，防止过快导致浏览器崩溃
            time.sleep(random.uniform(0.02, 0.04))
        
        sb.sleep(1)
        actions.release().perform()
        print("[+] 滑动动作已释放，等待最终校验...")
        sb.sleep(15) # 给签到成功后的页面跳转留出充足时间

    except Exception as e:
        print(f"[*] 流程异常: {e}")
        # 异常时也要尝试截图
        try: sb.save_screenshot("debug_error.png")
        except: pass

    # 结果捕获
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "N/A"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    # 使用增强配置：uc 模式、ad_block、禁止弹出窗口
    with SB(uc=True, test=True, ad_block=True, locale="zh_CN") as sb:
        run_checkin(sb)
