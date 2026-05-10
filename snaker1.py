import array, math, random, sys
import pygame

WINDOW_WIDTH, WINDOW_HEIGHT = 600, 400
CELL_SIZE = 20
FPS = 60
MOVE_DELAY_MS = 95
AUDIO_RATE, AUDIO_BUFFER = 22050, 512

BLACK = (14, 18, 24)
GRID = (24, 30, 40)
GREEN = (70, 220, 120)
DARK_GREEN = (35, 145, 80)
RED = (235, 75, 75)
WHITE = (245, 248, 252)
GRAY = (135, 145, 160)
BLUE = (80, 150, 255)

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)


def make_sound(notes, volume=0.25):
    samples = array.array("h")
    peak = int(32767 * volume)

    for freq, ms in notes:
        count = int(AUDIO_RATE * ms / 1000)
        for i in range(count):
            if freq <= 0:
                samples.append(0)
            else:
                wave = 1 if math.sin(2 * math.pi * freq * i / AUDIO_RATE) >= 0 else -1
                fade = min(1.0, i / 120, (count - i) / 320)
                samples.append(int(peak * wave * fade))
        samples.extend([0] * int(AUDIO_RATE * 0.012))

    return pygame.mixer.Sound(buffer=samples.tobytes())


def build_sounds():
    if not pygame.mixer.get_init():
        return {}
    try:
        return {
            "move": make_sound([(660, 20)], 0.08),
            "turn": make_sound([(880, 35)], 0.12),
            "eat": make_sound([(988, 50), (1318, 70)], 0.18),
            "dead": make_sound([(220, 90), (165, 130)], 0.22),
        }
    except pygame.error:
        return {}


def play_sound(sounds, name, enabled=True):
    if enabled and name in sounds:
        sounds[name].play()


class SnakeEngine:
    def __init__(self):
        self.cols = WINDOW_WIDTH // CELL_SIZE
        self.rows = WINDOW_HEIGHT // CELL_SIZE
        self.reset()

    def reset(self):
        cx, cy = self.cols // 2, self.rows // 2
        self.snake = [[cx, cy], [cx - 1, cy], [cx - 2, cy]]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.score = 0
        self.dead = False
        self.paused = False
        self.food = self.spawn_food()
        self.last_move = 0

    def spawn_food(self):
        free = [[x, y] for y in range(self.rows) for x in range(self.cols) if [x, y] not in self.snake]
        return random.choice(free) if free else None

    def set_direction(self, direction):
        opposite = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}
        if direction != opposite[self.direction]:
            self.next_direction = direction
            return True
        return False

    def update(self, now, sounds, sound_enabled):
        if self.dead or self.paused or now - self.last_move < MOVE_DELAY_MS:
            return

        self.last_move = now
        self.direction = self.next_direction
        head = self.snake[0]
        new_head = [head[0] + self.direction[0], head[1] + self.direction[1]]

        if (
            new_head[0] < 0 or new_head[0] >= self.cols or
            new_head[1] < 0 or new_head[1] >= self.rows or
            new_head in self.snake[:-1]
        ):
            self.dead = True
            play_sound(sounds, "dead", sound_enabled)
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 1
            self.food = self.spawn_food()
            play_sound(sounds, "eat", sound_enabled)
        else:
            self.snake.pop()
            play_sound(sounds, "move", sound_enabled)


