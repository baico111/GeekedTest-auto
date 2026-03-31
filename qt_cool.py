import os
import time
import sys
import datetime
import requests
import re
import random
import math
from seleniumbase import SB

# --- 导入专业解算模块 ---
try:
    from geeked.slide import SlideSolver
    from geeked.sign import Signer
except ImportError:
    print("[-] 警告: 未找到 geeked 模块，请检查目录结构")

CHECKIN_URL = "https://gpt.qt.cool/checkin"

# ================= 1. 核心：拟人化贝塞尔轨迹 (保留并增强) =================
def get_human_track(distance):
    track = []
    current = 0
    # 增加步数随机性，模拟真人犹豫感
    steps = random.randint(45, 65)
    for i in range(1, steps + 1):
        t = i / steps
        # Ease-out 三次方曲线
        move = round(distance * (1 - math.pow(1 - t, 3)))
        track.append(move - current)
        current = move
    # 模拟对准时的微小回退抖动
    track.extend([1, 1, 0, -1, -1]) 
    return track

# ================= 2. 报告逻辑 (完整保留) =================
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

# ================= 3. 主执行逻辑 (增强 iframe 穿透能力) =================
def run_checkin(sb):
    from selenium.webdriver.common.action_chains import ActionChains
    sk = os.environ.get("QTCOOL_SK")
    
    print("[*] 正在载入晴辰云...")
    sb.open(CHECKIN_URL)
    sb.wait_for_element_visible('input#renewKey', timeout=20)
    
    # 填入 SK 并进入签到页面
    sb.type('input#renewKey', sk)
    sb.click('button[onclick*="doRenewLogin"]')
    time.sleep(5) # 给页面充足的渲染时间
    
    # 处理可能的算术题 (保留功能)
    if sb.is_element_visible("#renewCaptchaQ"):
        q = sb.get_text("#renewCaptchaQ")
        print(f"[*] 发现算术题: {q}")
        nums = [int(n) for n in re.findall(r'\d+', q)]
        ans = (nums[0] - nums[1]) if "-" in q else (nums[0] + nums[1])
        sb.type("#renewCaptchaA", str(ans))
        time.sleep(1)

    # 点击签到按钮触发验证码
    if sb.is_element_visible("#checkinBtn"):
        print("[*] 点击签到按钮...")
        sb.click("#checkinBtn")
    
    # --- 关键修复：穿透 iFrame 探测滑块 ---
    print("[*] 正在等待验证码弹出...")
    try:
        # 增加 5 秒强制等待，确保极验的 iframe 节点已生成
        time.sleep(5)
        
        # 尝试切换到极验的 iframe (极验4.0的核心特征)
        # 尝试多种可能的 iframe 选择器
        if sb.is_element_present('iframe[title*="验证码"]'):
            sb.switch_to_frame('iframe[title*="验证码"]')
            print("[+] 已成功切入：标题标识 iframe")
        elif sb.is_element_present('iframe[src*="geetest"]'):
            sb.switch_to_frame('iframe[src*="geetest"]')
            print("[+] 已成功切入：协议标识 iframe")
        
        # 现在在 iframe 内部寻找滑块图片
        # 适配多种可能的选择器（Canvas 或 Div）
        target_selector = 'div[class*="geetest_canvas_img"]'
        sb.wait_for_element_visible(target_selector, timeout=20)
        print("[!] 探测到滑块！启动 OpenCV 识图...")
        
        # 提取图片 URL
        bg_style = sb.get_attribute('div[class*="geetest_canvas_img"]', 'style')
        slice_style = sb.get_attribute('div[class*="geetest_slice_bg"]', 'style')
        bg_url = re.search(r'url\("(.*?)"\)', bg_style).group(1)
        slice_url = re.search(r'url\("(.*?)"\)', slice_style).group(1)
        
        # 调用 SlideSolver 计算位移
        solver = SlideSolver(
            puzzle_piece=SlideSolver.load_image(slice_url),
            background=SlideSolver.load_image(bg_url)
        )
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别成功，目标位移: {distance}px")
        
        # 定位滑动条按钮
        slider_btn = sb.find_element('div[class*="slider_button"]')
        tracks = get_human_track(distance)
        
        # 开始物理滑动模拟
        ActionChains(sb.driver).click_and_hold(slider_btn).perform()
        for x in tracks:
            # 随机 1 像素 Y 轴偏移增加指纹复杂度
            y_offset = random.choice([-1, 0, 1]) if random.random() > 0.8 else 0
            ActionChains(sb.driver).move_by_offset(x, y_offset).perform()
            time.sleep(random.uniform(0.01, 0.02))
        
        time.sleep(0.8)
        ActionChains(sb.driver).release().perform()
        print("[+] 滑动结束，等待校验结果...")
        
        # 必须切回主文档，否则无法截图和抓取状态文字
        sb.switch_to_default_content()
        time.sleep(8)
        
    except Exception as e:
        print(f"[*] 滑块环节异常或未探测到: {e}")
        sb.switch_to_default_content()

    # 结果抓取与发送报告 (保留功能)
    photo = "result.png"
    sb.save_screenshot(photo)
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "抓取失败"
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "流程结束"
    
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    # 使用 UC 模式（反爬虫增强）
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
