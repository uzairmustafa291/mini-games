import random
import math
from array import array
from pathlib import Path

import pygame

from puzzleconfig import *
from puzzle_score_store import load_scores, record_score


BOARD_X = 42
BOARD_Y = 112
PANEL_X = 690
PANEL_Y = 112
PANEL_WIDTH = 390
PANEL_HEIGHT = 600
REFERENCE_SIZE = 340
SHUFFLE_MOVES = 20

COLOR_BG = (13, 17, 31)
COLOR_PANEL = (27, 32, 51)
COLOR_PANEL_EDGE = (68, 79, 106)
COLOR_ACCENT = (243, 194, 91)
COLOR_BUTTON = (113, 70, 165)
COLOR_BUTTON_HOVER = (139, 91, 194)
COLOR_MUTED = (188, 197, 217)

SOUND_SAMPLE_RATE = 22050


def make_sound(samples):
    pcm = array("h")
    for sample in samples:
        value = round(max(-1.0, min(1.0,  sample)) * 32767)
        pcm.extend((value, value))
    return pygame.mixer.Sound(buffer=pcm.tobytes())


def create_applause_sound():
    duration = 2.2
    samples = [0.0] * int(SOUND_SAMPLE_RATE * duration)
    clap_start = 0.0
    while clap_start < duration:
        start = int(clap_start * SOUND_SAMPLE_RATE)
        length = int(0.12 * SOUND_SAMPLE_RATE)
        for offset in range(min(length, len(samples) - start)):
            elapsed = offset / SOUND_SAMPLE_RATE
            envelope = math.exp(-elapsed * 35)
            samples[start + offset] += (
                random.uniform(-1, 1) * 0.55
                + math.sin(math.tau * 210 * elapsed) * 0.2
            ) * envelope * 0.5
        clap_start += random.uniform(0.08, 0.13)
    return make_sound(samples)


def create_tense_sound():
    duration = 1.2
    frame_count = int(SOUND_SAMPLE_RATE * duration)
    samples = []
    for frame in range(frame_count):
        elapsed = frame / SOUND_SAMPLE_RATE
        beat = elapsed % 0.6
        envelope = max(0.0, 1.0 - beat / 0.6) ** 2
        frequency = 82 if elapsed % 1.2 < 0.6 else 69
        tone = math.sin(math.tau * frequency * elapsed)
        overtone = math.sin(math.tau * frequency * 1.5 * elapsed) * 0.25
        samples.append((tone + overtone) * envelope * 0.32)
    return make_sound(samples)


def create_try_again_sound():
    duration = 0.9
    frame_count = int(SOUND_SAMPLE_RATE * duration)
    notes = ((440, 0.0), (349, 0.22), (262, 0.46))
    samples = []
    for frame in range(frame_count):
        elapsed = frame / SOUND_SAMPLE_RATE
        active_note = next(
            (note for note, start in reversed(notes) if elapsed >= start), None
        )
        if active_note is None:
            samples.append(0.0)
            continue
        note_start = next(start for note, start in notes if note == active_note)
        note_time = elapsed - note_start
        envelope = min(1.0, note_time * 35) * max(0.0, 1.0 - note_time / 0.38)
        samples.append(math.sin(math.tau * active_note * note_time) * envelope * 0.35)
    return make_sound(samples)


