# 🀄 连连看 - Mahjong Connect

一个基于终端的连连看游戏，使用 Python 标准库开发。

A console-based Mahjong Connect (Link Game) developed with Python standard library.

---

## 📖 游戏说明 / How to Play

### 中文

**连连看** 是一款经典的配对消除游戏。棋盘上排列着成对的方块，玩家需要找到两张相同的方块并用最多转弯 2 次的路径连接它们。

**目标**: 消除棋盘上所有方块。

**连接规则**:
- 两张方块必须图案相同
- 连接路径最多只能转弯 2 次
- 路径只能经过空格或棋盘外边界

**计分规则**:
- 基础分: 100 分 × 连击倍率
- 时间奖励: 5 秒内匹配额外 +50 分
- 连击: 3 秒内连续匹配获得倍率加成 (×1, ×2, ×3...)
- 提示: -20 分/次
- 洗牌: -50 分/次

### English

**Mahjong Connect** is a classic tile-matching game. Tiles are arranged on a grid, and players must find two identical tiles that can be connected with a path that has at most 2 turns.

**Goal**: Clear all tiles from the board.

**Connection Rules**:
- Two tiles must have the same symbol
- The connecting path can have at most 2 turns
- The path can only pass through empty cells or the board boundary

**Scoring**:
- Base score: 100 pts × combo multiplier
- Time bonus: match within 5 seconds +50 pts
- Combo: consecutive matches within 3 seconds earn multiplier (×1, ×2, ×3...)
- Hint: -20 pts each
- Shuffle: -50 pts each

---

## 🎮 操作说明 / Controls

| 按键 / Key | 功能 / Action |
|-----------|--------------|
| `↑ ↓ ← →` / `W A S D` | 移动光标 / Move cursor |
| `Enter` / `Space` | 选择/取消选择 / Select/deselect |
| `H` | 提示 / Hint |
| `S` | 洗牌 / Shuffle |
| `R` | 重新开始 / Restart |
| `P` | 暂停/继续 / Pause/Resume |
| `T` | 切换计时器 / Toggle timer |
| `Q` | 退出 / Quit |

---

## 🛠️ 安装与运行 / Installation & Usage

### 前置要求 / Prerequisites

- Python 3.7+
- pytest (仅用于测试 / for testing only)

### 安装 / Install

```bash
# 克隆或下载项目 / Clone or download the project
cd link-game

# 安装测试依赖（可选）/ Install test dependencies (optional)
pip install -r requirements.txt
```

### 运行 / Run

```bash
# 方法 1: 直接运行 / Method 1: Direct run
python3 game.py

# 方法 2: 使用脚本 / Method 2: Use script
./run.sh
```

### 运行测试 / Run Tests

```bash
pytest tests/ -q -v
```

---

## 🎨 界面预览 / Screenshot

```
  ╔═══╗╔══╗╔═══╗╔═══╗╔╗─╔╗╔═══╗╔═══╗
  ║╔═╗║║╔╗║║╔══╝║╔══╝║║─║║║╔══╝║╔═╗║
  ║╚═╝║║╚╝║║╚══╗║╚══╗║╚═╝║║╚══╗║╚═╝║
  ║╔╗╔╝║╔╗║║╔══╝║╔══╝║╔═╗║║╔══╝║╔╗╔╝
  ║║║╚╗║║║║║╚══╗║╚══╗║║─║║║╚══╗║║║╚╗
  ╚╝╚═╝╚╝╚╝╚═══╝╚═══╝╚╝─╚╝╚═══╝╚╝╚═╝

  连连看 - Mahjong Connect

  [1] 开始新游戏
  [2] 高分榜
  [3] 游戏说明
  [4] 设置
  [5] 退出
```

---

## ⚙️ 设置 / Settings

- **声音 / Sound**: 开/关 (On/Off)
- **语言 / Language**: 中文 / English
- **难度 / Difficulty**:
  - 简单 / Easy: 6×8 网格 (24 对)
  - 普通 / Normal: 8×12 网格 (48 对)
  - 困难 / Hard: 10×14 网格 (70 对)

---

## 📁 项目结构 / Project Structure

```
link-game/
├── game.py          # 主程序 / Main game (UI)
├── game_logic.py    # 核心逻辑 / Core logic
├── tests/
│   ├── __init__.py
│   └── test_game.py # 单元测试 / Unit tests
├── requirements.txt # 依赖 / Dependencies
├── run.sh           # 运行脚本 / Run script
├── scores.json      # 高分记录 / High scores (auto-generated)
└── README.md        # 本文件 / This file
```

---

## 🙏 致谢 / Credits

- 使用 Python 标准库开发 / Developed with Python standard library
- 测试框架: pytest
- 图标设计: ASCII Art

---

## 📄 许可 / License

MIT License
