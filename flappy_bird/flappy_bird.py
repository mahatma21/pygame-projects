import pygame
from pygame.locals import *

import os
import random
import pyautogui
import json

import game_engine as ge

pygame.mixer.pre_init(48000, -16, 2, 512)
pygame.init()


def load_image(name):
    return pygame.transform.rotozoom(ge.load_image(IMAGE_PATH, name), 0, image_scale)


def load_sound(name):
    snd = pygame.mixer.Sound(ge.get_path(SOUND_PATH, name))
    snd.set_volume(0.3)
    return snd


def create_pipe():
    x = SCREEN_SIZE[0]
    bottomy = random.randint(300, ground.rect.top - 70)
    topy = bottomy - random.randint(*GAP_RANGE)
    return [
        pipe_images[0].get_rect(topleft=(x, bottomy)),
        pipe_images[1].get_rect(bottomleft=(x, topy)),
        True,
    ]


def get_font(size):
    try:
        font = fonts[size]
    except KeyError:
        font = fonts[size] = pygame.font.Font(FONT_PATH, size)
    return font


def draw_text(text, size, color, **kwargs):
    text_surf = get_font(size).render(str(text), False, color)
    text_rect = text_surf.get_rect(**kwargs)
    screen.blit(text_surf, text_rect)


def hit():
    hit_snd.play()
    return False


