#!/usr/bin/env python3
"""
game.py - Mahjong Connect (连连看) Console Game
Main entry point with terminal UI.
"""

import os
import sys
import time
import signal

# Ensure we can import game_logic from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game_logic import Game, RESET, BOLD, DIM

# ── Cross-platform single-key input ──────────────────────────────────

def _get_key_unix():
    """Read a single keypress on Unix/Linux/macOS."""
    import termios
    import tty
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            # Arrow keys send escape sequences
            more = sys.stdin.read(2)
            ch += more
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _get_key_windows():
    """Read a single keypress on Windows."""
    import msvcrt
    ch = msvcrt.getch()
    if ch == b'\xe0':
        ch2 = msvcrt.getch()
        return '\x1b' + ch2.decode()
    try:
        return ch.decode()
    except UnicodeDecodeError:
        return '\x00'


def get_key():
    """Cross-platform single keypress input."""
    try:
        if os.name == 'nt':
            return _get_key_windows()
        else:
            return _get_key_unix()
    except (ImportError, OSError, AttributeError):
        # Fallback: use input()
        try:
            return input()
        except (EOFError, KeyboardInterrupt):
            return '\x03'


# ── ANSI helpers ─────────────────────────────────────────────────────

CLEAR = '\033[2J\033[H'
HIDE_CURSOR = '\033[?25l'
SHOW_CURSOR = '\033[?25h'
SAVE_CURSOR = '\033[s'
RESTORE_CURSOR = '\033[u'

# Color shortcuts
C_RED = '\033[31m'
C_GREEN = '\033[32m'
C_YELLOW = '\033[33m'
C_BLUE = '\033[34m'
C_MAGENTA = '\033[35m'
C_CYAN = '\033[36m'
C_WHITE = '\033[37m'
C_BRIGHT_RED = '\033[91m'
C_BRIGHT_GREEN = '\033[92m'
C_BRIGHT_YELLOW = '\033[93m'
C_BRIGHT_BLUE = '\033[94m'
C_BRIGHT_MAGENTA = '\033[95m'
C_BRIGHT_CYAN = '\033[96m'
C_BRIGHT_WHITE = '\033[97m'
C_BG_RED = '\033[41m'
C_BG_GREEN = '\033[42m'
C_BG_YELLOW = '\033[43m'
C_BG_BLUE = '\033[44m'
C_BG_MAGENTA = '\033[45m'
C_BG_CYAN = '\033[46m'
C_BG_WHITE = '\033[47m'
C_BG_BRIGHT_YELLOW = '\033[103m'
C_BG_BRIGHT_CYAN = '\033[106m'
C_BG_BRIGHT_WHITE = '\033[107m'

COLORS = [
    C_RED, C_GREEN, C_YELLOW, C_BLUE, C_MAGENTA, C_CYAN,
    C_BRIGHT_RED, C_BRIGHT_GREEN, C_BRIGHT_YELLOW, C_BRIGHT_BLUE,
    C_BRIGHT_MAGENTA, C_BRIGHT_CYAN,
]

# ── Settings ─────────────────────────────────────────────────────────

class Settings:
    def __init__(self):
        self.sound = True
        self.language = 'zh'  # 'zh' or 'en'
        self.difficulty = 'normal'

    def toggle_sound(self):
        self.sound = not self.sound
        return self.sound

    def cycle_language(self):
        self.language = 'en' if self.language == 'zh' else 'zh'
        return self.language

    def cycle_difficulty(self):
        diffs = ['easy', 'normal', 'hard']
        idx = diffs.index(self.difficulty)
        self.difficulty = diffs[(idx + 1) % 3]
        return self.difficulty


settings = Settings()


# ── Sound ────────────────────────────────────────────────────────────

def beep():
    """Play a terminal beep."""
    if settings.sound:
        sys.stdout.write('\a')
        sys.stdout.flush()


def try_pygame_sound(sound_type='match'):
    """Try to play sound via pygame if available."""
    if not settings.sound:
        return False
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        import io
        import struct
        import math

        duration = 0.15
        freq = 800 if sound_type == 'match' else (400 if sound_type == 'fail' else 1200)
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        samples = []
        for i in range(n_samples):
            t = i / sample_rate
            envelope = max(0, 1 - t / duration)
            value = int(32767 * math.sin(2 * math.pi * freq * t) * envelope)
            samples.append(value)

        buf = io.BytesIO()
        for s in samples:
            buf.write(struct.pack('<h', s))

        buf.seek(0)
        sound = pygame.mixer.Sound(buf)
        sound.play()
        return True
    except Exception:
        beep()
        return False


