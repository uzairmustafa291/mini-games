# main.py
import pygame
import sys
import random
import math
from array import array
from config import *
from sprites import Player, Projectile
from score_store import load_scores, record_score


def create_applause_sound():
    sample_rate = 44100
    duration = 2.4
    total_frames = int(sample_rate * duration)
    audio = [0.0] * total_frames

    clap_start = 0.0
    while clap_start < duration:
        start_frame = int(clap_start * sample_rate)
        clap_frames = int(sample_rate * 0.11)
        phase = random.uniform(0, math.tau)
        for offset in range(min(clap_frames, total_frames - start_frame)):
            elapsed = offset / sample_rate
            envelope = math.exp(-elapsed * 38)
            noise = random.uniform(-1, 1) * envelope
            body = math.sin(2 * math.pi * 190 * elapsed + phase) * envelope * 0.25
            audio[start_frame + offset] += (noise * 0.65 + body) * 0.55
        clap_start += random.uniform(0.09, 0.14)

    samples = array("h")
    for sample in audio:
        value = round(max(-1.0, min(1.0, sample)) * 32767)
        samples.extend((value, value))
    return pygame.mixer.Sound(buffer=samples.tobytes())


def create_background():
    background = pygame.Surface((WIDTH, HEIGHT))
    top_color = (17, 29, 47)
    bottom_color = (28, 44, 63)

    for y in range(HEIGHT):
        blend = y / max(HEIGHT - 1, 1)
        color = tuple(
            round(top + (bottom - top) * blend)
            for top, bottom in zip(top_color, bottom_color)
        )
        pygame.draw.line(background, color, (0, y), (WIDTH, y))

    grid_color = (31, 48, 68)
    for x in range(0, WIDTH, 100):
        pygame.draw.line(background, grid_color, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 100):
        pygame.draw.line(background, grid_color, (0, y), (WIDTH, y), 1)

    return background


def draw_scoreboards(screen, fonts, scores, top):
    panel_font, row_font = fonts
    panel_width = (WIDTH - 100) // 2
    panels = [
        pygame.Rect(32, top, panel_width, HEIGHT - top - 28),
        pygame.Rect(68 + panel_width, top, panel_width, HEIGHT - top - 28),
    ]
    ranked_scores = sorted(
        scores,
        key=lambda score: (-score["seconds"], score.get("played_at", "")),
    )
    top_scores = ranked_scores[:10]
    winners = [score for score in ranked_scores if score["won"]]
    displayed_winners = winners[:8]

    for panel in panels:
        pygame.draw.rect(screen, (15, 27, 43), panel, border_radius=16)
        pygame.draw.rect(screen, (48, 71, 94), panel, width=2, border_radius=16)

    for panel, heading in zip(panels, ("TOP 10 SCORES", f"WINNERS | {len(winners)}")):
        label = panel_font.render(heading, True, COLOR_PLAYER)
        screen.blit(label, (panel.x + 20, panel.y + 14))

    def fit_text(text, font, max_width):
        while text and font.size(text)[0] > max_width:
            text = text[:-1]
        return text

    if not top_scores:
        empty = row_font.render("No scores yet. Set the first record!", True, (167, 184, 202))
        screen.blit(empty, (panels[0].x + 20, panels[0].y + 62))
    else:
        for index, score in enumerate(top_scores):
            name = fit_text(score["name"], row_font, 250)
            text = f"{index + 1:>2}. {name} ({score['roll_number']})"
            line = row_font.render(text, True, COLOR_TEXT)
            value = row_font.render(f"{score['seconds']:.2f}s", True, (160, 224, 255))
            y = panels[0].y + 57 + index * 25
            screen.blit(line, (panels[0].x + 20, y))
            screen.blit(value, (panels[0].right - value.get_width() - 20, y))

    if not winners:
        empty = row_font.render("Nobody has crossed the finish line yet.", True, (167, 184, 202))
        screen.blit(empty, (panels[1].x + 20, panels[1].y + 62))
    else:
        for index, score in enumerate(displayed_winners):
            name = fit_text(score["name"], row_font, 290)
            line = row_font.render(
                f"{index + 1:>2}. {name} ({score['roll_number']})",
                True,
                COLOR_TEXT,
            )
            value = row_font.render(f"{score['seconds']:.2f}s", True, COLOR_WIN)
            y = panels[1].y + 57 + index * 25
            screen.blit(line, (panels[1].x + 20, y))
            screen.blit(value, (panels[1].right - value.get_width() - 20, y))
        if len(winners) > len(displayed_winners):
            more = row_font.render(
                f"+ {len(winners) - len(displayed_winners)} more winner(s)",
                True,
                (167, 184, 202),
            )
            screen.blit(more, (panels[1].x + 20, panels[1].bottom - 32))


