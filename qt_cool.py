import os
import time
import re
import requests
import random
import math
from seleniumbase import SB

def run_checkin(sb):
    sk = os.environ.get("QTCOOL_SK")
    
    # 彻底抹除指纹
    sb.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("[*] 载入晴辰云...")
    sb.open("https://gpt.qt.cool/checkin")
    sb.sleep(5)
    
    # 登录
    sb.type('#renewKey', sk)
    sb.click('button.renew') # 对应 HTML 里的 ci-btn renew
    sb.sleep(8)
    
    # 点击签到按钮触发验证码
    print("[*] 触发签到验证码...")
    sb.click("#checkinBtn")
    sb.sleep(5)

    try:
        # 1. 计算位移 (使用你之前的识别逻辑，假设识别出 distance)
        # 这里为了演示先设为识别出的值，实际运行时请结合你的 SlideSolver
        distance = 168 
        
        # 2. 注入“全路径”物理模拟脚本
        # 这个脚本会同时操作 事件流 + CSS样式 + Canvas属性
        print(f"[*] 启动全路径模拟滑动: {distance}px")
        
        js_ultimate_move = f"""
        (async () => {{
            var btn = document.querySelector('div[class*="geetest_btn"]');
            var slice = document.querySelector('div[class*="geetest_slice_"]');
            if (!btn) return "BTN_NOT_FOUND";

            var rect = btn.getBoundingClientRect();
            var startX = rect.left + rect.width / 2;
            var startY = rect.top + rect.height / 2;

            // 第一步：按下
            btn.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true, clientX: startX, clientY: startY, buttons: 1}}));
            await new Promise(r => setTimeout(r, 200));

            // 第二步：模拟物理滑动轨迹
            let steps = 40;
            for (let i = 1; i <= steps; i++) {{
                let progress = i / steps;
                // 五次方减速曲线
                let moveX = startX + ({distance} * (1 - Math.pow(1 - progress, 5)));
                let currentOffset = moveX - startX;

                // 核心：强制同步修改所有可能影响显示的 CSS 属性
                let transformStr = "translate(" + currentOffset + "px, 0px)";
                btn.style.setProperty("transform", transformStr, "important");
                if (slice) slice.style.setProperty("transform", transformStr, "important");

                // 派发移动事件
                btn.dispatchEvent(new MouseEvent('mousemove', {{
                    bubbles: true, 
                    clientX: moveX, 
                    clientY: startY + (Math.random() * 2 - 1),
                    buttons: 1
                }}));
                
                // 降低频率防止 Actions 崩溃
                if (i % 4 === 0) await new Promise(r => setTimeout(r, 10));
            }}

            // 第三步：释放
            await new Promise(r => setTimeout(r, 300));
            btn.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true, clientX: startX + {distance}, clientY: startY}}));
            
            return "SUCCESS_MOVED";
        }})();
        """
        
        result = sb.execute_script(js_ultimate_move)
        print(f"[*] 执行结果: {result}")

        # 3. 立即抓拍
        sb.sleep(0.5)
        photo = "action_final.png"
        sb.save_screenshot(photo)
        print(f"[+] 动作快照已保存")

    except Exception as e:
        print(f"[*] 流程异常: {e}")
        sb.save_screenshot("error.png")

if __name__ == "__main__":
    with SB(uc=True, test=True, locale="zh_CN") as sb:
        run_checkin(sb)