def play_sound(sound_type='match'):
    """Play sound effect."""
    try_pygame_sound(sound_type)


# ── Screen Drawing ───────────────────────────────────────────────────

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls||clear')


def move_cursor(r, c):
    """Move cursor to row r, column c (1-indexed)."""
    sys.stdout.write(f'\033[{r};{c}H')


def set_color(color_code):
    """Set text color."""
    sys.stdout.write(color_code)


def reset_color():
    """Reset text attributes."""
    sys.stdout.write(RESET)


def set_bold():
    sys.stdout.write(BOLD)


def set_dim():
    sys.stdout.write(DIM)


# ── ASCII Art Title ──────────────────────────────────────────────────

TITLE_ART = [
    "╔═══╗╔══╗╔═══╗╔═══╗╔╗─╔╗╔═══╗╔═══╗",
    "║╔═╗║║╔╗║║╔══╝║╔══╝║║─║║║╔══╝║╔═╗║",
    "║╚═╝║║╚╝║║╚══╗║╚══╗║╚═╝║║╚══╗║╚═╝║",
    "║╔╗╔╝║╔╗║║╔══╝║╔══╝║╔═╗║║╔══╝║╔╗╔╝",
    "║║║╚╗║║║║║╚══╗║╚══╗║║─║║║╚══╗║║║╚╗",
    "╚╝╚═╝╚╝╚╝╚═══╝╚═══╝╚╝─╚╝╚═══╝╚╝╚═╝",
]

GAME_OVER_ART = [
    "╔═══╗╔═══╗╔═══╗╔═══╗─╔═══╗╔═══╗╔═══╗╔═══╗",
    "║╔═╗║║╔══╝║╔══╝║╔═╗║─║╔═╗║║╔══╝║╔═╗║║╔═╗║",
    "║╚═╝║║╚══╗║╚══╗║╚═╝║─║╚═╝║║╚══╗║╚═╝║║║─║║",
    "║╔╗╔╝║╔══╝║╔══╝║╔╗╔╝─║╔╗╔╝║╔══╝║╔╗╔╝║║─║║",
    "║║║╚╗║╚══╗║╚══╗║║║╚╗─║║║╚╗║╚══╗║║║╚╗║╚═╝║",
    "╚╝╚═╝╚═══╝╚═══╝╚╝╚═╝─╚╝╚═╝╚═══╝╚╝╚═╝╚═══╝",
]

WIN_ART = [
    "╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗",
    "║╔═╗║║╔══╝║╔══╝║╔══╝║╔══╝║╔═╗║║╔══╝║╔══╝║╔═╗║",
    "║╚═╝║║╚══╗║╚══╗║╚══╗║╚══╗║╚═╝║║╚══╗║╚══╗║╚═╝║",
    "║╔╗╔╝║╔══╝║╔══╝║╔══╝║╔══╝║╔╗╔╝║╔══╝║╔══╝║╔╗╔╝",
    "║║║╚╗║║──║║╚══╗║╚══╗║╚══╗║║║╚╗║╚══╗║╚══╗║║║╚╗",
    "╚╝╚═╝╚╝──╚╝═══╝╚═══╝╚═══╝╚╝╚═╝╚═══╝╚═══╝╚╝╚═╝",
]


# ── Menu Screen ──────────────────────────────────────────────────────

