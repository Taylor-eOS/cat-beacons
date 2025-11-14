import pygame
import math

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
YARD_SCALE = 40
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
DARK_GRAY = (50, 50, 50)

background_surf = None

def dist(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def init_display():
    global background_surf
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Cat Zone Simulator")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    try:
        img = pygame.image.load('back.png')
        img = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        background_surf = img.convert_alpha()
        background_surf.set_alpha(128)
    except Exception:
        background_surf = None
    return screen, clock, font

def draw_background(screen):
    screen.fill(WHITE)
    if background_surf:
        screen.blit(background_surf, (0, 0))

def draw_beacon(screen, pos):
    pygame.draw.circle(screen, BLUE, pos, 5)

def draw_cat(screen, pos):
    pygame.draw.circle(screen, RED, pos, 8)

def create_heatmap_surface(grid_likelihoods, max_likelihood):
    if not grid_likelihoods or max_likelihood == 0:
        return pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    grid_width = len(grid_likelihoods[0])
    grid_height = len(grid_likelihoods)
    cell_w = SCREEN_WIDTH / grid_width
    cell_h = SCREEN_HEIGHT / grid_height
    heatmap = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for gy in range(grid_height):
        for gx in range(grid_width):
            likelihood = grid_likelihoods[gy][gx]
            intensity = likelihood / max_likelihood
            r = int(255 * (1 - intensity))
            g = int(255 * intensity)
            b = int(128 * (1 - intensity))
            a = int(150 * intensity)
            rect = pygame.Rect(gx * cell_w, gy * cell_h, cell_w, cell_h)
            pygame.draw.rect(heatmap, (r, g, b, a), rect)
    return heatmap

def draw_ui(screen, font, placing_beacons, beacons, cat_pos, estimated_pos, max_confidence):
    if placing_beacons:
        prompt = f"Click to place beacons (max 6, have {len(beacons)}). After a beacon, right-click to set range from it. SPACE to start, ESC quit."
    else:
        prompt = "Left-click for cat position (redraws heatmap). ESC quit."
    text = font.render(prompt, True, BLACK)
    screen.blit(text, (10, 10))
    if cat_pos and estimated_pos:
        est_mx = estimated_pos[0] / YARD_SCALE
        est_my = estimated_pos[1] / YARD_SCALE
        act_mx = cat_pos[0] / YARD_SCALE
        act_my = cat_pos[1] / YARD_SCALE
        info = font.render(f"Actual: ({act_mx:.1f},{act_my:.1f})m | Est: ({est_mx:.1f},{est_my:.1f})m | Conf: {max_confidence:.2f}", True, BLACK)
        screen.blit(info, (10, SCREEN_HEIGHT - 30))
