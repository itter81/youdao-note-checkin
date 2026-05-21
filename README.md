# youdao-note-checkin

有道云笔记 Windows 客户端自动签到脚本，基于 GUI 自动化实现，模拟人工点击，无需抓包。

## 目录结构

```
youdao-note-checkin/
├── scripts/
│   └── checkin.py
├── templates/
│   └── checkin_btn.png
├── .gitignore
├── requirements.txt
└── README.md
```

## 环境要求

- Windows 10
- Python 3.x
- 有道云笔记客户端已安装

## 依赖安装

```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

## 配置

编辑 `scripts/checkin.py` 顶部配置项：

```python
EXE_PATH = r"D:\installapp\有道云笔记\YoudaoNote\RunYNote.exe"  # 有道云笔记安装路径
AVATAR_OFFSET_X = 129  # 头像距窗口左边像素（根据实际调整）
AVATAR_OFFSET_Y = 63   # 头像距窗口顶部像素（根据实际调整）
CHECKIN_OFFSET_X = 664 # 签到按钮距窗口左边像素
CHECKIN_OFFSET_Y = 125 # 签到按钮距窗口顶部像素
```

## 模板图准备

截取有道云笔记签到面板中的**签到按钮**区域，保存为 `checkin_btn.png` 放到 `templates/` 目录。

![checkin_btn](templates/checkin_btn.png)

## 使用

```bash
python scripts/checkin.py
```

## 设置每日自动运行

打开任务计划程序，新建任务：

- 触发器：每天，设置时间
- 操作：
  - 程序：`D:\installapp\python\3.13.9\python.exe`
  - 参数：`checkin.py`
  - 起始于：`D:\installapp\shanxi-xunjian\scripts`

---

## 实现原理

```
启动有道云笔记
    ↓
查找窗口句柄（支持托盘隐藏状态）
    ↓
置前台 → 点击头像
    ↓
等待签到面板弹出
    ↓