def draw_menu():
    """Draw the main menu screen."""
    clear_screen()
    print(HIDE_CURSOR)

    # Title
    print(C_BRIGHT_YELLOW + BOLD)
    for line in TITLE_ART:
        print(f"  {line}")
    print(RESET)

    subtitle = "连连看 - Mahjong Connect"
    print(f"\n  {C_BRIGHT_CYAN}{BOLD}{subtitle}{RESET}\n")

    diff_names = {'easy': '简单 6×8', 'normal': '普通 8×12', 'hard': '困难 10×14'}
    lang_names = {'zh': '中文', 'en': 'English'}

    menu_items = [
        ("1", "开始新游戏", "New Game"),
        ("2", "高分榜", "High Scores"),
        ("3", "游戏说明", "How to Play"),
        ("4", "设置", "Settings"),
        ("5", "退出", "Quit"),
    ]

    for key, zh, en in menu_items:
        if settings.language == 'zh':
            print(f"  {C_GREEN}{BOLD}[{key}]{RESET} {zh}")
        else:
            print(f"  {C_GREEN}{BOLD}[{key}]{RESET} {en}")

    print(f"\n  {C_WHITE}{DIM}难度: {diff_names[settings.difficulty]}  |  语言: {lang_names[settings.language]}{RESET}")
    print(f"  {C_WHITE}{DIM}Version 1.0 | 按 Q 退出{RESET}")


def draw_high_scores():
    """Draw the high scores screen."""
    clear_screen()
    print(HIDE_CURSOR)

    if settings.language == 'zh':
        print(f"\n{C_BRIGHT_YELLOW}{BOLD}  🏆 高分榜 TOP 10{RESET}\n")
    else:
        print(f"\n{C_BRIGHT_YELLOW}{BOLD}  🏆 High Scores TOP 10{RESET}\n")

    game = Game()
    scores = game.load_scores()

    if not scores:
        if settings.language == 'zh':
            print(f"  {C_WHITE}{DIM}暂无记录{RESET}")
        else:
            print(f"  {C_WHITE}{DIM}No scores yet{RESET}")
    else:
        if settings.language == 'zh':
            print(f"  {'排名':<6} {'玩家':<8} {'分数':<8} {'日期':<16}")
            print(f"  {'─'*38}")
        else:
            print(f"  {'Rank':<6} {'Name':<8} {'Score':<8} {'Date':<16}")
            print(f"  {'─'*38}")

        for i, s in enumerate(scores):
            rank = i + 1
            medal = ""
            if rank == 1:
                medal = C_BRIGHT_YELLOW + "🥇" + RESET + " "
            elif rank == 2:
                medal = C_WHITE + "🥈" + RESET + " "
            elif rank == 3:
                medal = C_RED + "🥉" + RESET + " "
            else:
                medal = f"  "

            color = C_BRIGHT_GREEN if rank <= 3 else C_WHITE
            print(f"  {medal}{color}{rank:<3} {s['name']:<8} {s['score']:<8} {s['date']:<16}{RESET}")

    if settings.language == 'zh':
        print(f"\n  {C_GREEN}[Enter]{RESET} 返回菜单")
    else:
        print(f"\n  {C_GREEN}[Enter]{RESET} Back to Menu")


