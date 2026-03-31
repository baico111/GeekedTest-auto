import os
import time
import sys
import datetime
import requests
import re
import random
import math
from seleniumbase import SB

# 尝试导入专业模块
try:
    from geeked.slide import SlideSolver
    from geeked.sign import Signer
except ImportError:
    print("[-] 警告: 未找到 geeked 模块，将影响识图和加密生成")

CHECKIN_URL = "https://gpt.qt.cool/checkin"

# ================= 1. 核心：拟人化贝塞尔轨迹 =================
def get_human_track(distance):
    track = []
    current = 0
    # 模拟真实人类滑动步数
    steps = random.randint(40, 60)
    for i in range(1, steps + 1):
        t = i / steps
        # Ease-out 曲线：开始快，接近目标时变慢
        move = round(distance * (1 - math.pow(1 - t, 3)))
        track.append(move - current)
        current = move
    # 模拟人类微调：过头一点点再退回来
    track.extend([2, 1, 0, -1, -2]) 
    return track

# ================= 2. 报告逻辑 =================
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

# ================= 3. 主执行逻辑 =================
def run_checkin(sb):
    from selenium.webdriver.common.action_chains import ActionChains
    sk = os.environ.get("QTCOOL_SK")
    
    print("[*] 正在载入晴辰云...")
    sb.open(CHECKIN_URL)
    sb.wait_for_element_visible('input#renewKey', timeout=20)
    
    # 填入 SK 并进入签到页面
    sb.type('input#renewKey', sk)
    sb.click('button[onclick*="doRenewLogin"]')
    time.sleep(3)
    
    # 点击签到按钮触发验证码
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    # --- 关键：等待并破解极验滑块 ---
    print("[*] 正在等待验证码弹出...")
    try:
        # 显式等待验证码 Canvas 出现
        sb.wait_for_element_visible('div[class*="geetest_canvas_img"]', timeout=10)
        print("[!] 探测到滑块！启动 OpenCV 识图...")
        
        # 提取图片 URL
        bg_style = sb.get_attribute('div[class*="geetest_canvas_img"]', 'style')
        slice_style = sb.get_attribute('div[class*="geetest_slice_bg"]', 'style')
        bg_url = re.search(r'url\("(.*?)"\)', bg_style).group(1)
        slice_url = re.search(r'url\("(.*?)"\)', slice_style).group(1)
        
        # 使用 SlideSolver 计算物理距离
        solver = SlideSolver(
            puzzle_piece=SlideSolver.load_image(slice_url),
            background=SlideSolver.load_image(bg_url)
        )
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别成功，目标位移: {distance}px")
        
        # 开始模拟滑动
        slider_btn = sb.find_element('div[class*="slider_button"]')
        tracks = get_human_track(distance)
        
        ActionChains(sb.driver).click_and_hold(slider_btn).perform()
        for x in tracks:
            # 随机 1 像素的 Y 轴微小抖动
            y_offset = random.choice([-1, 0, 1]) if random.random() > 0.8 else 0
            ActionChains(sb.driver).move_by_offset(x, y_offset).perform()
            time.sleep(random.uniform(0.01, 0.02))
        
        time.sleep(0.5)
        ActionChains(sb.driver).release().perform()
        print("[+] 滑动结束，等待校验结果...")
        time.sleep(5)
        
    except Exception as e:
        print(f"[*] 未探测到滑块或破解失败: {e}")

    # 结果抓取
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "抓取失败"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "任务结束"
    
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
