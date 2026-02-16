import pygame
import sys
import os
import random


class Config:
    width = 576
    height = 555
    gravity = 0.4
    jump_strength = -6.5
    pipe_speed = 3.5
    pipe_spawn_rate = 1800
    pipe_gap = 160
    base_height = 112
    base_y = height - base_height
    pipe_min_height = 100
    pipe_max_height = height - base_height - pipe_gap - 50

    white = (0, 0, 0)
    black = (255, 255, 255)


class Bird:
    def __init__(self, game):
        self.game = game
        self.frames = []
        for i in range(1, 4):
            img = self.game.load_image(f'bird{i}.png', scale=2)
            self.frames.append(img)

        self.x = Config.width // 3
        self.y = Config.height // 2
        self.velocity = 0
        self.gravity = Config.gravity
        self.jump_strength = Config.jump_strength

        self.current_frame = 0
        self.animation_speed = 0.15
        self.frame_counter = 0

        self.alive = True
        self.rect = pygame.Rect(self.x, self.y,
                                self.frames[0].get_width(),
                                self.frames[0].get_height())

        self.angle = 0

    def jump(self):
        if self.alive:
            self.velocity = self.jump_strength

    def update(self):
        if not self.alive:
            return

        self.velocity += self.gravity
        self.y += self.velocity

        if self.y < 0:
            self.y = 0
            self.velocity = 0

        self.frame_counter += self.animation_speed
        if self.frame_counter >= 1:
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.frame_counter = 0

        self.rect.x = self.x
        self.rect.y = self.y

        if self.velocity < 0:
            self.angle = 15
        elif self.velocity > 8:
            self.angle = -45
        else:
            self.angle = -self.velocity * 3

    def draw(self, screen):
        current_image = self.frames[self.current_frame]
        rotated_image = pygame.transform.rotate(current_image, self.angle)
        new_rect = rotated_image.get_rect(center=current_image.get_rect(
            topleft=(self.x, self.y)).center)
        screen.blit(rotated_image, new_rect.topleft)

    def reset(self):
        self.__init__(self.game)

class Pipe:
    def __init__(self, game, x):
        self.game = game
        self.image = game.load_image('pipe_green.png', scale=2)

        self.x = x
        self.passed = False

        min_height = Config.pipe_min_height
        max_height = Config.pipe_max_height

        if min_height >= max_height:
            max_height = min_height + 100

        self.height = random.randint(min_height, max_height)

        self.top_pipe = pygame.transform.flip(self.image, False, True)
        self.top_rect = self.top_pipe.get_rect()
        self.top_rect.bottomleft = (self.x, self.height)

        self.bottom_pipe = self.image
        self.bottom_rect = self.bottom_pipe.get_rect()
        self.bottom_rect.topleft = (self.x, self.height + Config.pipe_gap)

        self.speed = Config.pipe_speed

    def update(self):
        self.x -= self.speed
        self.top_rect.x = self.x
        self.bottom_rect.x = self.x

    def draw(self, screen):
        screen.blit(self.top_pipe, self.top_rect)
        screen.blit(self.bottom_pipe, self.bottom_rect)

    def is_off_screen(self):
        return self.x + self.image.get_width() < 0

    def collide(self, bird_rect):
        return (self.top_rect.colliderect(bird_rect) or
                self.bottom_rect.colliderect(bird_rect))

    def get_center_x(self):
        return self.x + self.image.get_width() / 2


class PipeManager:
    def __init__(self, game):
        self.game = game
        self.pipes = []
        self.spawn_timer = 0
        self.last_time = pygame.time.get_ticks()

    def update(self, bird_rect, score_manager):
        current_time = pygame.time.get_ticks()
        delta_time = current_time - self.last_time
        self.last_time = current_time

        self.spawn_timer += delta_time
        if self.spawn_timer >= Config.pipe_spawn_rate:
            self.spawn_pipe()
            self.spawn_timer = 0

        pipes_to_remove = []
        for pipe in self.pipes:
            pipe.update()

            if not pipe.passed and pipe.get_center_x() < bird_rect.centerx:
                pipe.passed = True
                score_manager.add_score()

            if pipe.is_off_screen():
                pipes_to_remove.append(pipe)

        for pipe in pipes_to_remove:
            self.pipes.remove(pipe)

    def spawn_pipe(self):
        self.pipes.append(Pipe(self.game, Config.width))

    def draw(self, screen):
        for pipe in self.pipes:
            pipe.draw(screen)

    def check_collisions(self, bird_rect):
        for pipe in self.pipes:
            if pipe.collide(bird_rect):
                return True
        return False

    def reset(self):
        self.pipes.clear()
        self.spawn_timer = 0


class ScoreManager:
    def __init__(self, game):
        self.game = game
        self.digits = []

        for i in range(10):
            digit = game.load_image(f'{i}.png', scale=2)
            self.digits.append(digit)

        self.score = 0
        self.high_score = 0

    def add_score(self, points=1):
        self.score += points
        if self.score > self.high_score:
            self.high_score = self.score

    def reset_score(self):
        self.score = 0

    def draw(self, screen, x, y, score=None):
        if score is None:
            score = self.score

        score_str = str(score)
        if not score_str:
            return

        total_width = len(score_str) * self.digits[0].get_width()

        for i, digit_char in enumerate(score_str):
            digit_index = int(digit_char)
            digit_image = self.digits[digit_index]
            digit_x = x - total_width // 2 + i * self.digits[0].get_width()
            screen.blit(digit_image, (digit_x, y))

    def draw_high_score(self, screen, x, y):
        font = pygame.font.Font(None, 24)
        text = font.render(f"High Score: {self.high_score}", True, Config.white)
        screen.blit(text, (x, y))