def draw_how_to_play():
    """Draw the how-to-play screen."""
    clear_screen()
    print(HIDE_CURSOR)

    if settings.language == 'zh':
        print(f"\n{C_BRIGHT_YELLOW}{BOLD}  📖 游戏说明{RESET}\n")
        print(f"  {C_CYAN}连连看 (Mahjong Connect){RESET}")
        print(f"  {'─'*50}")
        print(f"  🎯 目标: 消除棋盘上所有相同的牌对")
        print(f"  {'─'*50}")
        print(f"  {C_BRIGHT_GREEN}操作说明:{RESET}")
        print(f"  {'─'*50}")
        print(f"  ↑↓←→ / WASD   移动光标选择方块")
        print(f"  Enter / Space  选择/取消选择方块")
        print(f"  H              提示 (剩余 {Game().max_hints} 次, 每次 -20分)")
        print(f"  S              洗牌 (剩余 {Game().max_shuffles} 次, 每次 -50分)")
        print(f"  R              重新开始游戏")
        print(f"  P              暂停/继续")
        print(f"  T              切换计时器显示")
        print(f"  Q              退出游戏")
        print(f"  {'─'*50}")
        print(f"  {C_BRIGHT_GREEN}连接规则:{RESET}")
        print(f"  • 两张相同的牌才能消除")
        print(f"  • 连接路径最多只能转弯2次")
        print(f"  • 路径只能经过空格或棋盘边界")
        print(f"  {'─'*50}")
        print(f"  {C_BRIGHT_GREEN}计分规则:{RESET}")
        print(f"  • 基础分: 100分 × 连击倍率")
        print(f"  • 时间奖励: 5秒内匹配 +50分")
        print(f"  • 连击: 3秒内连续匹配获得倍率加成")
        print(f"  • 提示: -20分/次")
        print(f"  • 洗牌: -50分/次")
        print(f"  {'─'*50}")
        print(f"  {C_BRIGHT_GREEN}难度说明:{RESET}")
        print(f"  • 简单: 6行×8列 (24对)")
        print(f"  • 普通: 8行×12列 (48对)")
        print(f"  • 困难: 10行×14列 (70对)")
    else:
        print(f"\n{C_BRIGHT_YELLOW}{BOLD}  📖 How to Play{RESET}\n")
        print(f"  {C_CYAN}Mahjong Connect (连连看){RESET}")
        print(f"  {'─'*50}")
        print(f"  🎯 Goal: Clear all matching tile pairs from the board")
        print(f"  {'─'*50}")
        print(f"  {C_BRIGHT_GREEN}Controls:{RESET}")
        print(f"  {'─'*50}")
        print(f"  ↑↓←→ / WASD   Move cursor")
        print(f"  Enter / Space  Select/deselect a tile")
        print(f"  H              Hint ({Game().max_hints} left, -20 pts each)")
        print(f"  S              Shuffle ({Game().max_shuffles} left, -50 pts each)")
        print(f"  R              Restart game")
        print(f"  P              Pause/Resume")
        print(f"  T              Toggle timer display")
        print(f"  Q              Quit game")
        print(f"  {'─'*50}")
        print(f"  {C_BRIGHT_GREEN}Connection Rules:{RESET}")
        print(f"  • Two identical tiles can be removed")
        print(f"  • Path can have at most 2 turns")
        print(f"  • Path can only go through empty cells or board boundary")
        print(f"  {'─'*50}")
        print(f"  {C_BRIGHT_GREEN}Scoring:{RESET}")
        print(f"  • Base: 100 pts × combo multiplier")
        print(f"  • Time bonus: match within 5s +50 pts")
        print(f"  • Combo: consecutive matches within 3s")
        print(f"  • Hint: -20 pts each")
        print(f"  • Shuffle: -50 pts each")
        print(f"  {'─'*50}")
        print(f"  {C_BRIGHT_GREEN}Difficulty:{RESET}")
        print(f"  • Easy: 6×8 grid (24 pairs)")
        print(f"  • Normal: 8×12 grid (48 pairs)")
        print(f"  • Hard: 10×14 grid (70 pairs)")

    if settings.language == 'zh':
        print(f"\n  {C_GREEN}[Enter]{RESET} 返回菜单")
    else:
        print(f"\n  {C_GREEN}[Enter]{RESET} Back to Menu")


def draw_settings():
    """Draw the settings screen."""
    clear_screen()
    print(HIDE_CURSOR)

    diff_names = {'easy': '简单 6×8', 'normal': '普通 8×12', 'hard': '困难 10×14'}
    diff_names_en = {'easy': 'Easy 6×8', 'normal': 'Normal 8×12', 'hard': 'Hard 10×14'}
    sound_str = '🔊 开' if settings.sound else '🔇 关'
    sound_str_en = 'ON' if settings.sound else 'OFF'
    lang_str = '中文' if settings.language == 'zh' else 'English'

    if settings.language == 'zh':
        print(f"\n{C_BRIGHT_YELLOW}{BOLD}  ⚙️ 设置{RESET}\n")
        print(f"  {C_GREEN}[1]{RESET} 声音: {sound_str}")
        print(f"  {C_GREEN}[2]{RESET} 语言: {lang_str}")
        print(f"  {C_GREEN}[3]{RESET} 难度: {diff_names[settings.difficulty]}")
        print(f"\n  {C_GREEN}[Enter]{RESET} 返回菜单")
    else:
        print(f"\n{C_BRIGHT_YELLOW}{BOLD}  ⚙️ Settings{RESET}\n")
        print(f"  {C_GREEN}[1]{RESET} Sound: {sound_str_en}")
        print(f"  {C_GREEN}[2]{RESET} Language: {lang_str}")
        print(f"  {C_GREEN}[3]{RESET} Difficulty: {diff_names_en[settings.difficulty]}")
        print(f"\n  {C_GREEN}[Enter]{RESET} Back to Menu")


# ── Game Screen ──────────────────────────────────────────────────────

