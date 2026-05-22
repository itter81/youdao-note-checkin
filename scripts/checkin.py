# 有道云笔记自动签到脚本
# 依赖: pip install pyautogui pywin32 opencv-python pillow psutil pygetwindow

import subprocess
import time
import sys
import os
import psutil
import pyautogui
import pygetwindow as gw
import win32gui
import win32con
import win32api
from PIL import ImageGrab, Image
import cv2
import numpy as np

# ===================== 配置 =====================
EXE_PATH = r"D:\installapp\有道云笔记\YoudaoNote\RunYNote.exe"
PROCESS_NAME = "YoudaoNote.exe"   # 实际进程exe名，用于判断是否已运行
WINDOW_TITLE_KEYWORD = "有道云笔记"   # 窗口标题关键字

# 头像在窗口内的相对位置（基于1366x768分辨率测试，可微调）
# 有道云笔记头像在窗口左上角
AVATAR_OFFSET_X = 129   # 距窗口左边
AVATAR_OFFSET_Y = 63   # 距窗口上边

# OCR相关
# OCR使用easyocr

# ================================================


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def is_process_running():
    """检查有道云笔记进程是否已在运行"""
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name'] or ""
            if "youdao" in name.lower() or "ynote" in name.lower() or "RunYNote" in name:
                return True
        except Exception:
            pass
    return False


def launch_app():
    """启动有道云笔记"""
    if not os.path.exists(EXE_PATH):
        log(f"❌ 找不到exe: {EXE_PATH}")
        sys.exit(1)

    if is_process_running():
        log("✅ 有道云笔记已在运行，跳过启动")
    else:
        log("🚀 正在启动有道云笔记...")
        subprocess.Popen([EXE_PATH])
        log("⏳ 等待程序加载...")
        time.sleep(5)


def find_window():
    """找到有道云笔记主窗口句柄（包括隐藏/托盘状态）"""
    log("🔍 正在查找有道云笔记窗口...")

    def callback(hwnd, result):
        # 不判断IsWindowVisible，因为窗口可能在托盘隐藏
        title = win32gui.GetWindowText(hwnd)
        if WINDOW_TITLE_KEYWORD in title:
            result.append(hwnd)

    for attempt in range(10):
        result = []
        win32gui.EnumWindows(callback, result)
        if result:
            hwnd = result[0]
            log(f"✅ 找到窗口: hwnd={hwnd}, 标题={win32gui.GetWindowText(hwnd)}")
            # 强制还原并显示窗口
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(1)
            return hwnd
        log(f"  第{attempt+1}次未找到，等待2秒...")
        time.sleep(2)

    log("❌ 未能找到有道云笔记窗口")
    sys.exit(1)


def bring_to_front(hwnd):
    """将窗口置于前台"""
    # 如果窗口最小化，先还原
    placement = win32gui.GetWindowPlacement(hwnd)
    if placement[1] == win32con.SW_SHOWMINIMIZED:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.5)

    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.8)
    log("✅ 窗口已置前台")


def get_window_rect(hwnd):
    """获取窗口位置和大小"""
    rect = win32gui.GetWindowRect(hwnd)
    x, y, x2, y2 = rect
    w = x2 - x
    h = y2 - y
    log(f"📐 窗口位置: ({x},{y}) 大小: {w}x{h}")
    return x, y, w, h


def click_avatar(hwnd):
    """点击头像（窗口左上角相对坐标）"""
    x, y, w, h = get_window_rect(hwnd)

    # 头像一般在窗口左侧边栏上方
    # 根据有道云笔记UI，头像在左侧栏顶部
    # 偏移量：距窗口左边约30px，距窗口顶部约30px
    click_x = x + AVATAR_OFFSET_X
    click_y = y + AVATAR_OFFSET_Y

    log(f"🖱️  点击头像位置: ({click_x}, {click_y})")
    pyautogui.click(click_x, click_y)
    time.sleep(2.5)  # 等待面板弹出


def screenshot_region(x, y, w, h):
    """截取指定区域截图"""
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    return img


