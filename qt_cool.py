import os
import time
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

def send_tg_report(expiry, status, photo):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("MY_CHAT_ID")
    if not token or not chat_id: return
    now = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    caption = f"📸 <b>Qt-Cool 物理模拟调试</b>\n---\n👤 状态: {status}\n📅 到期: {expiry}\n🕒 时间: {now}"
    try:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo, 'rb') as f:
            requests.post(url, data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}, files={'photo': f}, timeout=15)
    except: pass

def run_checkin(sb):
    sk = os.environ.get("QTCOOL_SK")
    
    # 彻底抹除指纹
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
    
    print("[*] 正在捕获动态验证码...")
    sb.sleep(10) 
    
    try:
        # 1. 提取图片 URL 并计算距离
        js_get_imgs = """
        var bg = getComputedStyle(document.querySelector('div[class*="geetest_bg_"]')).backgroundImage;
        var slice = getComputedStyle(document.querySelector('div[class*="geetest_slice_bg_"]')).backgroundImage;
        return [bg, slice];
        """
        urls = sb.execute_script(js_get_imgs)
        bg_url = re.search(r'url\("?(.*?)"?\)', urls[0]).group(1)
        slice_url = re.search(r'url\("?(.*?)"?\)', urls[1]).group(1)

        bg_content = requests.get(bg_url, timeout=10).content
        slice_content = requests.get(slice_url, timeout=10).content
        
        solver = SlideSolver(slice_content, bg_content)
        distance = solver.find_puzzle_piece_position()
        print(f"[+] 识别成功，位移: {distance}px")
        
        # 2. 物理拖拽实现 (修正后的 API)
        print("[*] 启动 SeleniumBase UC 物理拖拽...")
        slider_selector = 'div[class*="geetest_btn"]'
        
        # 使用 SeleniumBase 的底层 uc_gui 风格拖拽，这最接近真实物理操作
        # 参数分别为：选择器, x方向位移, y方向位移
        sb.drag_and_drop_with_offset(slider_selector, distance, 0)
        
        # 动作后立即截图
        print("[!] 拖拽动作完成，立即抓拍...")
        sb.sleep(1) 
        photo = "debug_physical.png"
        sb.save_screenshot(photo)
        print(f"[+] 现场截图已保存: {photo}")
        
        sb.sleep(10)

    except Exception as e:
        print(f"[*] 流程异常: {e}")
        photo = "debug_error.png"
        sb.save_screenshot(photo)

    # 结果上报
    expiry = sb.get_text("#renewUserExpiry") if sb.is_element_present("#renewUserExpiry") else "Wait result..."
    status = sb.get_text("#heroBadgeText") if sb.is_element_present("#heroBadgeText") else "End"
    send_tg_report(expiry, status, photo)

if __name__ == "__main__":
    # 必须开启 uc=True 才能使用高级拖拽功能
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