def draw_board(game, cursor_r, cursor_c, selected_r, selected_c,
               timer_visible=True, flash_cells=None, path_cells=None):
    """Draw the game board with cursor, selection, and effects."""
    if flash_cells is None:
        flash_cells = set()
    if path_cells is None:
        path_cells = set()

    clear_screen()
    print(HIDE_CURSOR)

    # ── Status bar (top) ──────────────────────────────────────────
    diff_names = {'easy': '简单', 'normal': '普通', 'hard': '困难'}
    diff_str = diff_names.get(game.difficulty, '普通')

    timer_str = ""
    if timer_visible:
        elapsed = game.get_elapsed_time()
        timer_str = f" ⏱ {game.format_time(elapsed)}"

    remaining = game.get_remaining_tiles()
    total = game.total_tiles
    progress = int((total - remaining) / total * 20) if total > 0 else 0
    progress_bar = "█" * progress + "░" * (20 - progress)

    combo_str = ""
    if game.combo > 1:
        combo_str = f" 🔥 {game.combo}x连击"

    hints_left = game.max_hints - game.hints_used
    shuffles_left = game.max_shuffles - game.shuffles_used

    top_bar = (
        f"{C_BRIGHT_WHITE}{BOLD}"
        f"  🀄 连连看 [{diff_str}]  "
        f"| 分数: {game.score}"
        f"{C_BRIGHT_YELLOW}{combo_str}{RESET}"
        f"{C_BRIGHT_WHITE}"
        f"  | 提示: {hints_left}/{game.max_hints}"
        f"  | 洗牌: {shuffles_left}/{game.max_shuffles}"
        f"{timer_str}"
        f"{RESET}"
    )
    print(f"  {top_bar}")
    print(f"  {C_CYAN}{DIM}[{progress_bar}] {remaining}/{total}{RESET}")
    print()

    # ── Board ──────────────────────────────────────────────────────
    # Column headers
    header = "     "
    for c in range(game.cols):
        header += f" {c % 10:2d} "
    print(f"  {C_WHITE}{DIM}{header}{RESET}")

    for r in range(game.rows):
        # Row number
        row_str = f"  {C_WHITE}{DIM}{r:02d} {RESET}"

        for c in range(game.cols):
            tile = game.board[r][c]

            # Determine cell background/style
            bg = ""
            fg = ""
            symbol = "  "

            if (r, c) in flash_cells:
                # Flash effect
                bg = C_BG_BRIGHT_WHITE
                fg = C_BRIGHT_RED + BOLD
                symbol = "★ "
            elif (r, c) in path_cells:
                # Path highlight
                bg = C_BG_BRIGHT_CYAN
                fg = C_BRIGHT_WHITE + BOLD
                symbol = "◆ "
            elif (r, c) == (cursor_r, cursor_c):
                # Cursor
                bg = C_BG_BRIGHT_YELLOW
                fg = C_BRIGHT_BLACK + BOLD
                if tile == 0:
                    symbol = "▣ "
                else:
                    symbol = f"{game.get_tile_symbol(tile)} "
            elif (r, c) == (selected_r, selected_c):
                # Selected tile
                bg = C_BG_GREEN
                fg = C_BRIGHT_WHITE + BOLD
                symbol = f"{game.get_tile_symbol(tile)} "
            elif tile != 0:
                # Normal tile
                color = game.get_tile_color(tile)
                fg = color + BOLD
                symbol = f"{game.get_tile_symbol(tile)} "
            else:
                # Empty cell
                fg = DIM
                symbol = ". "

            row_str += f"{bg}{fg}{symbol}{RESET}"

        print(row_str)

    # ── Legend ─────────────────────────────────────────────────────
    print()
    print(f"  {C_WHITE}{DIM}{'─' * (game.cols * 4 + 4)}{RESET}")
    legend_items = []
    shown = set()
    for r in range(game.rows):
        for c in range(game.cols):
            t = game.board[r][c]
            if t != 0 and t not in shown:
                shown.add(t)
                color = game.get_tile_color(t)
                symbol = game.get_tile_symbol(t)
                legend_items.append(f"{color}{BOLD}{symbol}{RESET}")
    # Show legend in rows of 12
    for i in range(0, len(legend_items), 12):
        chunk = legend_items[i:i + 12]
        print(f"  {' '.join(chunk)}")

    # ── Bottom status bar ──────────────────────────────────────────
    print()
    print(f"  {C_WHITE}{DIM}{'─' * 60}{RESET}")
    controls = (
        f"  {C_GREEN}[↑↓←→/WASD]{RESET}移动 "
        f"{C_GREEN}[Enter/Space]{RESET}选择 "
        f"{C_GREEN}[H]{RESET}提示 "
        f"{C_GREEN}[S]{RESET}洗牌 "
        f"{C_GREEN}[R]{RESET}重开 "
        f"{C_GREEN}[P]{RESET}暂停 "
        f"{C_GREEN}[Q]{RESET}退出"
    )
    print(f"  {controls}")
    print()


