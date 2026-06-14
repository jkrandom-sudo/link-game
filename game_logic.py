"""
game_logic.py - Core logic for Mahjong Connect (连连看)
Handles board generation, path finding, scoring, and game state.
"""

import json
import os
import random
import time
from collections import deque
from datetime import datetime


# ── Tile display symbols ──────────────────────────────────────────────
# Map tile type ID -> display character
# Use numbers 1-70 with Chinese-style formatting
TILE_SYMBOLS = {}
for i in range(1, 71):
    TILE_SYMBOLS[i] = f"{i:02d}"

# ANSI color palette (cycling)
COLORS = [
    '\033[31m',  # Red
    '\033[32m',  # Green
    '\033[33m',  # Yellow
    '\033[34m',  # Blue
    '\033[35m',  # Magenta
    '\033[36m',  # Cyan
    '\033[91m',  # Bright Red
    '\033[92m',  # Bright Green
    '\033[93m',  # Bright Yellow
    '\033[94m',  # Bright Blue
    '\033[95m',  # Bright Magenta
    '\033[96m',  # Bright Cyan
]
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Directions: up, right, down, left
DIRS = [(-1, 0), (0, 1), (1, 0), (0, -1)]


class Game:
    """Core game logic for Mahjong Connect."""

    DIFFICULTIES = {
        'easy':   {'rows': 6,  'cols': 8,  'pairs': 24},
        'normal': {'rows': 8,  'cols': 12, 'pairs': 48},
        'hard':   {'rows': 10, 'cols': 14, 'pairs': 70},
    }

    SCORES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scores.json')

    def __init__(self, difficulty='normal'):
        self.difficulty = difficulty
        self.setup_board()
        self.reset_game_state()

    # ── Board Setup ────────────────────────────────────────────────────

    def setup_board(self):
        cfg = self.DIFFICULTIES.get(self.difficulty, self.DIFFICULTIES['normal'])
        self.rows = cfg['rows']
        self.cols = cfg['cols']
        self.pairs = cfg['pairs']
        self.total_tiles = self.pairs * 2
        self.generate_board()

    def generate_board(self):
        """Generate a random board with guaranteed at least one valid pair."""
        tile_types = list(range(1, self.pairs + 1)) * 2
        random.shuffle(tile_types)

        self.board = [[0] * self.cols for _ in range(self.rows)]
        idx = 0
        for r in range(self.rows):
            for c in range(self.cols):
                self.board[r][c] = tile_types[idx]
                idx += 1

        # Ensure at least one valid pair exists
        if not self.has_valid_pair():
            self._fix_solvability()

    def _fix_solvability(self):
        """Swap random tiles until at least one valid pair exists."""
        for _ in range(500):
            r1, c1 = random.randint(0, self.rows - 1), random.randint(0, self.cols - 1)
            r2, c2 = random.randint(0, self.rows - 1), random.randint(0, self.cols - 1)
            self.board[r1][c1], self.board[r2][c2] = self.board[r2][c2], self.board[r1][c1]
            if self.has_valid_pair():
                return
        # Last resort: rebuild
        self.generate_board()

    def reset_game_state(self):
        self.score = 0
        self.combo = 0
        self.hints_used = 0
        self.shuffles_used = 0
        self.max_hints = 5
        self.max_shuffles = 3
        self.last_match_time = None
        self.start_time = time.time()
        self.elapsed_time = 0
        self.matches_made = 0
        self.paused = False
        self.game_over = False
        self.show_path = None  # List of (r,c) for path animation
        self.show_path_time = 0
        self.flash_cells = []  # Cells to flash during removal
        self.flash_time = 0

    # ── Path Finding ──────────────────────────────────────────────────

    def _is_valid_cell(self, r, c, target):
        """Check if a cell is traversable (empty, boundary, or target)."""
        if (r, c) == target:
            return True
        # Outside board = boundary (always empty), but limit to 1 cell outside
        if r < -1 or r > self.rows or c < -1 or c > self.cols:
            return False
        if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
            return True
        # Inside board: must be empty
        return self.board[r][c] == 0

    def find_path(self, r1, c1, r2, c2):
        """
        BFS path finding with at most 2 turns.
        Returns list of (r,c) from start to end, or None if no path.
        """
        if (r1, c1) == (r2, c2):
            return None
        if self.board[r1][c1] == 0 or self.board[r2][c2] == 0:
            return None
        if self.board[r1][c1] != self.board[r2][c2]:
            return None

        target = (r2, c2)
        # BFS: (r, c, dir_idx, turns, path)
        visited = set()
        q = deque()

        # Initialize: from start, try all 4 directions
        for d_idx in range(4):
            nr = r1 + DIRS[d_idx][0]
            nc = c1 + DIRS[d_idx][1]
            if self._is_valid_cell(nr, nc, target):
                state = (nr, nc, d_idx, 0)
                if state not in visited:
                    visited.add(state)
                    q.append((nr, nc, d_idx, 0, [(r1, c1), (nr, nc)]))

        while q:
            r, c, d_idx, turns, path = q.popleft()

            # Reached target?
            if (r, c) == target:
                return path

            # 1) Continue in same direction
            nr = r + DIRS[d_idx][0]
            nc = c + DIRS[d_idx][1]
            if self._is_valid_cell(nr, nc, target):
                state = (nr, nc, d_idx, turns)
                if state not in visited:
                    visited.add(state)
                    q.append((nr, nc, d_idx, turns, path + [(nr, nc)]))

            # 2) Turn (if turns < 2)
            if turns < 2:
                for new_d_idx in range(4):
                    if new_d_idx == d_idx or new_d_idx == (d_idx + 2) % 4:
                        continue  # Skip same and opposite directions
                    nr = r + DIRS[new_d_idx][0]
                    nc = c + DIRS[new_d_idx][1]
                    if self._is_valid_cell(nr, nc, target):
                        state = (nr, nc, new_d_idx, turns + 1)
                        if state not in visited:
                            visited.add(state)
                            q.append((nr, nc, new_d_idx, turns + 1, path + [(nr, nc)]))

        return None

    # ── Board Queries ─────────────────────────────────────────────────

    def get_tile(self, r, c):
        """Get tile value at position, or 0 if empty or out of bounds."""
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.board[r][c]
        return 0

    def is_empty(self, r, c):
        """Check if a cell is empty."""
        return self.get_tile(r, c) == 0

    def get_remaining_tiles(self):
        """Count remaining tiles on the board."""
        count = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] != 0:
                    count += 1
        return count

    def has_valid_pair(self):
        """Check if at least one valid pair exists on the board."""
        # Group tiles by type
        positions = {}
        for r in range(self.rows):
            for c in range(self.cols):
                t = self.board[r][c]
                if t != 0:
                    positions.setdefault(t, []).append((r, c))

        for t, cells in positions.items():
            if len(cells) >= 2:
                for i in range(len(cells)):
                    for j in range(i + 1, len(cells)):
                        if self.find_path(cells[i][0], cells[i][1],
                                          cells[j][0], cells[j][1]):
                            return True
        return False

    def get_valid_pairs(self):
        """Return list of all valid ((r1,c1),(r2,c2)) pairs."""
        pairs = []
        positions = {}
        for r in range(self.rows):
            for c in range(self.cols):
                t = self.board[r][c]
                if t != 0:
                    positions.setdefault(t, []).append((r, c))

        for t, cells in positions.items():
            if len(cells) >= 2:
                for i in range(len(cells)):
                    for j in range(i + 1, len(cells)):
                        path = self.find_path(cells[i][0], cells[i][1],
                                              cells[j][0], cells[j][1])
                        if path:
                            pairs.append((cells[i], cells[j], path))
        return pairs

    def get_hint(self):
        """Return a valid pair ((r1,c1),(r2,c2), path) or None."""
        pairs = self.get_valid_pairs()
        if pairs:
            return random.choice(pairs)
        return None

    # ── Game Actions ──────────────────────────────────────────────────

    def make_match(self, r1, c1, r2, c2):
        """
        Attempt to match two tiles.
        Returns dict with result info, or None if invalid.
        """
        if self.board[r1][c1] == 0 or self.board[r2][c2] == 0:
            return None
        if self.board[r1][c1] != self.board[r2][c2]:
            return None

        path = self.find_path(r1, c1, r2, c2)
        if path is None:
            return None

        # Calculate score
        now = time.time()
        time_since_last = (now - self.last_match_time) if self.last_match_time else 999

        if time_since_last <= 3:
            self.combo += 1
        else:
            self.combo = 1

        multiplier = self.combo
        base_score = 100 * multiplier

        time_bonus = 0
        if time_since_last <= 5:
            time_bonus = 50

        total_score = base_score + time_bonus
        self.score += total_score
        self.matches_made += 1
        self.last_match_time = now

        # Remove tiles
        tile_type = self.board[r1][c1]
        self.board[r1][c1] = 0
        self.board[r2][c2] = 0

        # Check game over
        if self.get_remaining_tiles() == 0:
            self.game_over = True

        # Check if auto-shuffle needed
        if not self.game_over and not self.has_valid_pair():
            if self.shuffles_used < self.max_shuffles:
                self.shuffle()
                return {
                    'success': True,
                    'score': total_score,
                    'combo': self.combo,
                    'multiplier': multiplier,
                    'time_bonus': time_bonus,
                    'path': path,
                    'auto_shuffled': True,
                }

        return {
            'success': True,
            'score': total_score,
            'combo': self.combo,
            'multiplier': multiplier,
            'time_bonus': time_bonus,
            'path': path,
            'auto_shuffled': False,
        }

    def use_hint(self):
        """Use a hint. Returns hint info or None if no hints left / no valid pairs."""
        if self.hints_used >= self.max_hints:
            return None
        hint = self.get_hint()
        if hint is None:
            return None
        self.hints_used += 1
        self.score -= 20
        return hint

    def shuffle(self):
        """
        Shuffle remaining tiles. Returns True if successful.
        Auto-shuffle does not count toward the limit.
        """
        if self.shuffles_used >= self.max_shuffles:
            return False

        # Collect remaining tiles
        tiles = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] != 0:
                    tiles.append(self.board[r][c])

        if len(tiles) < 2:
            return False

        random.shuffle(tiles)

        idx = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] != 0:
                    self.board[r][c] = tiles[idx]
                    idx += 1

        self.shuffles_used += 1
        self.score -= 50

        # Ensure solvability after shuffle
        if not self.has_valid_pair():
            self._fix_solvability()

        return True

    def auto_shuffle(self):
        """
        Auto-shuffle when no moves remain. Does NOT count toward manual shuffle limit.
        """
        tiles = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] != 0:
                    tiles.append(self.board[r][c])

        if len(tiles) < 2:
            return False

        random.shuffle(tiles)

        idx = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] != 0:
                    self.board[r][c] = tiles[idx]
                    idx += 1

        # Ensure solvability
        if not self.has_valid_pair():
            self._fix_solvability()

        return True

    # ── Timer ─────────────────────────────────────────────────────────

    def get_elapsed_time(self):
        """Get elapsed time in seconds."""
        if self.paused:
            return self.elapsed_time
        if self.start_time is None:
            return 0
        return time.time() - self.start_time + self.elapsed_time

    def toggle_pause(self):
        """Toggle pause state."""
        if not self.paused:
            # Pausing: save elapsed time
            self.elapsed_time = self.get_elapsed_time()
        else:
            # Resuming: reset start time
            self.start_time = time.time()
        self.paused = not self.paused
        return self.paused

    # ── Score Persistence ─────────────────────────────────────────────

    def load_scores(self):
        """Load high scores from scores.json."""
        try:
            with open(self.SCORES_FILE, 'r', encoding='utf-8') as f:
                scores = json.load(f)
                # Sort by score descending
                scores.sort(key=lambda x: x['score'], reverse=True)
                return scores[:10]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_score(self, name, score=None):
        """Save a score to scores.json."""
        if score is None:
            score = self.score
        scores = self.load_scores()
        scores.append({
            'name': name[:3],
            'score': score,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        })
        scores.sort(key=lambda x: x['score'], reverse=True)
        scores = scores[:10]
        try:
            with open(self.SCORES_FILE, 'w', encoding='utf-8') as f:
                json.dump(scores, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def is_high_score(self, score=None):
        """Check if a score qualifies for the top 10."""
        if score is None:
            score = self.score
        scores = self.load_scores()
        if len(scores) < 10:
            return True
        return score > scores[-1]['score']

    # ── Utility ───────────────────────────────────────────────────────

    def get_tile_color(self, tile_type):
        """Get ANSI color code for a tile type."""
        return COLORS[tile_type % len(COLORS)]

    def get_tile_symbol(self, tile_type):
        """Get display symbol for a tile type."""
        return TILE_SYMBOLS.get(tile_type, f"{tile_type:02d}")

    def format_time(self, seconds):
        """Format seconds as MM:SS."""
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"
