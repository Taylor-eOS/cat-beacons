import sys
import math
from ui import *

beacons = []
cat_pos = None
signal_range = 5.0
last_beacon = None
placing_beacons = True
heatmap_surface = None
estimated_pos = None
max_confidence = 0.0

def signal_strength(beacon_pos, point_pos, max_range):
    d_pixels = dist(beacon_pos, point_pos)
    d_meters = d_pixels / YARD_SCALE
    if d_meters == 0:
        return 1.0
    falloff = (max_range / d_meters) ** 2
    return max(0.0, falloff / (1 + falloff))

def strengths_at_point(beacon_positions, point_pos, max_range):
    return [signal_strength(b, point_pos, max_range) for b in beacon_positions]

def compute_likelihood_heatmap(beacon_positions, measured_strengths, max_range):
    if not measured_strengths or sum(measured_strengths) == 0:
        return None, 0.0, None
    N = len(measured_strengths)
    sigma = 0.1
    grid_width = 40
    grid_height = 30
    cell_w = SCREEN_WIDTH / grid_width
    cell_h = SCREEN_HEIGHT / grid_height
    max_likelihood = 0.0
    best_pos = None
    grid_likelihoods = []
    for gy in range(grid_height):
        row = []
        for gx in range(grid_width):
            x = (gx + 0.5) * cell_w
            y = (gy + 0.5) * cell_h
            cell_pos = (x, y)
            expected = strengths_at_point(beacon_positions, cell_pos, max_range)
            sse = sum((m - e)**2 for m, e in zip(measured_strengths, expected))
            likelihood = math.exp(-sse / (2 * sigma**2))
            row.append(likelihood)
            if likelihood > max_likelihood:
                max_likelihood = likelihood
                best_pos = cell_pos
        grid_likelihoods.append(row)
    return grid_likelihoods, max_likelihood, best_pos

def detect_and_update(cat_pos_local):
    global heatmap_surface, estimated_pos, max_confidence
    if not cat_pos_local or not beacons:
        return
    strengths = strengths_at_point(beacons, cat_pos_local, signal_range)
    grid_likelihoods, max_conf, est_pos = compute_likelihood_heatmap(beacons, strengths, signal_range)
    if grid_likelihoods is not None:
        heatmap_surface = create_heatmap_surface(grid_likelihoods, max_conf)
    estimated_pos = est_pos
    max_confidence = max_conf

screen, clock, font = init_display()
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
        draw_beacon(screen, b)
    if cat_pos:
        draw_cat(screen, cat_pos)
        if heatmap_surface:
            screen.blit(heatmap_surface, (0, 0))
    draw_ui(screen, font, placing_beacons, beacons, cat_pos, estimated_pos, max_confidence)
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
sys.exit()