根据窗口相对坐标点击签到按钮
```

不使用 HTTP 请求或注入方式，完全模拟用户操作，规避风控风险。

---

## 实现过程与踩坑记录

> 这一节记录整个调试过程，包括技术选型、报错和解决方案，供参考。

### 一、为什么不用 HTTP 请求直接签到

最开始考虑过抓包拿到签到接口直接发请求，但放弃了，原因：

- token 会过期，需要定期维护
- 长期自动请求容易触发风控，可能需要处理验证码、设备指纹、加密签名
- 协议随时可能变，维护成本高

最终选择 **GUI 自动化**，完全模拟人的点击操作，从服务器角度看就是正常用户行为，规避所有风控风险。

---

### 二、启动程序与查找窗口

**启动方式**：直接用安装路径启动 `RunYNote.exe`，不管程序是否已在运行，有道云笔记有单例保护会自动激活已有窗口。

查找窗口时第一版用了 `IsWindowVisible` 过滤，结果一直找不到：

```
[10:36:22] 🔍 正在查找有道云笔记窗口...
[10:36:22]   第1次未找到，等待2秒...
[10:36:24]   第2次未找到，等待2秒...
...
[10:36:36]   第8次未找到，等待2秒...
Traceback: 未能找到有道云笔记窗口
```

原因是有道云笔记启动后默认在托盘隐藏，窗口不可见，`IsWindowVisible` 返回 False。

去掉可见性过滤，改为枚举所有窗口标题匹配，找到后用 `ShowWindow(SW_RESTORE)` 强制还原：

```python
win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
```

---

### 三、OCR 方案的选择与失败

签到面板里的"签到"按钮需要识别，最初计划用 OCR 识别文字来定位按钮位置，先后尝试了三个方案，全部因为 **Python 3.13 兼容性问题**折在 DLL 上。

**尝试一：PaddleOCR**

```
ValueError: Unknown argument: show_log
...
Checking connectivity to the model hosters, this may take a while.
Downloading Model from https://www.modelscope.cn ...
```

参数不兼容新版本，而且每次运行都要联网下载模型，速度极慢，放弃。

**尝试二：EasyOCR**

```
OSError: [WinError 1114] 动态链接库(DLL)初始化例程失败。
Error loading "torch\lib\c10.dll"
```

EasyOCR 依赖 torch，torch 目前不支持 Python 3.13，DLL 加载失败。

**尝试三：ddddocr**

```
ImportError: DLL load failed while importing onnxruntime_pybind11_state:
动态链接库(DLL)初始化例程失败。
```

ddddocr 依赖 onnxruntime，同样不支持 Python 3.13。

**尝试四：rapidocr**

```
ImportError: DLL load failed while importing onnxruntime_pybind11_state:
动态链接库(DLL)初始化例程失败。
```

底层还是 onnxruntime，结果一样。

**结论**：Python 3.13 目前与主流 OCR 库的底层 DLL 全面不兼容，彻底放弃 OCR 方案。

---

### 四、改用 OpenCV 模板匹配

既然 OCR 走不通，改用 OpenCV 模板匹配，截一张签到按钮的图作为模板，在屏幕截图里搜索匹配区域。OpenCV 在 Python 3.13 上没有 DLL 问题：

```bash
python -c "import cv2; print('OK', cv2.__version__)"
OK 4.13.0
```

但模板匹配遇到了新问题，相似度阈值 0.7 时一直匹配到错误位置：

```
[11:12:50]   模板匹配: checkin_btn.png 相似度=0.70
[11:12:50]   找到'签到'按钮: (71, 595)   ← 错误！应该在右上角
[11:12:50] 🖱️  找到签到按钮，点击位置: (71, 595)
```

坐标 `(71, 595)` 在屏幕左下角，完全不对。通过保存调试截图发现，模板匹配到了界面左下角一个颜色相近的区域，而不是签到按钮。

```python
# 保存调试截图
cv2.imwrite("debug_screen.png", screen_np)
```

查看截图后确认：**签到面板弹出正常，但模板匹配定位错误**。

---

### 五、最终方案：固定相对坐标

模板匹配不可靠，改为直接用**窗口相对坐标**点击签到按钮。

通过调试截图确认窗口位置和签到按钮的屏幕坐标：

- 窗口左上角：`(196, 33)`
- 签到按钮屏幕坐标：`(860, 158)`
- 相对偏移：`x = 860 - 196 = 664`，`y = 158 - 33 = 125`

头像坐标通过实测获得（鼠标悬停3秒后打印坐标）：

```python
import pyautogui, time
time.sleep(3)
print(pyautogui.position())
# Point(x=325, y=96)
```

最终运行结果：

```
[11:22:42] 🖱️  点击签到按钮: (860, 158)
[11:22:44] 🎉 签到完成！
[11:22:44] ✅ 签到流程完成！
```

点击后截图确认签到按钮变为灰色"已签到"状态，存储空间显示 **+1M** 奖励到账。

---

### 六、有道云笔记界面结构说明

调试过程中发现有道云笔记是用 **CEF（Chromium Embedded Framework）** 渲染界面的，本质上是内嵌浏览器，所以：

- 无法用 `FindWindowEx` 找到头像、签到按钮等控件句柄
- 所有 UI 元素都是 HTML 渲染，不是 Win32 控件
- 枚举子窗口只能看到 `CefBrowserWindow`、`Chrome_RenderWidgetHostHWND` 等 CEF 内部窗口

```
类名:CefBrowserWindow    标题:''  位置:(749, 128, 1497, 768)
类名:Chrome_WidgetWin_0  标题:''  位置:(749, 128, 1497, 768)
类名:Chrome_RenderWidgetHostHWND  标题:'Chrome Legacy Window'
```

这也是为什么最终只能用坐标方案，而不是更优雅的控件句柄方案。
