import pygame
import math
import sys

pygame.init()

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

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Cat Zone Simulator")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)

beacons = []
cat_pos = None
signal_range = 5.0
last_beacon = None
placing_beacons = True
heatmap_surface = None
estimated_pos = None
max_confidence = 0.0

def dist(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def signal_strength(beacon_pos, point_pos, max_range):
    d_pixels = dist(beacon_pos, point_pos)
    d_meters = d_pixels / YARD_SCALE
    if d_meters == 0:
        return 1.0
    falloff = (max_range / d_meters) ** 2
    return max(0.0, falloff / (1 + falloff))

def strengths_at_point(beacon_positions, point_pos, max_range):
    return [signal_strength(b, point_pos, max_range) for b in beacon_positions]

def compute_heatmap(beacon_positions, max_range):
    grid_width = 40
    grid_height = 30
    cell_w = SCREEN_WIDTH / grid_width
    cell_h = SCREEN_HEIGHT / grid_height
    heatmap = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    max_total_strength = 0.0
    grid_strengths = []
    for gy in range(grid_height):
        row = []
        for gx in range(grid_width):
            x = (gx + 0.5) * cell_w
            y = (gy + 0.5) * cell_h
            cell_pos = (x, y)
            total_strength = sum(strengths_at_point(beacon_positions, cell_pos, max_range))
            row.append(total_strength)
            if total_strength > max_total_strength:
                max_total_strength = total_strength
        grid_strengths.append(row)
    for gy in range(grid_height):
        for gx in range(grid_width):
            total_strength = grid_strengths[gy][gx]
            intensity = total_strength / max_total_strength if max_total_strength > 0 else 0.0
            r = int(255 * (1 - intensity))
            g = int(255 * intensity)
            b = int(128 * (1 - intensity))
            a = int(100 * intensity)
            rect = pygame.Rect(gx * cell_w, gy * cell_h, cell_w, cell_h)
            pygame.draw.rect(heatmap, (r, g, b, a), rect)
    return heatmap, max_total_strength

def estimate_position(beacon_positions, strengths, max_range):
    if not strengths or sum(strengths) == 0:
        return None
    total_strength = sum(strengths)
    weighted_x = sum(s * b[0] for s, b in zip(strengths, beacon_positions)) / total_strength
    weighted_y = sum(s * b[1] for s, b in zip(strengths, beacon_positions)) / total_strength
    return (weighted_x, weighted_y)

def draw_beacon(pos):
    pygame.draw.circle(screen, BLUE, pos, 5)

def draw_cat(pos):
    pygame.draw.circle(screen, RED, pos, 8)

def draw_estimated(pos):
    if pos:
        pygame.draw.circle(screen, GREEN, pos, 6)

def draw_ui(cat_pos_local):
    if placing_beacons:
        prompt = f"Click to place beacons (max 6, have {len(beacons)}). After a beacon, right-click to set range from it. SPACE to start cat mode, ESC quit."
    else:
        prompt = "Left-click for cat position (redraws heatmap). SPACE to reset, ESC quit."
    text = font.render(prompt, True, BLACK)
    screen.blit(text, (10, 10))
    if cat_pos_local and estimated_pos:
        est_mx = estimated_pos[0] / YARD_SCALE
        est_my = estimated_pos[1] / YARD_SCALE
        act_mx = cat_pos_local[0] / YARD_SCALE
        act_my = cat_pos_local[1] / YARD_SCALE
        info = font.render(f"Actual: ({act_mx:.1f},{act_my:.1f})m | Est: ({est_mx:.1f},{est_my:.1f})m | Conf: {max_confidence:.2f}", True, BLACK)
        screen.blit(info, (10, SCREEN_HEIGHT - 30))

def detect_and_update(cat_pos_local):
    global heatmap_surface, estimated_pos, max_confidence
    if not cat_pos_local or not beacons:
        return
    strengths = strengths_at_point(beacons, cat_pos_local, signal_range)
    estimated_pos = estimate_position(beacons, strengths, signal_range)
    heatmap_surface, max_confidence = compute_heatmap(beacons, signal_range)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                if placing_beacons and len(beacons) > 0 and signal_range > 0:
                    placing_beacons = False
                    cat_pos = None
                else:
                    placing_beacons = True
                    cat_pos = None
                    last_beacon = None
                    signal_range = 5.0
                    heatmap_surface = None
                    estimated_pos = None
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            if event.button == 1:
                if placing_beacons:
                    if len(beacons) < 6:
                        beacons.append((mx, my))
                        last_beacon = (mx, my)
                    else:
                        print("Max beacons reached; use SPACE to enter cat mode.")
                else:
                    cat_pos = (mx, my)
                    detect_and_update(cat_pos)
                    strengths = strengths_at_point(beacons, cat_pos, signal_range)
                    print(f"Strengths from beacons: {[f'{s:.2f}' for s in strengths]}")
            elif event.button == 3 and placing_beacons and last_beacon:
                new_range = dist(last_beacon, (mx, my)) / YARD_SCALE
                signal_range = max(1.0, new_range)
                print(f"Range set to {signal_range:.1f}m from last beacon")

    screen.fill(WHITE)
    for b in beacons:
        draw_beacon(b)

    if cat_pos:
        draw_cat(cat_pos)
        draw_estimated(estimated_pos)
        if heatmap_surface:
            screen.blit(heatmap_surface, (0, 0))

    draw_ui(cat_pos)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
