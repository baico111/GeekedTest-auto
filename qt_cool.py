import os
import time
import sys
import datetime
import requests
import re
import base64
import json
import random
import math
from seleniumbase import SB

# --- 导入专业解算模块 ---
try:
    from geeked.slide import SlideSolver
    from geeked.sign import Signer
except ImportError:
    print("[-] 错误: 请确保仓库中存在 geeked 目录及相关 py 文件")

CHECKIN_URL = "https://gpt.qt.cool/checkin"

# ================= 1. 轨迹算法：模拟真人手抖 (核心) =================
def get_bezier_track(distance):
    """
    生成贝塞尔曲线轨迹，模拟人类先快后慢、随机抖动、最后微调对齐的过程
    """
    track = []
    current = 0
    # 模拟人类操作步数 (30-50步)
    steps = random.randint(35, 50)
    for i in range(1, steps + 1):
        t = i / steps
        # 缓动函数：Ease-Out 三次方曲线
        move = round(distance * (1 - math.pow(1 - t, 3)))
        track.append(move - current)
        current = move
    # 模拟对准时的微小回退（人类特征：滑过头一点点再退回来）
    track.extend([1, 1, 0, -1, -1]) 
    return track

# ================= 2. 自动化报告逻辑 =================
def send_report(expiry, status, photo):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("MY_CHAT_ID")
    if not token or not chat_id: return
    
    now = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    html = f"✅ <b>Qt-Cool 续期任务报告</b>\n---\n👤 <b>状态:</b> {status}\n📅 <b>到期:</b> {expiry}\n🕒 <b>时间:</b> {now}"
    
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(photo, 'rb') as f:
            requests.post(url, data={'chat_id': chat_id, 'caption': html, 'parse_mode': 'HTML'}, files={'photo': f}, timeout=15)
    except: pass

# ================= 3. 主业务工作流 =================
def run_workflow(sb):
    from selenium.webdriver.common.action_chains import ActionChains
    sk = os.environ.get("QTCOOL_SK")
    
    try:
        print("[*] 正在载入晴辰云...")
        sb.open(CHECKIN_URL)
        time.sleep(5)
        
        # 填入 SK 并登录
        sb.type('input#renewKey', sk)
        sb.click('button[onclick*="doRenewLogin"]')
        time.sleep(3)
        
        # 处理可能的算术题
        if sb.is_element_visible("#renewCaptchaQ"):
            q = sb.get_text("#renewCaptchaQ")
            nums = [int(n) for n in re.findall(r'\d+', q)]
            ans = (nums[0] - nums[1]) if "-" in q else (nums[0] + nums[1])
            sb.type("#renewCaptchaA", str(ans))
            
        # 点击签到激活滑块
        sb.click("#checkinBtn")
        time.sleep(2)
        
        # --- 强力破解滑块环节 ---
        if sb.is_element_present('div[class*="geetest_canvas_img"]'):
            print("[!] 探测到滑块，启动 OpenCV + 贝塞尔强攻...")
            
            # 提取背景图和拼图块 URL
            bg_style = sb.get_attribute('div[class*="geetest_canvas_img"]', 'style')
            slice_style = sb.get_attribute('div[class*="geetest_slice_bg"]', 'style')
            bg_url = re.search(r'url\("(.*?)"\)', bg_style).group(1)
            slice_url = re.search(r'url\("(.*?)"\)', slice_style).group(1)
            
            # 调用专业识图模块
            solver = SlideSolver(
                puzzle_piece=SlideSolver.load_image(slice_url),
                background=SlideSolver.load_image(bg_url)
            )
            distance = solver.find_puzzle_piece_position()
            print(f"[+] OpenCV 识别精确距离: {distance}px")
            
            # 生成拟人轨迹并滑动
            slider = sb.find_element('div[class*="slider_button"]')
            tracks = get_bezier_track(distance)
            
            ActionChains(sb.driver).click_and_hold(slider).perform()
            for x in tracks:
                # 随机增加微小的 Y 轴抖动
                y_offset = random.choice([-1, 0, 1]) if random.random() > 0.8 else 0
                ActionChains(sb.driver).move_by_offset(x, y_offset).perform()
                time.sleep(random.uniform(0.01, 0.03))
            time.sleep(0.5)
            ActionChains(sb.driver).release().perform()
            
        print("[*] 动作结束，等待状态抓取...")
        time.sleep(10)
        
        # 结果处理
        photo = "result.png"
        sb.save_screenshot(photo)
        expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "未知"
        status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "任务完成"
        
        send_report(expiry, status, photo)
        return True
    except Exception as e:
        print(f"[-] 流程异常: {e}"); return False

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        if not run_workflow(sb): sys.exit(1)