class Bird(pygame.sprite.Sprite):
    def __init__(self, frames, *groups, **kwargs):
        super().__init__(*groups)
        self.frames = frames
        self.rect = self.frames[0].get_rect(**kwargs)
        self.momentum = 0
        self.rotation = 0
        self.frame_count = 0

    def update(self):
        self.rect.y += self.momentum
        self.momentum = min(MAX_GRAV, self.momentum + GRAVITY)

        if self.momentum >= 3:
            self.rotation = max(-80, self.rotation - 2)

        if self.rotation >= -45:
            self.frame_count = (self.frame_count + 1) % (
                len(self.frames) * FPS_PER_FRAME
            )
        else:
            self.frame_count = 1 * FPS_PER_FRAME

    def draw(self, screen):
        image = self.rotated_image
        screen.blit(image, image.get_rect(center=self.rect.center))

    def flap(self):
        flap_snd.play()
        self.momentum = FLAP_VEL
        self.rotation = 30

    def reset(self):
        self.rect.center = BIRD_START_POS
        self.momentum = 0
        self.frame_count = 0

    @property
    def rotated_image(self):
        return pygame.transform.rotozoom(
            self.frames[self.frame_count // FPS_PER_FRAME], self.rotation, 1
        )


class Background(pygame.sprite.Sprite):
    def __init__(self, image, depth, *groups, **kwargs):
        super().__init__(*groups)
        self.image = image
        self.rect = self.image.get_rect(**kwargs)
        self.depth = depth

    def update(self):
        self.x = (self.x - VEL * self.depth) % self.rect.width

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        screen.blit(self.image, (self.rect.x - self.rect.width, self.rect.y))

    @property
    def rect(self):
        return self.__rect

    @rect.setter
    def rect(self, value):
        self.__rect = value
        self.__x = self.__rect.x

    @property
    def x(self):
        return self.__x

    @x.setter
    def x(self, value):
        self.__x = value
        self.__rect.x = self.__x


pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()

SCREEN_SIZE = 422, 750
SCREEN_MID = tuple(n / 2 for n in SCREEN_SIZE)
h = pyautogui.size()[1] - 150
DISPLAY_SIZE = int(9 * h / 16), h

IMAGE_PATH = os.path.join("assets", "images")
FONT_PATH = os.path.join("assets", "04B_19.TTF")
SOUND_PATH = os.path.join("assets", "audio")
HIGH_SCORE_PATH = ge.get_path("high_score.json")

VEL = 2
GRAVITY = 0.2
MAX_GRAV = 5
FLAP_VEL = -7
BIRD_START_POS = 70, SCREEN_MID[1]
FPS_PER_FRAME = 10
GAP_RANGE = 190, 200

# Custom event
SPAWN_PIPE = pygame.USEREVENT + 1
pygame.time.set_timer(SPAWN_PIPE, 1300)

# Game Variables
entities = pygame.sprite.Group()
pipes = []  # [[bottom_pipe_rect, top_pipe_rect, not_passed], ...]
game_active = False
fonts = {}
score = 0
# Load high score from json file
with open(HIGH_SCORE_PATH) as f:
    data = json.load(f)

if (curr_dir := os.getcwd()) != data['path']:
    data['high_score'] = 0
    data['path'] = curr_dir

# Load sounds
flap_snd = load_sound("sfx_wing.wav")
hit_snd = load_sound("sfx_hit.wav")
score_snd = load_sound("sfx_point.wav")

# Create game window
display = pygame.display.set_mode(DISPLAY_SIZE)
screen = pygame.Surface(SCREEN_SIZE).convert()

bg_image = ge.load_image(IMAGE_PATH, "background-day.png").convert()
image_scale = SCREEN_SIZE[0] / bg_image.get_width()
bg_image = pygame.transform.rotozoom(bg_image, 0, image_scale)
ground_image = load_image("base.png").convert()
bird_frames = tuple(
    load_image(f"yellowbird-{tag}.png").convert_alpha()
    for tag in ("upflap", "midflap", "downflap")
)
pipe_images = (
    (bottom_pipe_image := load_image("pipe-green.png").convert_alpha()),
    pygame.transform.flip(bottom_pipe_image, False, True),
)
message_image = load_image("message.png")

# Create rects
bg = Background(bg_image, 0.2, entities)
ground = Background(ground_image, 1, entities, top=SCREEN_SIZE[1] - 50)
bird = Bird(bird_frames, entities, center=(BIRD_START_POS))
message_rect = message_image.get_rect(center=SCREEN_MID)


while True:
    screen.fill(Color("black"))

    bg.draw(screen)
    # Update pipes
    if game_active:
        for pipe in pipes[:]:
            screen.blit(pipe_images[0], pipe[0])
            screen.blit(pipe_images[1], pipe[1])

            pipe[0].x -= VEL
            pipe[1].x -= VEL

            # Check bird collisions
            if bird.rect.collidelist(pipe[:2]) != -1 or (
                bird.rect.right >= pipe[0].left and bird.rect.bottom <= 0
            ):
                game_active = hit()

            # Check score increment
            if pipe[2] and bird.rect.left > pipe[0].right:
                score_snd.play()
                score += 1
                pipe[2] = False

            if pipe[0].right < 0:
                pipes.remove(pipe)

        bird.draw(screen)

    ground.draw(screen)

    if game_active:
        draw_text(score, 48, "white", center=(SCREEN_MID[0], 100))
    else:
        draw_text(score, 64, "white", center=(SCREEN_MID[0], 100))
        draw_text(
            f"High score: {data['high_score']}",
            40,
            "white",
            center=(SCREEN_MID[0], SCREEN_SIZE[1] - 100),
        )
        screen.blit(message_image, message_rect)

    scaled_screen = pygame.transform.scale(screen, DISPLAY_SIZE)
    display.blit(scaled_screen, (0, 0))
    pygame.display.update()

    flap = False
    for event in pygame.event.get():
        if ge.game_quit_check(event):
            # Write high score to json file
            with open(HIGH_SCORE_PATH, "w") as f:
                json.dump(data, f, indent=4)
            raise SystemExit

        if event.type == KEYDOWN:
            if event.key == K_SPACE:
                flap = True
        if event.type == MOUSEBUTTONDOWN:
            if pygame.mouse.get_pressed(3)[0]:
                flap = True
        if event.type == SPAWN_PIPE:
            pipes.append(create_pipe())
    if flap:
        if not game_active:
            bird.reset()
            pipes.clear()
            score = 0
            game_active = True
        bird.flap()

    # ------------------------------------------------ Game Update
    if game_active:
        entities.update()

        if bird.rect.bottom >= ground.rect.top:
            game_active = hit()

        # Update high score
        data['high_score'] = max(data['high_score'], score)

    clock.tick(120)