class SlidingPuzzle:
    def __init__(self):
        pygame.mixer.pre_init(SOUND_SAMPLE_RATE, -16, 2)
        pygame.init()
        self.applause_sound = create_applause_sound()
        self.tense_sound = create_tense_sound()
        self.try_again_sound = create_try_again_sound()
        self.tense_channel = pygame.mixer.Channel(0)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Magical Sliding Picture Puzzle")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 23, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 18)
        self.title_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.button_font = pygame.font.SysFont("Arial", 22, bold=True)
        self.entry_font = pygame.font.SysFont("Arial", 26)
        self.score_font = pygame.font.SysFont("Arial", 18)
        self.section_font = pygame.font.SysFont("Arial", 23, bold=True)
        self.board_rect = pygame.Rect(BOARD_X, BOARD_Y, WINDOW_SIZE, WINDOW_SIZE)

        self.load_and_prep_image()
        self.roll_number = ""
        self.player_name = ""
        self.active_field = "roll_number"
        self.storage_error = None
        try:
            self.scores = load_scores()
        except (OSError, ValueError) as error:
            self.scores = []
            self.storage_error = str(error)
        self.game_state = "STORAGE_ERROR" if self.storage_error else "PLAYER_ENTRY"
        self.moves = 0
        self.start_ticks = 0
        self.finish_time = 0.0
        self.score_saved = False
        self.result_won = False
        self.confetti = []
        self.reset_button = pygame.Rect(PANEL_X + 95, PANEL_Y + 520, 200, 52)
        self.start_button = pygame.Rect(PANEL_X + 65, PANEL_Y + 485, 260, 58)
        self.results_button = pygame.Rect(SCREEN_WIDTH // 2 - 130, 145, 260, 52)
        self.shuffle_puzzle()

    def load_and_prep_image(self):
        image_path = Path(__file__).with_name("puzzle_reference.png")
        if not image_path.is_file():
            raise FileNotFoundError(f"Puzzle picture not found: {image_path}")

        original_image = pygame.image.load(str(image_path)).convert()
        self.base_image = pygame.transform.smoothscale(
            original_image, (WINDOW_SIZE, WINDOW_SIZE)
        )
        self.reference_image = pygame.transform.smoothscale(
            original_image, (REFERENCE_SIZE, REFERENCE_SIZE)
        )

        self.tiles = {}
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                tile_id = row * GRID_SIZE + col
                crop_rect = pygame.Rect(
                    col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE
                )
                tile_surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
                tile_surface.blit(self.base_image, (0, 0), crop_rect)
                self.tiles[tile_id] = tile_surface

    def shuffle_puzzle(self):
        self.correct_layout = list(range(GRID_SIZE * GRID_SIZE))
        self.current_layout = self.correct_layout.copy()
        self.blank_index = len(self.current_layout) - 1
        previous_blank = None

        for _ in range(SHUFFLE_MOVES):
            candidates = [
                move for move in self.get_valid_moves()
                if move != previous_blank
            ]
            target = random.choice(candidates)
            previous_blank = self.blank_index
            self.swap_with_blank(target)

        if self.current_layout == self.correct_layout:
            self.swap_with_blank(self.get_valid_moves()[0])

        self.moves = 0

    def start_game(self):
        self.tense_channel.stop()
        self.shuffle_puzzle()
        self.start_ticks = pygame.time.get_ticks()
        self.score_saved = False
        self.game_state = "PLAYING"

    def save_current_score(self, won):
        if self.score_saved:
            return
        self.result_won = won
        try:
            self.scores = record_score(
                self.scores,
                self.roll_number,
                self.player_name,
                self.finish_time,
                won,
            )
            self.storage_error = None
        except (OSError, ValueError) as error:
            self.storage_error = str(error)
        self.score_saved = True

    def get_valid_moves(self):
        moves = []
        blank_row, blank_col = divmod(self.blank_index, GRID_SIZE)

        if blank_row > 0:
            moves.append(self.blank_index - GRID_SIZE)
        if blank_row < GRID_SIZE - 1:
            moves.append(self.blank_index + GRID_SIZE)
        if blank_col > 0:
            moves.append(self.blank_index - 1)
        if blank_col < GRID_SIZE - 1:
            moves.append(self.blank_index + 1)
        return moves

    def swap_with_blank(self, tile_index):
        self.current_layout[self.blank_index], self.current_layout[tile_index] = (
            self.current_layout[tile_index],
            self.current_layout[self.blank_index],
        )
        self.blank_index = tile_index

    def slide_tile(self, tile_index):
        if tile_index not in self.get_valid_moves():
            return

        self.swap_with_blank(tile_index)
        self.moves += 1
        if self.current_layout == self.correct_layout:
            self.finish_game()

    def finish_game(self):
        self.tense_channel.stop()
        self.applause_sound.play()
        self.finish_time = (pygame.time.get_ticks() - self.start_ticks) / 1000
        self.current_layout = self.correct_layout.copy()
        self.blank_index = len(self.current_layout) - 1
        self.save_current_score(won=True)
        self.confetti = [
            {
                "x": random.uniform(0, SCREEN_WIDTH),
                "y": random.uniform(-SCREEN_HEIGHT, 0),
                "speed": random.uniform(100, 260),
                "drift": random.uniform(-45, 45),
                "size": random.randint(5, 11),
                "color": random.choice([
                    (255, 90, 120),
                    (255, 205, 80),
                    (100, 220, 255),
                    (155, 110, 255),
                    (110, 240, 160),
                ]),
            }
            for _ in range(100)
        ]
        self.game_state = "RESULTS"

    def update_confetti(self, delta_time):
        for particle in self.confetti:
            particle["y"] += particle["speed"] * delta_time
            particle["x"] += particle["drift"] * delta_time
            if particle["y"] > SCREEN_HEIGHT:
                particle["y"] = random.uniform(-80, -10)
                particle["x"] = random.uniform(0, SCREEN_WIDTH)

    def draw_confetti(self):
        for particle in self.confetti:
            size = particle["size"]
            pygame.draw.ellipse(
                self.screen,
                particle["color"],
                pygame.Rect(round(particle["x"]), round(particle["y"]), size, size * 2),
            )

    def draw_button(self, rect, label, mouse_pos):
        color = COLOR_BUTTON_HOVER if rect.collidepoint(mouse_pos) else COLOR_BUTTON
        pygame.draw.rect(self.screen, color, rect, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_ACCENT, rect, width=2, border_radius=12)
        text = self.button_font.render(label, True, (255, 255, 255))
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_panel(self):
        panel_rect = pygame.Rect(PANEL_X, PANEL_Y, PANEL_WIDTH, PANEL_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect, border_radius=18)
        pygame.draw.rect(
            self.screen, COLOR_PANEL_EDGE, panel_rect, width=2, border_radius=18
        )

    def draw_board(self):
        pygame.draw.rect(self.screen, (7, 9, 18), self.board_rect, border_radius=8)

        for index, tile_id in enumerate(self.current_layout):
            row, col = divmod(index, GRID_SIZE)
            tile_rect = pygame.Rect(
                BOARD_X + col * TILE_SIZE,
                BOARD_Y + row * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE,
            )
            if index == self.blank_index and self.game_state != "WON":
                pygame.draw.rect(self.screen, (7, 9, 18), tile_rect)
            else:
                self.screen.blit(self.tiles[tile_id], tile_rect)
            pygame.draw.rect(self.screen, COLOR_ACCENT, tile_rect, width=3)

        pygame.draw.rect(self.screen, COLOR_ACCENT, self.board_rect, width=4)

    def draw_preview_screen(self, mouse_pos):
        self.screen.fill(COLOR_BG)
        title = self.title_font.render("MAGICAL SLIDING PUZZLE", True, COLOR_ACCENT)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 48)))

        self.draw_panel()
        image_rect = pygame.Rect(BOARD_X, BOARD_Y, WINDOW_SIZE, WINDOW_SIZE)
        self.screen.blit(self.base_image, image_rect)
        pygame.draw.rect(self.screen, COLOR_ACCENT, image_rect, width=4)

        heading = self.font.render("Study the picture", True, (255, 255, 255))
        self.screen.blit(heading, heading.get_rect(center=(PANEL_X + 195, 185)))
        lines = [
            "A tougher puzzle scrambled with",
            "20 valid tile moves!",
            "Slide the neighboring tiles into",
            "the empty space to solve it.",
            "The reference picture stays",
            "visible while you play.",
        ]
        for index, line in enumerate(lines):
            text = self.small_font.render(line, True, COLOR_MUTED)
            self.screen.blit(text, text.get_rect(center=(PANEL_X + 195, 235 + index * 31)))

        self.draw_button(self.start_button, "START PUZZLE", mouse_pos)

    def sorted_scores(self):
        return sorted(
            self.scores,
            key=lambda score: (
                not score["won"],
                score["seconds"] if score["won"] else -score["seconds"],
                score.get("played_at", ""),
            ),
        )

    def draw_scoreboards(self, top):
        ranked = self.sorted_scores()
        winners = [score for score in ranked if score["won"]]
        panels = (
            pygame.Rect(42, top, 500, SCREEN_HEIGHT - top - 24),
            pygame.Rect(562, top, 516, SCREEN_HEIGHT - top - 24),
        )
        headings = ("TOP 10 SCORES", f"WINNERS | {len(winners)}")
        for panel, heading in zip(panels, headings):
            pygame.draw.rect(self.screen, COLOR_PANEL, panel, border_radius=16)
            pygame.draw.rect(
                self.screen, COLOR_PANEL_EDGE, panel, width=2, border_radius=16
            )
            title = self.section_font.render(heading, True, COLOR_ACCENT)
            self.screen.blit(title, (panel.x + 18, panel.y + 14))

        top_scores = ranked[:10]
        if not top_scores:
            empty = self.small_font.render(
                "No scores yet. Be the first to solve it!",
                True,
                COLOR_MUTED,
            )
            self.screen.blit(empty, (panels[0].x + 18, panels[0].y + 60))
        for index, score in enumerate(top_scores):
            status = "SOLVED" if score["won"] else "TIME UP"
            name = score["name"][:20]
            line = self.score_font.render(
                f"{index + 1:>2}. {name} ({score['roll_number'][:12]})",
                True,
                (255, 255, 255),
            )
            result = self.score_font.render(
                f"{score['seconds']:.1f}s  {status}",
                True,
                COLOR_WIN if score["won"] else COLOR_MUTED,
            )
            y = panels[0].y + 56 + index * 36
            self.screen.blit(line, (panels[0].x + 18, y))
            self.screen.blit(
                result,
                (panels[0].right - result.get_width() - 18, y),
            )

        if not winners:
            empty = self.small_font.render(
                "No winners yet. Can you restore the picture?",
                True,
                COLOR_MUTED,
            )
            self.screen.blit(empty, (panels[1].x + 18, panels[1].y + 60))
        for index, score in enumerate(winners[:10]):
            line = self.score_font.render(
                f"{index + 1:>2}. {score['name'][:24]} ({score['roll_number'][:12]})",
                True,
                (255, 255, 255),
            )
            result = self.score_font.render(
                f"{score['seconds']:.1f}s",
                True,
                COLOR_WIN,
            )
            y = panels[1].y + 56 + index * 36
            self.screen.blit(line, (panels[1].x + 18, y))
            self.screen.blit(
                result,
                (panels[1].right - result.get_width() - 18, y),
            )

    def draw_player_entry_screen(self):
        self.screen.fill(COLOR_BG)
        title = self.title_font.render("MAGICAL SLIDING PUZZLE", True, COLOR_ACCENT)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 42)))
        subtitle = self.font.render("Enter your details before you play", True, COLOR_MUTED)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 83)))

        fields = (
            ("ROLL NUMBER", "roll_number", self.roll_number, SCREEN_WIDTH // 2 - 250),
            ("NAME", "name", self.player_name, SCREEN_WIDTH // 2 + 250),
        )
        for label, field, value, center_x in fields:
            label_image = self.small_font.render(label, True, COLOR_MUTED)
            self.screen.blit(label_image, label_image.get_rect(center=(center_x, 119)))
            box = pygame.Rect(0, 0, 430, 48)
            box.center = (center_x, 157)
            border = COLOR_ACCENT if self.active_field == field else COLOR_PANEL_EDGE
            pygame.draw.rect(self.screen, COLOR_PANEL, box, border_radius=9)
            pygame.draw.rect(self.screen, border, box, width=2, border_radius=9)
            text = self.entry_font.render(value or "Type here...", True, (255, 255, 255) if value else COLOR_MUTED)
            self.screen.blit(text, (box.x + 13, box.y + 8))

        hint = self.small_font.render(
            "Enter to continue | Tab to switch fields | Scores saved automatically",
            True,
            COLOR_ACCENT,
        )
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 203)))
        self.draw_scoreboards(top=232)

    def draw_results_screen(self):
        self.screen.fill(COLOR_BG)
        title_text = "PUZZLE SOLVED!" if self.result_won else "TIME IS UP"
        title_color = COLOR_WIN if title_text == "PUZZLE SOLVED!" else COLOR_FAIL
        title = self.title_font.render(title_text, True, title_color)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 42)))
        details = self.font.render(
            f"{self.player_name} | Roll no. {self.roll_number} | "
            f"{self.finish_time:.1f}s | {self.moves} moves",
            True,
            (255, 255, 255),
        )
        self.screen.blit(details, details.get_rect(center=(SCREEN_WIDTH // 2, 91)))
        self.draw_button(self.results_button, "PLAY AS NEW PLAYER", pygame.mouse.get_pos())
        self.draw_scoreboards(top=232)
        if self.storage_error:
            warning = self.small_font.render(
                f"Score could not be saved: {self.storage_error[:90]}",
                True,
                COLOR_FAIL,
            )
            self.screen.blit(warning, warning.get_rect(center=(SCREEN_WIDTH // 2, 211)))

    def draw_storage_error(self):
        self.screen.fill(COLOR_BG)
        title = self.title_font.render("SCORE FILE ERROR", True, COLOR_FAIL)
        message = self.small_font.render(
            f"Could not load puzzle_scores.json: {self.storage_error[:100]}",
            True,
            (255, 255, 255),
        )
        hint = self.small_font.render(
            "Fix the score file and restart the game.",
            True,
            COLOR_MUTED,
        )
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 300)))
        self.screen.blit(message, message.get_rect(center=(SCREEN_WIDTH // 2, 360)))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 405)))

    def draw_game_screen(self, current_time, mouse_pos):
        self.screen.fill(COLOR_BG)
        title = self.title_font.render("MAGICAL SLIDING PUZZLE", True, COLOR_ACCENT)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 48)))
        self.draw_board()
        self.draw_panel()

        label = self.font.render("REFERENCE PICTURE", True, COLOR_ACCENT)
        self.screen.blit(label, label.get_rect(center=(PANEL_X + 195, PANEL_Y + 40)))
        image_rect = pygame.Rect(
            PANEL_X + 25, PANEL_Y + 65, REFERENCE_SIZE, REFERENCE_SIZE
        )
        self.screen.blit(self.reference_image, image_rect)
        pygame.draw.rect(self.screen, COLOR_ACCENT, image_rect, width=3)

        if self.game_state == "PLAYING":
            time_left = max(0, TIME_LIMIT - current_time)
            timer_color = COLOR_FAIL if time_left <= 10 else (255, 255, 255)
            timer = self.font.render(f"TIME LEFT: {time_left:04.1f}s", True, timer_color)
            status = f"Tiles moved: {self.moves}"
            instruction = "Click a tile beside the empty space."
        elif self.game_state == "WON":
            timer = self.font.render("PICTURE RESTORED!", True, COLOR_WIN)
            status = f"Solved in {self.finish_time:.1f} seconds!"
            instruction = "Start a fresh puzzle with Reset."
        else:
            timer = self.font.render("TIME IS UP!", True, COLOR_FAIL)
            status = f"Tiles moved: {self.moves}"
            instruction = "Try again and beat the clock."

        self.screen.blit(timer, timer.get_rect(center=(PANEL_X + 195, PANEL_Y + 435)))
        status_text = self.small_font.render(status, True, COLOR_MUTED)
        self.screen.blit(
            status_text, status_text.get_rect(center=(PANEL_X + 195, PANEL_Y + 467))
        )
        instruction_text = self.small_font.render(instruction, True, COLOR_MUTED)
        self.screen.blit(
            instruction_text,
            instruction_text.get_rect(center=(PANEL_X + 195, PANEL_Y + 500)),
        )
        self.draw_button(self.reset_button, "RESET PUZZLE", mouse_pos)

    def run(self):
        while True:
            mouse_pos = pygame.mouse.get_pos()
            current_time = 0.0
            if self.game_state == "PLAYING":
                current_time = (pygame.time.get_ticks() - self.start_ticks) / 1000
                if current_time >= TIME_LIMIT:
                    self.tense_channel.stop()
                    self.try_again_sound.play()
                    self.finish_time = TIME_LIMIT
                    self.save_current_score(won=False)
                    self.game_state = "RESULTS"
                    current_time = TIME_LIMIT
                elif TIME_LIMIT - current_time <= 10 and not self.tense_channel.get_busy():
                    self.tense_channel.play(self.tense_sound, loops=-1)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if self.game_state == "PLAYER_ENTRY" and event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return
                    if event.key == pygame.K_TAB:
                        self.active_field = (
                            "name" if self.active_field == "roll_number" else "roll_number"
                        )
                    elif event.key == pygame.K_RETURN:
                        if self.roll_number.strip() and self.player_name.strip():
                            self.roll_number = self.roll_number.strip()
                            self.player_name = self.player_name.strip()
                            self.game_state = "PREVIEW"
                    elif event.key == pygame.K_BACKSPACE:
                        if self.active_field == "roll_number":
                            self.roll_number = self.roll_number[:-1]
                        else:
                            self.player_name = self.player_name[:-1]
                    elif event.unicode.isprintable():
                        if self.active_field == "roll_number" and len(self.roll_number) < 24:
                            self.roll_number += event.unicode
                        elif self.active_field == "name" and len(self.player_name) < 32:
                            self.player_name += event.unicode

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.game_state == "PREVIEW" and self.start_button.collidepoint(event.pos):
                        self.start_game()
                    elif self.game_state == "RESULTS" and self.results_button.collidepoint(event.pos):
                        self.roll_number = ""
                        self.player_name = ""
                        self.active_field = "roll_number"
                        self.game_state = "PLAYER_ENTRY"
                    elif self.game_state == "PLAYING" and self.reset_button.collidepoint(event.pos):
                        self.start_game()
                    elif self.game_state == "PLAYING" and self.board_rect.collidepoint(event.pos):
                        col = (event.pos[0] - BOARD_X) // TILE_SIZE
                        row = (event.pos[1] - BOARD_Y) // TILE_SIZE
                        self.slide_tile(row * GRID_SIZE + col)

            if self.game_state == "PLAYER_ENTRY":
                self.draw_player_entry_screen()
                self.clock.tick(FPS)
            elif self.game_state == "STORAGE_ERROR":
                self.draw_storage_error()
                self.clock.tick(FPS)
            elif self.game_state == "RESULTS":
                self.draw_results_screen()
                if self.result_won:
                    delta_time = self.clock.tick(FPS) / 1000
                    self.update_confetti(delta_time)
                    self.draw_confetti()
                else:
                    self.clock.tick(FPS)
            elif self.game_state == "PREVIEW":
                self.draw_preview_screen(mouse_pos)
                self.clock.tick(FPS)
            else:
                self.draw_game_screen(current_time, mouse_pos)
                self.clock.tick(FPS)
            pygame.display.flip()


if __name__ == "__main__":
    SlidingPuzzle().run()