def player_entry_screen(screen, background, clock, scores, fonts):
    title_font, ui_font, input_font, panel_font, row_font = fonts
    roll_number = ""
    name = ""
    active_field = "roll_number"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_TAB:
                    active_field = "name" if active_field == "roll_number" else "roll_number"
                elif event.key == pygame.K_RETURN:
                    if roll_number.strip() and name.strip():
                        return roll_number.strip(), name.strip()
                elif event.key == pygame.K_BACKSPACE:
                    if active_field == "roll_number":
                        roll_number = roll_number[:-1]
                    else:
                        name = name[:-1]
                elif event.unicode.isprintable():
                    if active_field == "roll_number" and len(roll_number) < 24:
                        roll_number += event.unicode
                    elif active_field == "name" and len(name) < 32:
                        name += event.unicode

        screen.blit(background, (0, 0))
        title = title_font.render("SURVIVAL CHALLENGE", True, COLOR_TEXT)
        subtitle = ui_font.render("Enter your details to start a run", True, (167, 184, 202))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 48)))
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 105)))

        for label, value, field, center_x in (
            ("ROLL NUMBER", roll_number, "roll_number", WIDTH // 2 - 220),
            ("NAME", name, "name", WIDTH // 2 + 220),
        ):
            label_surface = panel_font.render(label, True, (167, 184, 202))
            screen.blit(label_surface, label_surface.get_rect(center=(center_x, 157)))
            box = pygame.Rect(0, 0, 390, 54)
            box.center = (center_x, 207)
            border = COLOR_PLAYER if active_field == field else (65, 86, 108)
            pygame.draw.rect(screen, (18, 31, 48), box, border_radius=10)
            pygame.draw.rect(screen, border, box, width=2, border_radius=10)
            value_surface = input_font.render(
                value or "Type here...",
                True,
                COLOR_TEXT if value else (105, 124, 144),
            )
            screen.blit(value_surface, (box.x + 14, box.y + 11))

        instruction = ui_font.render(
            "Press Enter to play  |  Tab to switch fields  |  Esc to quit",
            True,
            COLOR_PLAYER,
        )
        screen.blit(instruction, instruction.get_rect(center=(WIDTH // 2, 273)))
        draw_scoreboards(screen, (panel_font, row_font), scores, 318)
        pygame.display.flip()
        clock.tick(FPS)


def draw_storage_error(screen, background, clock, error):
    title_font = pygame.font.SysFont("Arial", 46, bold=True)
    ui_font = pygame.font.SysFont("Arial", 23)
    message = f"Score storage could not be loaded: {error}"
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN)
            ):
                return
        screen.blit(background, (0, 0))
        title = title_font.render("SCORE FILE ERROR", True, (255, 130, 130))
        detail = ui_font.render(message[:110], True, COLOR_TEXT)
        hint = ui_font.render("Fix the scores.json file, then restart the game.", True, (167, 184, 202))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 55)))
        screen.blit(detail, detail.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 42)))
        pygame.display.flip()
        clock.tick(FPS)


