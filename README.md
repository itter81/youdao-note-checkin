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

示例：

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