def draw_paused(game):
    """Draw pause overlay."""
    elapsed = game.elapsed_time
    remaining = game.get_remaining_tiles()

    if settings.language == 'zh':
        pause_text = "⏸ 游戏暂停"
        info_text = f"已用时: {game.format_time(elapsed)}  |  剩余方块: {remaining}"
        continue_text = "按 P 继续游戏  |  按 Q 退出"
    else:
        pause_text = "⏸ PAUSED"
        info_text = f"Time: {game.format_time(elapsed)}  |  Tiles left: {remaining}"
        continue_text = "Press P to Resume  |  Press Q to Quit"

    print(f"\n  {C_BRIGHT_YELLOW}{BOLD}{pause_text}{RESET}\n")
    print(f"  {C_WHITE}{info_text}{RESET}\n")
    print(f"  {C_GREEN}{continue_text}{RESET}")


def draw_game_over(game, is_new_high_score=False):
    """Draw the game over screen."""
    clear_screen()
    print(HIDE_CURSOR)

    if game.get_remaining_tiles() == 0:
        art = WIN_ART
        color = C_BRIGHT_GREEN
        title = "🎉 恭喜通关！" if settings.language == 'zh' else "🎉 Congratulations!"
    else:
        art = GAME_OVER_ART
        color = C_BRIGHT_RED
        title = "游戏结束" if settings.language == 'zh' else "Game Over"

    print(color + BOLD)
    for line in art:
        print(f"  {line}")
    print(RESET)

    elapsed = game.get_elapsed_time()
    print(f"\n  {C_BRIGHT_WHITE}{BOLD}{title}{RESET}")
    print(f"\n  {C_CYAN}{'─'*40}{RESET}")
    print(f"  {C_WHITE}{BOLD}{'最终得分' if settings.language == 'zh' else 'Final Score'}: {C_BRIGHT_YELLOW}{game.score}{RESET}")
    print(f"  {C_WHITE}{BOLD}{'用时' if settings.language == 'zh' else 'Time'}: {C_BRIGHT_CYAN}{game.format_time(elapsed)}{RESET}")
    print(f"  {C_WHITE}{BOLD}{'消除对数' if settings.language == 'zh' else 'Matches'}: {C_BRIGHT_GREEN}{game.matches_made}{RESET}")
    print(f"  {C_CYAN}{'─'*40}{RESET}")

    if is_new_high_score:
        print(f"\n  {C_BRIGHT_YELLOW}{BOLD}{'🏆 新纪录！' if settings.language == 'zh' else '🏆 New High Score!'}{RESET}")
        return True

    if settings.language == 'zh':
        print(f"\n  {C_GREEN}[Enter]{RESET} 返回菜单  {C_GREEN}[R]{RESET} 重新开始")
    else:
        print(f"\n  {C_GREEN}[Enter]{RESET} Menu  {C_GREEN}[R]{RESET} Restart")

    return False


# ── Name Entry ───────────────────────────────────────────────────────

def draw_name_entry(score):
    """Draw name entry screen for high scores."""
    clear_screen()
    print(HIDE_CURSOR)

    print(f"\n  {C_BRIGHT_YELLOW}{BOLD}{'🏆 新纪录！' if settings.language == 'zh' else '🏆 New High Score!'}{RESET}")
    print(f"\n  {C_WHITE}{BOLD}{'得分' if settings.language == 'zh' else 'Score'}: {C_BRIGHT_GREEN}{score}{RESET}")

    if settings.language == 'zh':
        print(f"\n  {C_CYAN}{'请输入你的名字（最多3个字符）:'}{RESET}")
        print(f"  {C_CYAN}{'按 Enter 确认'}{RESET}")
    else:
        print(f"\n  {C_CYAN}{'Enter your name (max 3 characters):'}{RESET}")
        print(f"  {C_CYAN}{'Press Enter to confirm'}{RESET}")

    return input(f"\n  {C_BRIGHT_GREEN}{BOLD}> {RESET}").strip()[:3]