def main():
    pygame.mixer.pre_init(44100, -16, 2)
    pygame.init()
    applause_sound = create_applause_sound()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("THE IMPOSSIBLE 60S THRESHOLD CHALLENGE")
    clock = pygame.time.Clock()
    background = create_background()

    # System Fonts Setup
    ui_font = pygame.font.SysFont("Arial", 32, bold=True)
    title_font = pygame.font.SysFont("Arial", 64, bold=True)
    retry_font = pygame.font.SysFont("Arial", 38, bold=True)
    input_font = pygame.font.SysFont("Arial", 27)
    panel_font = pygame.font.SysFont("Arial", 24, bold=True)
    row_font = pygame.font.SysFont("Arial", 19)
    entry_fonts = (title_font, ui_font, input_font, panel_font, row_font)

    # High score tracker initialized to 0.0 seconds
    session_high_score = 0.0

    try:
        scores = load_scores()
    except (OSError, ValueError) as error:
        draw_storage_error(screen, background, clock, error)
        pygame.quit()
        return

    while True:
        roll_number, player_name = player_entry_screen(
            screen,
            background,
            clock,
            scores,
            entry_fonts,
        )

        # Create fresh sprite groupings for a clean run/restart loop
        bullets = pygame.sprite.Group()
        
        player = Player()

        start_ticks = pygame.time.get_ticks()
        spawn_counter = 0
        game_state = "PLAYING"  # States: PLAYING, CRASHED, WINNER
        final_survival_time = 0.0

        # Core Active State Loop
        while game_state == "PLAYING":
            # 1. Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            # 2. Time Tracking
            current_time = (pygame.time.get_ticks() - start_ticks) / 1000.0
            
            if current_time >= WIN_THRESHOLD:
                game_state = "WINNER"
                final_survival_time = WIN_THRESHOLD
                break

            # 3. Dynamic Enemy Spawning Mechanics
            # Target spawn delay ticks lower as time progresses
            target_spawn_delay = max(3, 20 - int(current_time * SPAWN_SCALING_FACTOR))
            spawn_counter += 1
            if spawn_counter >= target_spawn_delay:
                bullet = Projectile(current_time)
                bullets.add(bullet)
                spawn_counter = 0

            # 4. Updates
            keys = pygame.key.get_pressed()
            player.update(keys)
            bullets.update()

            # 5. Collision Checks
            # Uses Pygame's built-in rapid rect collision masking
            if pygame.sprite.spritecollideany(player, bullets):
                game_state = "CRASHED"
                final_survival_time = current_time
                if final_survival_time > session_high_score:
                    session_high_score = final_survival_time

            # 6. Render Environment & Sprites
            screen.blit(background, (0, 0))
            bullets.draw(screen)
            screen.blit(player.image, player.rect)

            # Live UI Scoreboards
            timer_lbl = ui_font.render(f"TIME: {current_time:.2f}s / {WIN_THRESHOLD}s", True, COLOR_TEXT)
            high_lbl = ui_font.render(f"SESSION BEST: {session_high_score:.2f}s", True, COLOR_PLAYER)
            screen.blit(timer_lbl, (20, 20))
            screen.blit(high_lbl, (WIDTH - high_lbl.get_width() - 20, 20))

            pygame.display.flip()
            clock.tick(FPS)

        session_high_score = max(session_high_score, final_survival_time)
        storage_error = None
        try:
            scores = record_score(
                scores,
                roll_number,
                player_name,
                final_survival_time,
                game_state == "WINNER",
            )
        except (OSError, ValueError) as error:
            storage_error = str(error)

        # Post-Game Intermission Loop (Handles screens for Crashes and Victories)
        bubbles = []
        bubble_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        bubble_spawn_timer = 0.0
        animation_start = pygame.time.get_ticks()

        if game_state == "WINNER":
            applause_sound.play()
            bubbles = [
                {
                    "x": random.randint(0, WIDTH),
                    "y": random.randint(-HEIGHT, 0),
                    "radius": random.randint(8, 22),
                    "speed": random.uniform(160, 300),
                    "drift": random.uniform(-35, 35),
                }
                for _ in range(36)
            ]

        while game_state in ["CRASHED", "WINNER"]:
            delta_time = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    game_state = "RESTART"

            screen.blit(background, (0, 0))

            if game_state == "CRASHED":
                elapsed = (pygame.time.get_ticks() - animation_start) / 1000.0
                pulse = (math.sin(elapsed * 4) + 1) / 2
                retry_color = (255, round(90 + pulse * 100), round(90 + pulse * 100))
                msg_main = title_font.render("GAME OVER", True, COLOR_BULLET)
                msg_sub = ui_font.render(f"You survived: {final_survival_time:.2f} seconds", True, COLOR_TEXT)
                player_line = ui_font.render(
                    f"{player_name}  |  Roll no. {roll_number}",
                    True,
                    COLOR_PLAYER,
                )
                msg_hint = retry_font.render("TRY AGAIN!", True, retry_color)
                
                screen.blit(msg_main, msg_main.get_rect(center=(WIDTH // 2, 45)))
                screen.blit(msg_sub, msg_sub.get_rect(center=(WIDTH // 2, 105)))
                screen.blit(player_line, player_line.get_rect(center=(WIDTH // 2, 151)))
                screen.blit(msg_hint, msg_hint.get_rect(center=(WIDTH // 2, 207)))

            elif game_state == "WINNER":
                bubble_spawn_timer += delta_time
                while bubble_spawn_timer >= 0.045:
                    bubble_spawn_timer -= 0.045
                    bubbles.append({
                        "x": random.randint(0, WIDTH),
                        "y": -24,
                        "radius": random.randint(8, 22),
                        "speed": random.uniform(160, 300),
                        "drift": random.uniform(-35, 35),
                    })

                bubble_layer.fill((0, 0, 0, 0))
                for bubble in bubbles:
                    bubble["y"] += bubble["speed"] * delta_time
                    bubble["x"] += bubble["drift"] * delta_time
                    radius = bubble["radius"]
                    center = (round(bubble["x"]), round(bubble["y"]))
                    pygame.draw.circle(bubble_layer, (80, 255, 190, 35), center, radius)
                    pygame.draw.circle(bubble_layer, (110, 255, 205, 150), center, radius, 2)
                    pygame.draw.circle(
                        bubble_layer,
                        (220, 255, 245, 190),
                        (center[0] - radius // 3, center[1] - radius // 3),
                        max(2, radius // 5),
                    )
                bubbles = [bubble for bubble in bubbles if bubble["y"] < HEIGHT + bubble["radius"]]
                screen.blit(bubble_layer, (0, 0))

                msg_main = title_font.render("YOU WON THE GAME", True, COLOR_WIN)
                msg_sub = ui_font.render(
                    f"{player_name}  |  Roll no. {roll_number}",
                    True,
                    COLOR_TEXT,
                )
                msg_hint = ui_font.render("Press Enter to play again", True, COLOR_PLAYER)
                
                screen.blit(msg_main, msg_main.get_rect(center=(WIDTH // 2, 55)))
                screen.blit(msg_sub, msg_sub.get_rect(center=(WIDTH // 2, 119)))
                screen.blit(msg_hint, msg_hint.get_rect(center=(WIDTH // 2, 190)))

            if storage_error:
                warning = ui_font.render(
                    f"Score could not be saved: {storage_error[:72]}",
                    True,
                    (255, 145, 145),
                )
                screen.blit(warning, warning.get_rect(center=(WIDTH // 2, 252)))
            elif game_state == "CRASHED":
                instruction = ui_font.render("Press Enter to play again", True, COLOR_TEXT)
                screen.blit(instruction, instruction.get_rect(center=(WIDTH // 2, 258)))

            draw_scoreboards(screen, (panel_font, row_font), scores, 300)
            pygame.display.flip()

if __name__ == "__main__":
    main()