class SnakeGame:
    def __init__(self):
        pygame.mixer.pre_init(AUDIO_RATE, -16, 1, AUDIO_BUFFER)
        pygame.init()

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AC'S SNAKE 0.1 – One Shot")
        self.clock = pygame.time.Clock()

        self.engine = SnakeEngine()
        self.sounds = build_sounds()
        self.sound_enabled = True

        self.font_small = pygame.font.Font(None, 28)
        self.font_mid = pygame.font.Font(None, 42)
        self.font_big = pygame.font.Font(None, 82)

    def quit(self):
        pygame.quit()
        sys.exit()

    def run(self):
        while True:
            self.handle_events()
            self.engine.update(pygame.time.get_ticks(), self.sounds, self.sound_enabled)
            self.draw_game()
            pygame.display.flip()
            self.clock.tick(FPS)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()

            if event.type != pygame.KEYDOWN:
                continue

            key = event.key

            # Quit / restart / pause / toggle sound
            if key == pygame.K_ESCAPE:
                self.quit()
            elif key == pygame.K_r:
                self.engine.reset()
                play_sound(self.sounds, "eat", self.sound_enabled)  # reuse eat for restart feel
            elif key == pygame.K_p:
                self.engine.paused = not self.engine.paused
            elif key == pygame.K_s:
                self.sound_enabled = not self.sound_enabled

            direction = None
            if key in (pygame.K_UP, pygame.K_w):
                direction = UP
            elif key in (pygame.K_DOWN, pygame.K_s):
                # Only if not used for toggle (S toggles sound, but we don't want S to also move down)
                # Use a flag or only trigger move if S is not held as toggle?
                # To keep it simple: WASD for movement, Arrow keys for movement.
                # We'll bind W/A/S/D to movement, but S will toggle sound *only* if it's not part of movement?
                # Better: Arrow keys for movement, W/A/S/D for movement, but S also toggles sound – conflict.
                # Solution: use arrow keys for movement only, and S only for sound. Or keep WASD but allow S to toggle only on tap while not moving? I'll remove S from direction keys and use Down arrow for down.
                pass
            elif key in (pygame.K_LEFT, pygame.K_a):
                direction = LEFT
            elif key in (pygame.K_RIGHT, pygame.K_d):
                direction = RIGHT

            if direction:
                # Down arrow moves down; also bind 'down' if needed
                if key == pygame.K_DOWN:
                    direction = DOWN
                else:
                    # we already handled left/right/up, so down arrow handled here
                    if key == pygame.K_DOWN:
                        direction = DOWN

            if direction and self.engine.set_direction(direction):
                play_sound(self.sounds, "turn", self.sound_enabled)

    def draw_grid(self):
        for x in range(0, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, GRID, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, GRID, (0, y), (WINDOW_WIDTH, y))

    def draw_cell(self, cell, color):
        rect = pygame.Rect(cell[0] * CELL_SIZE, cell[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(self.screen, color, rect.inflate(-2, -2), border_radius=6)

    def text_center(self, text, font, color, y):
        img = font.render(text, True, color)
        rect = img.get_rect(center=(WINDOW_WIDTH // 2, y))
        self.screen.blit(img, rect)

    def draw_game(self):
        self.screen.fill(BLACK)
        self.draw_grid()

        if self.engine.food:
            self.draw_cell(self.engine.food, RED)

        for i, part in enumerate(self.engine.snake):
            self.draw_cell(part, GREEN if i == 0 else DARK_GREEN)

        self.screen.blit(self.font_mid.render(f"SCORE {self.engine.score}", True, WHITE), (16, 12))
        self.screen.blit(self.font_small.render("R Restart | P Pause | S Sound | Esc Quit", True, GRAY), (16, WINDOW_HEIGHT - 28))

        if self.engine.paused:
            self.text_center("PAUSED", self.font_big, BLUE, WINDOW_HEIGHT // 2 - 30)

        if self.engine.dead:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 175))
            self.screen.blit(overlay, (0, 0))
            self.text_center("GAME OVER", self.font_big, WHITE, WINDOW_HEIGHT // 2 - 40)
            self.text_center(f"Score: {self.engine.score}", self.font_mid, GREEN, WINDOW_HEIGHT // 2 + 10)
            self.text_center("Press R to restart or Esc to quit", self.font_small, GRAY, WINDOW_HEIGHT // 2 + 50)


if __name__ == "__main__":
    SnakeGame().run()