# ── Game Loop ────────────────────────────────────────────────────────

def run_game():
    """Main game loop."""
    game = Game(settings.difficulty)
    cursor_r, cursor_c = 0, 0
    selected_r, selected_c = -1, -1
    timer_visible = True
    flash_cells = set()
    flash_start = 0
    path_cells = set()
    path_start = 0
    path_duration = 0.5  # Show path for 0.5 seconds
    flash_duration = 0.3
    message = ""
    message_color = C_GREEN
    message_start = 0
    message_duration = 2.0
    need_auto_shuffle_msg = False

    while True:
        now = time.time()

        # Check if we need to show path/flash
        if path_cells and (now - path_start) > path_duration:
            path_cells = set()
        if flash_cells and (now - flash_start) > flash_duration:
            flash_cells = set()

        # Draw
        draw_board(game, cursor_r, cursor_c, selected_r, selected_c,
                   timer_visible, flash_cells, path_cells)

        if game.paused:
            draw_paused(game)

        # Show message
        if message and (now - message_start) < message_duration:
            print(f"  {message_color}{BOLD}{message}{RESET}")
        elif message:
            message = ""

        # Show auto-shuffle message
        if need_auto_shuffle_msg:
            if settings.language == 'zh':
                print(f"  {C_BRIGHT_YELLOW}{BOLD}🔄 无可用配对，自动洗牌！{RESET}")
            else:
                print(f"  {C_BRIGHT_YELLOW}{BOLD}🔄 No valid moves, auto shuffling!{RESET}")
            need_auto_shuffle_msg = False

        # Handle input
        key = get_key()

        if game.paused:
            if key in ('p', 'P'):
                game.toggle_pause()
            elif key in ('q', 'Q', '\x03'):
                return 'quit'
            continue

        # ── Key handling ──────────────────────────────────────────

        # Arrow keys / WASD
        if key in ('\x1b[A', 'w', 'W'):
            cursor_r = max(0, cursor_r - 1)
        elif key in ('\x1b[B', 's', 'S'):
            cursor_r = min(game.rows - 1, cursor_r + 1)
        elif key in ('\x1b[D', 'a', 'A'):
            cursor_c = max(0, cursor_c - 1)
        elif key in ('\x1b[C', 'd', 'D'):
            cursor_c = min(game.cols - 1, cursor_c + 1)

        # Enter / Space - select
        elif key in ('\r', '\n', ' '):
            tile = game.board[cursor_r][cursor_c]
            if tile == 0:
                # Empty cell - deselect
                selected_r, selected_c = -1, -1
                continue

            if selected_r == -1 and selected_c == -1:
                # First selection
                selected_r, selected_c = cursor_r, cursor_c
            elif selected_r == cursor_r and selected_c == cursor_c:
                # Deselect
                selected_r, selected_c = -1, -1
            else:
                # Attempt match
                result = game.make_match(selected_r, selected_c, cursor_r, cursor_c)
                if result and result['success']:
                    # Success!
                    play_sound('match')
                    flash_cells = {(selected_r, selected_c), (cursor_r, cursor_c)}
                    flash_start = now
                    path_cells = set(result.get('path', []))
                    path_start = now

                    # Show score message
                    if result['combo'] > 1:
                        msg = (f"✅ +{result['score']}分 (x{result['multiplier']}连击"
                               f"{' +时间奖励' if result['time_bonus'] > 0 else ''})")
                    else:
                        msg = f"✅ +{result['score']}分"
                    message = msg
                    message_color = C_BRIGHT_GREEN
                    message_start = now

                    selected_r, selected_c = -1, -1

                    # Check game over
                    if game.game_over:
                        break

                    # Check auto-shuffle
                    if result.get('auto_shuffled'):
                        need_auto_shuffle_msg = True

                else:
                    # Failed match
                    play_sound('fail')
                    if settings.language == 'zh':
                        message = "❌ 无法连接！"
                    else:
                        message = "❌ Cannot connect!"
                    message_color = C_BRIGHT_RED
                    message_start = now
                    selected_r, selected_c = -1, -1

        # H - Hint
        elif key in ('h', 'H'):
            if game.hints_used >= game.max_hints:
                if settings.language == 'zh':
                    message = "⚠️ 提示次数已用完！"
                else:
                    message = "⚠️ No hints remaining!"
                message_color = C_BRIGHT_RED
                message_start = now
            else:
                hint = game.use_hint()
                if hint:
                    (r1, c1), (r2, c2), path = hint
                    path_cells = set(path)
                    path_start = now
                    flash_cells = {(r1, c1), (r2, c2)}
                    flash_start = now
                    if settings.language == 'zh':
                        message = f"💡 提示: ({r1},{c1}) ↔ ({r2},{c2}) (-20分)"
                    else:
                        message = f"💡 Hint: ({r1},{c1}) ↔ ({r2},{c2}) (-20 pts)"
                    message_color = C_BRIGHT_CYAN
                    message_start = now
                else:
                    if settings.language == 'zh':
                        message = "⚠️ 没有可用的配对！"
                    else:
                        message = "⚠️ No valid pairs!"
                    message_color = C_BRIGHT_RED
                    message_start = now

        # S - Shuffle
        elif key in ('s', 'S'):
            if game.shuffles_used >= game.max_shuffles:
                if settings.language == 'zh':
                    message = "⚠️ 洗牌次数已用完！"
                else:
                    message = "⚠️ No shuffles remaining!"
                message_color = C_BRIGHT_RED
                message_start = now
            else:
                game.shuffle()
                play_sound('shuffle')
                selected_r, selected_c = -1, -1
                if settings.language == 'zh':
                    message = "🔄 已洗牌！(-50分)"
                else:
                    message = "🔄 Shuffled! (-50 pts)"
                message_color = C_BRIGHT_YELLOW
                message_start = now

        # R - Restart
        elif key in ('r', 'R'):
            return 'restart'

        # P - Pause
        elif key in ('p', 'P'):
            game.toggle_pause()

        # T - Toggle timer
        elif key in ('t', 'T'):
            timer_visible = not timer_visible

        # Q - Quit
        elif key in ('q', 'Q', '\x03'):
            return 'quit'

    # ── Game Over ──────────────────────────────────────────────────

    # Check for high score
    is_new = game.is_high_score()

    while True:
        draw_game_over(game, is_new)

        if is_new:
            name = draw_name_entry(game.score)
            if name:
                game.save_score(name)
            is_new = False
            continue

        key = get_key()

        if key in ('\r', '\n', ' '):
            return 'menu'
        elif key in ('r', 'R'):
            return 'restart'
        elif key in ('q', 'Q', '\x03'):
            return 'quit'