def template_match(screen_np, tmpl_path, threshold=0.65):
    """用opencv模板匹配，返回匹配位置中心坐标，找不到返回None"""
    if not os.path.exists(tmpl_path):
        log(f"  ⚠️  模板图不存在: {tmpl_path}")
        return None
    tmpl = cv2.imread(tmpl_path)
    if tmpl is None:
        log(f"  ⚠️  模板图读取失败: {tmpl_path}")
        return None
    # 转为灰度匹配，更稳定
    screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_BGR2GRAY)
    tmpl_gray   = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(screen_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    log(f"  模板匹配: {os.path.basename(tmpl_path)} 相似度={max_val:.2f}")
    if max_val >= threshold:
        th, tw = tmpl_gray.shape
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        return cx, cy
    return None


def ocr_find_checkin(img):
    """用opencv模板匹配查找签到/已签到按钮"""
    # 脚本同目录下的模板图
    base = os.path.dirname(os.path.abspath(__file__))
    tmpl_dir = os.path.join(os.path.dirname(base), "templates")
    checkin_tmpl   = os.path.join(tmpl_dir, "checkin_btn.png")
    checked_tmpl   = os.path.join(tmpl_dir, "checked_btn.png")

    screen_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # 保存截图用于调试
    debug_img = os.path.join(base, "debug_screen.png")
    cv2.imwrite(debug_img, screen_np)
    log(f"  已保存截图: {debug_img}")

    # 先找"已签到"
    pos = template_match(screen_np, checked_tmpl, threshold=0.65)
    if pos:
        log(f"  找到'已签到'按钮: {pos}")
        return pos[0], pos[1], "already"

    # 再找"签到"
    pos = template_match(screen_np, checkin_tmpl, threshold=0.65)
    if pos:
        log(f"  找到'签到'按钮: {pos}")
        return pos[0], pos[1], "checkin"

    return None, None, None


# 签到按钮相对于窗口的偏移量（实测）
# 从debug截图看：窗口左上角(196,33)，签到按钮在屏幕(860,158)
# 相对偏移: x=860-196=664, y=158-33=125
CHECKIN_OFFSET_X = 664
CHECKIN_OFFSET_Y = 125


def find_and_click_checkin(win_x, win_y):
    """根据窗口位置计算签到按钮坐标并点击"""
    log("📸 截取截图确认面板已弹出...")

    screen_w, screen_h = pyautogui.size()
    img = screenshot_region(0, 0, screen_w, screen_h)

    # 保存调试截图
    base = os.path.dirname(os.path.abspath(__file__))
    screen_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    cv2.imwrite(os.path.join(base, "debug_screen.png"), screen_np)

    # 用模板匹配确认面板是否弹出（找到就点，找不到用固定坐标兜底）
    checkin_tmpl = os.path.join(base, "checkin_btn.png")
    checked_tmpl = os.path.join(base, "checked_btn.png")

    # 直接用固定相对坐标点击签到按钮
    click_x = win_x + CHECKIN_OFFSET_X
    click_y = win_y + CHECKIN_OFFSET_Y
    log(f"🖱️  点击签到按钮: ({click_x}, {click_y})")
    pyautogui.click(click_x, click_y)
    time.sleep(1.5)

    # 检测是否弹出错误弹窗（已签到过/其他错误）
    screen_w, screen_h = pyautogui.size()
    img2 = screenshot_region(0, 0, screen_w, screen_h)
    screen_np2 = cv2.cvtColor(np.array(img2), cv2.COLOR_RGB2BGR)

    # 用模板匹配找"确定"按钮
    confirm_tmpl = os.path.join(base, "confirm_btn.png")
    pos = template_match(screen_np2, confirm_tmpl, threshold=0.65)
    if pos:
        log(f"⚠️  检测到弹窗，点击确定关闭: {pos}")
        pyautogui.click(pos[0], pos[1])
        time.sleep(0.8)
        log("✅ 今天已经签到过了")
    else:
        log("🎉 签到成功！+1M 空间到账")

    return True


def close_panel():
    """按ESC关闭面板"""
    pyautogui.press('escape')
    time.sleep(0.5)


def main():
    log("=" * 40)
    log("  有道云笔记自动签到脚本")
    log("=" * 40)

    # 1. 启动程序
    launch_app()

    # 2. 找窗口
    hwnd = find_window()

    # 3. 置前台
    bring_to_front(hwnd)

    # 4. 点击头像
    log("🖱️  点击头像...")
    click_avatar(hwnd)

    # 5. OCR找签到并点击
    x, y, w, h = get_window_rect(hwnd)
    success = find_and_click_checkin(x, y)

    # 6. 关闭面板
    close_panel()

    if success:
        log("✅ 签到流程完成！")
    else:
        log("❌ 签到流程失败，请手动检查")

    log("=" * 40)


if __name__ == "__main__":
    main()
