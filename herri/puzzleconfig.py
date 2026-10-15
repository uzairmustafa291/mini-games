# puzzle_config.py
import pygame

# Screen Setup
WINDOW_SIZE = 600
SCREEN_WIDTH = 1120
SCREEN_HEIGHT = 760
FPS = 60

# Puzzle Dimensions
GRID_SIZE = 3      # 3x3 grid (Change to 4 for a harder 4x4 challenge)
TILE_SIZE = WINDOW_SIZE // GRID_SIZE

# Target Time Limit Threshold
TIME_LIMIT = 60.0

# Theme Colors
COLOR_BG = (15, 13, 25)       # Dark Magical Violet
COLOR_GRID = (212, 175, 55)   # Gryffindor / Hogwarts Gold
COLOR_TEXT = (255, 255, 255)
COLOR_WIN = (50, 205, 50)
COLOR_FAIL = (220, 20, 60)