# ── Main ─────────────────────────────────────────────────────────────

def main():
    """Application entry point."""
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print(SHOW_CURSOR + RESET)
        clear_screen()
        print(f"\n  {C_CYAN}感谢游玩连连看！再见！{RESET}\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    state = 'menu'

    while True:
        if state == 'menu':
            draw_menu()
            key = get_key()

            if key == '1':
                state = 'game'
            elif key == '2':
                draw_high_scores()
                get_key()
            elif key == '3':
                draw_how_to_play()
                get_key()
            elif key == '4':
                while True:
                    draw_settings()
                    key = get_key()
                    if key == '1':
                        settings.toggle_sound()
                    elif key == '2':
                        settings.cycle_language()
                    elif key == '3':
                        settings.cycle_difficulty()
                    elif key in ('\r', '\n', ' '):
                        break
            elif key in ('5', 'q', 'Q', '\x03'):
                break

        elif state == 'game':
            result = run_game()
            if result == 'menu':
                state = 'menu'
            elif result == 'restart':
                continue  # Stay in game state, loop restarts
            elif result == 'quit':
                break

        elif state == 'quit':
            break

    # Clean exit
    print(SHOW_CURSOR + RESET)
    clear_screen()
    if settings.language == 'zh':
        print(f"\n  {C_CYAN}感谢游玩连连看！再见！{RESET}\n")
    else:
        print(f"\n  {C_CYAN}Thanks for playing Mahjong Connect! Goodbye!{RESET}\n")


if __name__ == '__main__':
    main()
