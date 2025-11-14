import sys
import math
from ui import *

beacons = []
cat_pos = None
signal_range = 5.0
last_beacon = None
placing_beacons = True
house_placement = False
house_corners = []
houses = []
heatmap_surface = None
estimated_pos = None
max_confidence = 0.0
building_attenuation_coeff = 0.5

def compute_intersection(a_x, a_y, b_x, b_y, c_x, c_y, d_x, d_y):
    denom = (b_x - a_x)*(d_y - c_y) - (b_y - a_y)*(d_x - c_x)
    if abs(denom) < 1e-9:
        return None
    t = ((c_x - a_x)*(d_y - c_y) - (c_y - a_y)*(d_x - c_x)) / denom
    u = ((c_x - a_x)*(b_y - a_y) - (c_y - a_y)*(b_x - a_x)) / denom
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (a_x + t*(b_x - a_x), a_y + t*(b_y - a_y))
    return None

def point_in_convex_poly(point, poly):
    n = len(poly)
    if n < 3:
        return False
    eps = 1e-9
    sign = 0
    for i in range(n):
        p1 = poly[i]
        p2 = poly[(i + 1) % n]
        cx = (p2[0] - p1[0]) * (point[1] - p1[1]) - (p2[1] - p1[1]) * (point[0] - p1[0])
        if cx > eps:
            if sign < 0:
                return False
            sign = 1
        elif cx < -eps:
            if sign > 0:
                return False
            sign = -1
    return True

def line_intersects_poly(p1, p2, poly):
    if point_in_convex_poly(p1, poly) or point_in_convex_poly(p2, poly):
        return True
    n = len(poly)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        if compute_intersection(p1[0], p1[1], p2[0], p2[1], a[0], a[1], b[0], b[1]) is not None:
            return True
    return False

def signal_strength(beacon_pos, point_pos, max_range):
    d_pixels = dist(beacon_pos, point_pos)
    d_meters = d_pixels / YARD_SCALE
    if d_meters == 0:
        base = 1.0
    else:
        falloff = (max_range / d_meters) ** 2
        base = max(0.0, falloff / (1.0 + falloff))
    total_inside = 0.0
    for house in houses:
        L = segment_length_inside_poly(beacon_pos, point_pos, house)
        total_inside += L
    if total_inside > 0:
        base *= math.exp(-building_attenuation_coeff * total_inside)
    if d_meters <= max_range:
        return base
    over = d_meters - max_range
    roll_k = 0.8
    roll = math.exp(-roll_k * over)
    noise_floor = 1e-5
    return max(base * roll, noise_floor)

def segment_length_inside_poly(p1, p2, poly):
    px, py = p1
    qx, qy = p2
    dx = qx - px
    dy = qy - py
    total_pixel_length = math.hypot(dx, dy)
    if total_pixel_length < 1e-9:
        return 0.0
    step_px = 5.0
    n_steps = max(20, int(math.ceil(total_pixel_length / step_px)))
    inside_pixels = 0.0
    prev_inside = point_in_convex_poly((px, py), poly)
    prev_x, prev_y = px, py
    for i in range(1, n_steps + 1):
        t = i / n_steps
        cx = px + t * dx
        cy = py + t * dy
        curr_inside = point_in_convex_poly((cx, cy), poly)
        if prev_inside and curr_inside:
            seg_len = math.hypot(cx - prev_x, cy - prev_y)
            inside_pixels += seg_len
        elif prev_inside and not curr_inside:
            seg_len = math.hypot(cx - prev_x, cy - prev_y)
            inside_pixels += seg_len * 0.5
        elif not prev_inside and curr_inside:
            seg_len = math.hypot(cx - prev_x, cy - prev_y)
            inside_pixels += seg_len * 0.5
        prev_inside = curr_inside
        prev_x, prev_y = cx, cy
    total_meters = inside_pixels / YARD_SCALE
    return total_meters

def strengths_at_point(beacon_positions, point_pos, max_range):
    return [signal_strength(b, point_pos, max_range) for b in beacon_positions]

def compute_likelihood_heatmap(beacon_positions, measured_strengths, max_range):
    if not measured_strengths or sum(measured_strengths) == 0:
        return None, 0.0, None
    N = len(measured_strengths)
    sigma = 0.25
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
            sse = sum((m - e) ** 2 for m, e in zip(measured_strengths, expected))
            likelihood = math.exp(-sse / (2.0 * sigma * sigma))
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
                if placing_beacons:
                    if len(beacons) > 0 and signal_range > 0:
                        placing_beacons = False
                        house_placement = True
                        house_corners = []
                elif house_placement:
                    house_placement = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            if event.button == 1:
                if placing_beacons:
                    if len(beacons) < 6:
                        beacons.append((mx, my))
                        last_beacon = (mx, my)
                    else:
                        print("Max beacons reached; use SPACE to enter house mode.")
                elif house_placement:
                    house_corners.append((mx, my))
                    if len(house_corners) == 4:
                        houses.append(house_corners[:])
                        house_corners = []
                        print("House added.")
                else:
                    cat_pos = (mx, my)
                    detect_and_update(cat_pos)
                    strengths = strengths_at_point(beacons, cat_pos, signal_range)
                    print(f"Strengths from beacons: {[f'{s:.2f}' for s in strengths]}")
            elif event.button == 3 and placing_beacons and last_beacon:
                new_range = dist(last_beacon, (mx, my)) / YARD_SCALE
                signal_range = max(1.0, new_range)
                print(f"Range set to {signal_range:.1f} from last beacon")
    draw_background(screen)
    for house in houses:
        pygame.draw.polygon(screen, DARK_GRAY, house, 2)
    for b in beacons:
        draw_beacon(screen, b)
    if cat_pos and beacons:
        strengths = strengths_at_point(beacons, cat_pos, signal_range)
        for b, s in zip(beacons, strengths):
            intensity = max(0.0, min(1.0, s))
            color = (int(255 * (1.0 - intensity)), int(255 * intensity), 0)
            width = max(1, int(1 + intensity * 12))
            pygame.draw.line(screen, color, b, cat_pos, width)
    if cat_pos:
        draw_cat(screen, cat_pos)
        if heatmap_surface:
            screen.blit(heatmap_surface, (0, 0))
    draw_ui(screen, font, placing_beacons, house_placement, house_corners, beacons, cat_pos, estimated_pos, max_confidence)
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
sys.exit()