class FlappyBird:
    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((Config.width, Config.height))
        pygame.display.set_caption("Flappy Bird")
        self.clock = pygame.time.Clock()
        self.fps = 60

        self.assets = {}
        self.load_all_assets()

        self.bird = Bird(self)
        self.pipe_manager = PipeManager(self)
        self.score_manager = ScoreManager(self)

        self.base_x1 = 0
        self.base_x2 = self.assets['base'].get_width()

        self.game_state = "START"

        self.start_bird_y = Config.height // 3
        self.start_bird_float = 0
        self.float_speed = 0.05

    def load_image(self, filename, scale=1):
        try:
            paths = [
                os.path.join('assets', filename),
                os.path.join('..', 'assets', filename),
                filename,
                os.path.join(os.path.dirname(__file__), 'assets', filename)
            ]

            for path in paths:
                if os.path.exists(path):
                    image = pygame.image.load(path).convert_alpha()
                    if scale != 1:
                        size = image.get_size()
                        image = pygame.transform.scale(image,
                                                       (int(size[0] * scale), int(size[1] * scale)))
                    return image

            print(f"Warning: Could not load {filename}")
            surf = pygame.Surface((50, 50))
            surf.fill((255, 0, 255))
            return surf

        except Exception as e:
            print(f"Error loading {filename}: {e}")
            surf = pygame.Surface((50, 50))
            surf.fill((255, 0, 255))
            return surf

    def load_all_assets(self):
        self.assets['base'] = self.load_image('base.png', scale=2)
        if self.assets['base'].get_width() <= 50:
            self.assets['base'] = self.load_image('ground.png', scale=2)

        self.assets['message'] = self.load_image('message.png', scale=2)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.handle_click()
                elif event.key == pygame.K_ESCAPE:
                    return False

            if event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_click()

        return True

    def handle_click(self):
        if self.game_state == "START":
            self.game_state = "PLAYING"
        elif self.game_state == "PLAYING":
            self.bird.jump()
        elif self.game_state == "GAME_OVER":
            self.reset_game()

    def reset_game(self):
        self.bird.reset()
        self.pipe_manager.reset()
        self.score_manager.reset_score()
        self.game_state = "START"

    def update(self):
        if self.game_state == "PLAYING":
            self.bird.update()

            self.pipe_manager.update(self.bird.rect, self.score_manager)

            self.base_x1 -= Config.pipe_speed
            self.base_x2 -= Config.pipe_speed

            if self.base_x1 + self.assets['base'].get_width() < 0:
                self.base_x1 = self.base_x2 + self.assets['base'].get_width()

            if self.base_x2 + self.assets['base'].get_width() < 0:
                self.base_x2 = self.base_x1 + self.assets['base'].get_width()

            bird_fell = self.bird.y + self.bird.frames[0].get_height() > Config.base_y
            hit_pipe = self.pipe_manager.check_collisions(self.bird.rect)

            if bird_fell or hit_pipe:
                self.game_state = "GAME_OVER"
                self.bird.alive = False

        elif self.game_state == "START":
            self.start_bird_float += self.float_speed
            float_offset = (pygame.math.Vector2(0, self.start_bird_float).y % 40) - 20
            self.bird.y = self.start_bird_y + float_offset
            self.bird.frame_counter += self.bird.animation_speed / 3
            if self.bird.frame_counter >= 1:
                self.bird.current_frame = (self.bird.current_frame + 1) % len(self.bird.frames)
                self.bird.frame_counter = 0

    def draw(self):
        self.screen.fill((135, 206, 235))

        if self.game_state != "START":
            self.pipe_manager.draw(self.screen)

        self.bird.draw(self.screen)

        self.screen.blit(self.assets['base'], (self.base_x1, Config.base_y))
        self.screen.blit(self.assets['base'], (self.base_x2, Config.base_y))

        if self.game_state == "START":
            msg_rect = self.assets['message'].get_rect(
                center=(Config.width // 2, Config.height // 2 - 50))
            self.screen.blit(self.assets['message'], msg_rect)

            self.score_manager.draw_high_score(self.screen, 10, 10)

            font = pygame.font.Font(None, 20)
            text = font.render("Press SPACE or CLICK to start", True, Config.white)
            text_rect = text.get_rect(center=(Config.width // 2, Config.height - 30))
            self.screen.blit(text, text_rect)

        elif self.game_state == "PLAYING":
            if self.score_manager.digits:
                self.score_manager.draw(self.screen, Config.width // 2, 50)

        elif self.game_state == "GAME_OVER":
            if self.score_manager.digits:
                self.score_manager.draw(self.screen, Config.width // 2, Config.height // 2 - 100)

            font = pygame.font.Font(None, 36)
            text = font.render(f"High Score: {self.score_manager.high_score}",
                               True, Config.white)
            text_rect = text.get_rect(center=(Config.width // 2, Config.height // 2 - 50))
            self.screen.blit(text, text_rect)

            font = pygame.font.Font(None, 24)
            text = font.render("Press SPACE or CLICK to restart", True, Config.white)
            text_rect = text.get_rect(center=(Config.width // 2, Config.height // 2 + 50))
            self.screen.blit(text, text_rect)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.fps)

        pygame.quit()
        sys.exit()


def main():
    game = FlappyBird()
    game.run()


if __name__ == "__main__":
    main()