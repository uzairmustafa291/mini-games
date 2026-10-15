# sprites.py
import pygame
import random
import math
from config import *

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((38, 48), pygame.SRCALPHA)
        dark_outline = (8, 18, 32)
        center_x = self.image.get_width() // 2

        pygame.draw.circle(self.image, (0, 220, 255, 65), (center_x, 24), 19)

        # Draw an outlined person silhouette so the player reads clearly at game size.
        pygame.draw.circle(self.image, dark_outline, (center_x, 10), 9)
        pygame.draw.line(self.image, dark_outline, (center_x, 19), (center_x, 32), 12)
        pygame.draw.line(self.image, dark_outline, (center_x, 22), (6, 29), 10)
        pygame.draw.line(self.image, dark_outline, (center_x, 22), (32, 29), 10)
        pygame.draw.line(self.image, dark_outline, (center_x, 31), (11, 43), 10)
        pygame.draw.line(self.image, dark_outline, (center_x, 31), (27, 43), 10)

        pygame.draw.circle(self.image, (255, 255, 255), (center_x, 10), 6)
        pygame.draw.line(self.image, COLOR_PLAYER, (center_x, 19), (center_x, 32), 7)
        pygame.draw.line(self.image, COLOR_PLAYER, (center_x, 22), (6, 29), 6)
        pygame.draw.line(self.image, COLOR_PLAYER, (center_x, 22), (32, 29), 6)
        pygame.draw.line(self.image, COLOR_PLAYER, (center_x, 31), (11, 43), 6)
        pygame.draw.line(self.image, COLOR_PLAYER, (center_x, 31), (27, 43), 6)
        
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH // 2, HEIGHT // 2)
        self.speed = BASE_PLAYER_SPEED

    def update(self, keys):
        # Movement controls (Arrow keys or WASD)
        dx, dy = 0, 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:  dx = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:    dy = -self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:  dy = self.speed

        # Prevent faster diagonal movement
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.rect.x += dx
        self.rect.y += dy

        # Keep player strictly inside the screen borders
        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))


class Projectile(pygame.sprite.Sprite):
    def __init__(self, current_time):
        super().__init__()
        self.radius = random.randint(14, 22)
        image_size = self.radius * 2 + 8
        self.image = pygame.Surface((image_size, image_size), pygame.SRCALPHA)
        center = image_size // 2

        # Uneven angular segments give each projectile a rough stone silhouette.
        vertex_count = random.randint(7, 10)
        angle_offset = random.uniform(0, math.tau)
        points = []
        for index in range(vertex_count):
            angle = angle_offset + math.tau * index / vertex_count
            distance = self.radius * random.uniform(0.72, 1.0)
            points.append((
                round(center + math.cos(angle) * distance),
                round(center + math.sin(angle) * distance),
            ))

        stone_color = random.choice([
            (221, 145, 54),
            (237, 166, 66),
            (202, 126, 49),
            (231, 153, 75),
        ])
        outline_color = (73, 49, 32)
        highlight_color = (255, 218, 139)
        shadow_color = (130, 76, 34)

        pygame.draw.polygon(self.image, stone_color, points)
        pygame.draw.polygon(self.image, outline_color, points, width=3)
        pygame.draw.polygon(
            self.image,
            highlight_color,
            [points[0], points[1], (center, center)],
        )
        pygame.draw.line(
            self.image,
            shadow_color,
            (center, center),
            points[vertex_count // 2],
            width=1,
        )
        
        self.rect = self.image.get_rect()
        
        # Calculate scaling difficulty based on survival time
        speed_boost = 1.0 + (current_time * SPEED_SCALING_FACTOR)
        self.speed = random.uniform(BASE_BULLET_SPEED - 1, BASE_BULLET_SPEED + 2) * speed_boost

        # Randomly choose an outer edge to spawn from (Top, Bottom, Left, Right)
        edge = random.choice(['T', 'B', 'L', 'R'])
        if edge == 'T':
            self.rect.centerx = random.randint(0, WIDTH)
            self.rect.bottom = 0
            self.dx, self.dy = random.uniform(-0.5, 0.5), 1
        elif edge == 'B':
            self.rect.centerx = random.randint(0, WIDTH)
            self.rect.top = HEIGHT
            self.dx, self.dy = random.uniform(-0.5, 0.5), -1
        elif edge == 'L':
            self.rect.right = 0
            self.rect.centery = random.randint(0, HEIGHT)
            self.dx, self.dy = 1, random.uniform(-0.5, 0.5)
        else:
            self.rect.left = WIDTH
            self.rect.centery = random.randint(0, HEIGHT)
            self.dx, self.dy = -1, random.uniform(-0.5, 0.5)

        # Normalize direction vector so bullets fly at consistent speeds
        length = math.hypot(self.dx, self.dy)
        self.dx /= length
        self.dy /= length

    def update(self):
        self.rect.x += self.dx * self.speed
        self.rect.y += self.dy * self.speed

        # Delete the bullet once it flies fully off screen to preserve computer memory
        if (self.rect.right < -50 or self.rect.left > WIDTH + 50 or 
            self.rect.bottom < -50 or self.rect.top > HEIGHT + 50):
            self.kill()
