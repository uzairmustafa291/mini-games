# config.py
import pygame

# Screen Configuration
WIDTH = 1280
HEIGHT = 720
FPS = 60

# Game Progression & Goals
WIN_THRESHOLD = 45.0  # Seconds to survive to win the prize!
BASE_PLAYER_SPEED = 5

# Dynamic Difficulty Constants
BASE_BULLET_SPEED = 4.0
SPEED_SCALING_FACTOR = 0.025  # Gradual speed increase across the longer round
SPAWN_SCALING_FACTOR = 0.11  # Slightly more frequent spawns as the round progresses

# Aesthetics (Color Palette)
COLOR_BACKGROUND = (10, 10, 15)
COLOR_PLAYER = (0, 255, 255)       # Neon Blue
COLOR_BULLET = (112, 116, 122)    # Stone Gray
COLOR_TEXT = (255, 255, 255)       # White
COLOR_WIN = (0, 255, 100)          # Cyber Green