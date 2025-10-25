import cv2
import mediapipe as mp
mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles
import pygame
import sys
import os  # add os module for path checks
import time  # add time module for countdowns
import random  # add random module for random gesture selection
from collections import deque

# =======================
# Initialization
# =======================
# Open camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Unable to open camera")
    sys.exit()

# Initialize MediaPipe Hands module
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False,
                       max_num_hands=2,
                       min_detection_confidence=0.5,
                       min_tracking_confidence=0.5)

# Initialize pygame
pygame.init()

# Configuration: whether to draw MediaPipe landmark control points on the camera preview
SHOW_LANDMARKS = False

# Compute project path so the script uses relative paths; moving the folder won't break it
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
SOUNDS_DIR = os.path.join(PROJECT_ROOT, 'sounds')

# Initialize mixer and load cat meow sound (if present)
try:
    pygame.mixer.init()
except Exception:
    # In some environments the mixer may fail to initialize (no sound card, etc.), ignore error so program continues
    pass
# Use relative paths to find sound files (more robust)
cat_sound = None
cat_sound_path = os.path.join(SOUNDS_DIR, 'Cat_Meow.wav')
if os.path.exists(cat_sound_path):
    try:
        cat_sound = pygame.mixer.Sound(cat_sound_path)
        cat_sound.set_volume(0.9)
    except Exception:
        cat_sound = None
# Play the cat meow once at startup (play only once)
try:
    if cat_sound:
        cat_sound.play()
except Exception:
    pass

# Result sound effects (win/lose/draw)
win_sound = None
lose_sound = None
draw_sound = None
win_sound_path = os.path.join(SOUNDS_DIR, 'Win.wav')
lose_sound_path = os.path.join(SOUNDS_DIR, 'Lose.wav')
draw_sound_path = os.path.join(SOUNDS_DIR, 'Draw.wav')
if os.path.exists(win_sound_path):
    try:
        win_sound = pygame.mixer.Sound(win_sound_path)
        win_sound.set_volume(0.9)
    except Exception:
        win_sound = None
if os.path.exists(lose_sound_path):
    try:
        lose_sound = pygame.mixer.Sound(lose_sound_path)
        lose_sound.set_volume(0.9)
    except Exception:
        lose_sound = None
if os.path.exists(draw_sound_path):
    try:
        draw_sound = pygame.mixer.Sound(draw_sound_path)
        draw_sound.set_volume(0.9)
    except Exception:
        draw_sound = None

# Background music (BGM) - play looped at low volume if present
bgm_path = os.path.join(SOUNDS_DIR, 'Hopeful.mp3')
bgm_playing = False
if os.path.exists(bgm_path):
    try:
        # Use pygame's music module for streaming longer music files
        pygame.mixer.music.load(bgm_path)
        pygame.mixer.music.set_volume(0.12)  # low volume
        pygame.mixer.music.play(-1)  # loop indefinitely
        bgm_playing = True
    except Exception:
        bgm_playing = False

# Create pygame window
WINDOW_WIDTH, WINDOW_HEIGHT = 800, 480
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Paw-Punch")

# Define left and right panels
LEFT_PANEL_WIDTH = WINDOW_WIDTH // 2
RIGHT_PANEL_WIDTH = WINDOW_WIDTH - LEFT_PANEL_WIDTH

# Load cat hand assets
cat_hands_path = os.path.join(ASSETS_DIR, "Cat Hands.png")
if not os.path.exists(cat_hands_path):
    print(f"Cat hand image not found: {cat_hands_path}")
    sys.exit()

cat_hands_image = pygame.image.load(cat_hands_path)
cat_hands_width, cat_hands_height = cat_hands_image.get_size()

# Split the full image into three separate images and flip vertically
single_width = cat_hands_width // 3
cat_hands = {
    "paper": pygame.transform.flip(cat_hands_image.subsurface((0, 0, single_width, cat_hands_height)), False, True),
    "rock": pygame.transform.flip(cat_hands_image.subsurface((single_width, 0, single_width, cat_hands_height)), False, True),
    "scissors": pygame.transform.flip(cat_hands_image.subsurface((2 * single_width, 0, single_width, cat_hands_height)), False, True)
}

# Example: prepare left-side display
current_hand = "paper"  # currently displayed hand

# Scale down cat hand images
for gesture in cat_hands:
    cat_hands[gesture] = pygame.transform.scale(cat_hands[gesture], (cat_hands[gesture].get_width() // 2, cat_hands[gesture].get_height() // 2))

# Load background tile
background_path = os.path.join(ASSETS_DIR, 'Background.png')
if not os.path.exists(background_path):
    print(f"Background image not found: {background_path}")
    sys.exit()

background_image = pygame.image.load(background_path)
background_image = pygame.transform.scale(background_image, (100, 100))  # scale tile to 100x100

# Define left cat-hand area and right camera display area
cat_hand_area = (50, 50)  # top-left of left cat-hand area
cam_area = (WINDOW_WIDTH - cat_hand_area[0] - 50, 50)  # top-left of right camera area

# Nudge camera area to be closer to the window edge
cam_area = (cam_area[0] - 10, cam_area[1] - 10)

# Enlarge cat hand images
for gesture in cat_hands:
    cat_hands[gesture] = pygame.transform.scale(cat_hands[gesture], (cat_hands[gesture].get_width() * 2, cat_hands[gesture].get_height() * 2))

# Further enlarge by 1.5x to make the paw larger
for gesture in cat_hands:
    w, h = cat_hands[gesture].get_size()
    cat_hands[gesture] = pygame.transform.scale(cat_hands[gesture], (int(w * 1.5), int(h * 1.5)))

# Position camera preview smaller and in bottom-right
cam_width, cam_height = WINDOW_WIDTH // 4, WINDOW_HEIGHT // 4
cam_area = (WINDOW_WIDTH - cam_width - 10, WINDOW_HEIGHT - cam_height - 10)

# Center cat-hand display area
cat_hand_area = (WINDOW_WIDTH // 2 - cat_hands["rock"].get_width() // 2, WINDOW_HEIGHT // 2 - cat_hands["rock"].get_height() // 2)

# =======================
# Layout and positions
# =======================
cat_hand_x = WINDOW_WIDTH // 2 - cat_hands["rock"].get_width() // 2
cat_start_y = -50  # initial (idle) cat paw Y position; moved further up so the paw sits higher on the title/idle screen
cat_target_y = WINDOW_HEIGHT // 2 - cat_hands["rock"].get_height() // 2 - 140  # move up 140px (a bit more)
cat_hand_y = cat_start_y
# Movement speed of the cat paw
cat_speed = 5

cam_width, cam_height = WINDOW_WIDTH // 4, WINDOW_HEIGHT // 4
cam_area = (WINDOW_WIDTH - cam_width - 10, WINDOW_HEIGHT - cam_height - 10)

# =======================
# Game state
# =======================
current_hand = "paper"
player_gesture = None
cat_gesture = None

# Cat paw animation state
revealing = False  # cat paw is extending animation
# Whether the player has triggered the round (previously fist/rock, now paper allowed)
start_triggered = False

# Temporal smoothing: require N consecutive frames to trigger start
start_buffer = deque(maxlen=3)
# Final gesture buffer collected during revealing; majority vote used
final_gesture_buffer = deque(maxlen=5)

counting_down = False
countdown_start = 0
countdown = 3

show_result = False
result_text = ""
result_timer = 0

# Background scrolling parameters (scroll toward bottom-right)
bg_offset_x = 0.0
bg_offset_y = 0.0
bg_speed_x = 0.5  # pixels/frame to the right (tweakable)
bg_speed_y = 0.25  # pixels/frame downward (tweakable)

# Add pygame clock object
clock = pygame.time.Clock()

# Text outline drawing helper
def draw_text_with_outline(surface, text, font, pos, fg_color, outline_color, outline_width=2):
    # Draw a multi-layer outline (simple but effective)
    for ox in range(-outline_width, outline_width+1):
        for oy in range(-outline_width, outline_width+1):
            if ox == 0 and oy == 0:
                continue
            outline_surf = font.render(text, True, outline_color)
            surface.blit(outline_surf, (pos[0] + ox, pos[1] + oy))
    main_surf = font.render(text, True, fg_color)
    surface.blit(main_surf, pos)

# =======================
# Recognition / decision functions
# =======================
def recognize_hand_gesture(hand_landmarks, hand_label=None):
    """More robust hand gesture recognition (thresholds + majority rules):
    - Uses TIP vs PIP y-differences with thresholds to avoid jitter
    - Uses TIP.x - IP.x for thumb with handedness info
    - Returns: 'rock' / 'paper' / 'scissors' / None
    """
    lm = hand_landmarks.landmark

    # Thresholds (empirical, tweakable)
    THRESH_Y = 0.04  # TIP above PIP by this amount => finger considered extended
    THRESH_THUMB_X = 0.03  # thumb x-axis difference threshold

    # safe reader to avoid index errors
    def y_diff(tip_idx, pip_idx):
        try:
            return lm[pip_idx].y - lm[tip_idx].y
        except Exception:
            return 0.0

    # For the other four fingers: PIP.y - TIP.y > THRESH_Y indicates extended
    index_open = y_diff(mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.INDEX_FINGER_PIP) > THRESH_Y
    middle_open = y_diff(mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP) > THRESH_Y
    ring_open = y_diff(mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_PIP) > THRESH_Y
    pinky_open = y_diff(mp_hands.HandLandmark.PINKY_TIP, mp_hands.HandLandmark.PINKY_PIP) > THRESH_Y

    # Thumb detection: use x-axis difference and handedness
    try:
        thumb_tip = lm[mp_hands.HandLandmark.THUMB_TIP]
        thumb_ip = lm[mp_hands.HandLandmark.THUMB_IP]
        thumb_dx = thumb_tip.x - thumb_ip.x
    except Exception:
        thumb_dx = 0.0

    if hand_label == 'Right':
        thumb_open = thumb_dx > THRESH_THUMB_X
    elif hand_label == 'Left':
        thumb_open = thumb_dx < -THRESH_THUMB_X
    else:
        # When handedness is unavailable, relax condition: either x diff or y diff can indicate thumb open
        thumb_open = abs(thumb_dx) > THRESH_THUMB_X or y_diff(mp_hands.HandLandmark.THUMB_TIP, mp_hands.HandLandmark.THUMB_IP) > THRESH_Y

    # Count opened fingers
    fingers_open = [thumb_open, index_open, middle_open, ring_open, pinky_open]
    open_count = sum(1 for f in fingers_open if f)

    # Decision rules (thresholds + open count)
    # paper: majority of fingers (>=4) extended
    if open_count >= 4:
        return "paper"
    # Scissors: index and middle fingers extended, others bent
    if index_open and middle_open and not ring_open and not pinky_open:
        # Thumb can be any state and it's still counted as scissors
        return "scissors"
    # Rock: no fingers clearly extended
    if open_count == 0:
        return "rock"

    # If uncertain, return None (upper layer can use buffering/fallback)
    return None

def determine_result(player, cat):
    """Determine result of the round.
    Normalizes inputs and handles invalid input by returning "No Move".
    Returns: "Draw" / "You Win!" / "You Lose!" / "No Move"
    """
    if not player or not cat:
        return "No Move"

    p = str(player).lower()
    c = str(cat).lower()

    if p == c:
        return "Draw"
    if (p == "rock" and c == "scissors") or \
       (p == "scissors" and c == "paper") or \
       (p == "paper" and c == "rock"):
        return "You Win!"
    return "You Lose!"

def reset_round():
    global player_gesture, current_hand, counting_down, countdown_start, cat_hand_y
    player_gesture = None
    counting_down = False
    countdown_start = 0
    current_hand = random.choice(["rock","paper","scissors"])
    cat_hand_y = cat_start_y
    # require player to trigger the next round again
    global start_triggered
    start_triggered = False

# =======================
# Main loop
# =======================
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Capture camera
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    # Prepare RGB image for MediaPipe
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Let MediaPipe process the frame (one pass, results used below)
    results = hands.process(frame_rgb)

    # =======================
    # Player gesture recognition (using processed results)
    # =======================
    if not counting_down and not show_result and results.multi_hand_landmarks:
    # Read handedness list (may be None)
        handedness_list = results.multi_handedness if results.multi_handedness else [None] * len(results.multi_hand_landmarks)
        for hand_landmarks, hand_handedness in zip(results.multi_hand_landmarks, handedness_list):
            hand_label = None
            try:
                hand_label = hand_handedness.classification[0].label
            except Exception:
                hand_label = None
            gesture = recognize_hand_gesture(hand_landmarks, hand_label)
            # Start trigger: require consecutive frames of paper (hand extended) to begin; reduces false triggers
            start_buffer.append(gesture)
            # When N consecutive frames are paper (or rock for tolerance) start countdown
            # Accept either paper or rock for robustness
            if len(start_buffer) == start_buffer.maxlen and all((g in ("paper","rock")) and g is not None for g in start_buffer):
                # Set the player's current gesture to the most frequent gesture in the recent buffer
                # Prefer the most common (e.g., if buffer contains paper/rock, choose the one with higher count)
                try:
                    counts_start = {}
                    for g in start_buffer:
                        if g:
                            counts_start[g] = counts_start.get(g, 0) + 1
                    if counts_start:
                        player_gesture = max(counts_start.items(), key=lambda x: x[1])[0]
                    else:
                        player_gesture = "paper"
                except Exception:
                    player_gesture = "paper"
                start_triggered = True
                counting_down = True
                countdown_start = pygame.time.get_ticks()
                start_buffer.clear()
                # Clear final gesture buffer to prepare for next collection
                final_gesture_buffer.clear()
                break

    # =======================
    # Draw scrolling background (wraps toward bottom-right)
    # Use offsets and wrap at tile boundaries to avoid heavy allocations
    # =======================
    tile_w = background_image.get_width()
    tile_h = background_image.get_height()
    # Update offsets (keep within [0, tile_w) / [0, tile_h) range)
    bg_offset_x = (bg_offset_x + bg_speed_x) % tile_w
    bg_offset_y = (bg_offset_y + bg_speed_y) % tile_h

    # Compute starting draw point (start from negative offset to cover the whole window)
    start_x = -int(bg_offset_x)
    while start_x < WINDOW_WIDTH:
        start_y = -int(bg_offset_y)
        while start_y < WINDOW_HEIGHT:
            screen.blit(background_image, (start_x, start_y))
            start_y += tile_h
        start_x += tile_w

    # If counting down: show only the countdown
    if counting_down:
        font_count = pygame.font.Font(None, 160)
        elapsed = (pygame.time.get_ticks() - countdown_start) // 1000
        remaining = max(0, countdown - elapsed)
        text_str = str(remaining)
    # Pink theme: foreground is lightpink, outline is darker pink
        fg = (255, 182, 193)  # lightpink
        outline = (219, 112, 147)  # palevioletred
        text_surf = font_count.render(text_str, True, fg)
        pos = (WINDOW_WIDTH // 2 - text_surf.get_width() // 2,
               WINDOW_HEIGHT // 2 - text_surf.get_height() // 2)
        draw_text_with_outline(screen, text_str, font_count, pos, fg, outline, outline_width=3)
    # Skip to screen refresh
    else:
    # =======================
    # Draw camera preview (with landmarks)
    # Camera preview is hidden during countdown (controlled by counting_down)
    # =======================
        if not counting_down:
            if SHOW_LANDMARKS and 'results' in locals() and results and results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    try:
                        mp_drawing.draw_landmarks(frame,
                                                  hand_landmarks,
                                                  mp_hands.HAND_CONNECTIONS,
                                                  mp_styles.get_default_hand_landmarks_style(),
                                                  mp_styles.get_default_hand_connections_style())
                    except Exception:
                        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Convert the BGR frame (with drawings) to RGB for pygame display
            display_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_surface = pygame.surfarray.make_surface(display_rgb.swapaxes(0,1))
            cam_aspect = frame.shape[1] / frame.shape[0]
            if cam_width / cam_height > cam_aspect:
                new_height = cam_height
                new_width = int(cam_height * cam_aspect)
            else:
                new_width = cam_width
                new_height = int(cam_width / cam_aspect)
            frame_surface = pygame.transform.scale(frame_surface, (new_width, new_height))
            # Compute camera display position and draw a white border around it
            cam_x = WINDOW_WIDTH - new_width - 10
            cam_y = WINDOW_HEIGHT - new_height - 10
            border_thickness = 4  # white border thickness (pixels)
            # Draw border (outline only, not filled)
            pygame.draw.rect(screen, (255, 255, 255), (cam_x - border_thickness, cam_y - border_thickness,
                               new_width + border_thickness * 2, new_height + border_thickness * 2),
                     border_thickness)
            screen.blit(frame_surface, (cam_x, cam_y))

    # If the round hasn't been triggered yet, show a hint on how to start
    if not start_triggered and not counting_down and not show_result:
        hint_font = pygame.font.Font(None, 36)
        hint_text = "Show hand to start"
        draw_text_with_outline(screen, hint_text, hint_font, (10, 10), (255, 182, 193), (219, 112, 147), outline_width=2)

    # During revealing, collect several frames into final_gesture_buffer for a majority-vote decision
    if revealing and results and results.multi_hand_landmarks:
        try:
            handedness_list_collect = results.multi_handedness if results.multi_handedness else [None] * len(results.multi_hand_landmarks)
            # Only take the first detected hand as the player's gesture sample
            hand_landmarks_c = results.multi_hand_landmarks[0]
            hand_handedness_c = handedness_list_collect[0] if handedness_list_collect else None
            hand_label_c = None
            try:
                hand_label_c = hand_handedness_c.classification[0].label
            except Exception:
                hand_label_c = None
            detected_c = recognize_hand_gesture(hand_landmarks_c, hand_label_c)
            final_gesture_buffer.append(detected_c)
        except Exception:
            # Ignore any errors that may occur during collection
            pass

    # Display the currently detected player gesture (for debugging/feedback)
    if player_gesture and not counting_down and not show_result:
        dbg_font = pygame.font.Font(None, 36)
        dbg_text = f"Detected: {player_gesture}"
        # Show debug text with pink outline
        draw_text_with_outline(screen, dbg_text, dbg_font, (10, WINDOW_HEIGHT - 48), (255, 182, 193), (219, 112, 147), outline_width=2)

    # =======================
    # Countdown handling (timing logic calculated before drawing)
    # =======================
    if counting_down:
        elapsed = (pygame.time.get_ticks() - countdown_start) // 1000
        remaining = countdown - elapsed
        if remaining <= 0:
            # Countdown finished; start cat paw reveal animation
            counting_down = False
            cat_gesture = random.choice(["rock","paper","scissors"])
            current_hand = cat_gesture
            revealing = True
            # (Removed) cat punch sound — now played once at startup

    # =======================
    # Cat paw reveal animation (runs while revealing)
    # =======================
    if revealing:
        # Try to move toward target position (no-op if already there)
        if cat_hand_y < cat_target_y:
            cat_hand_y += cat_speed

        # If reaches or passes target, finalize reveal and decide result
        if cat_hand_y >= cat_target_y:
            cat_hand_y = cat_target_y
            revealing = False
            # After reveal, determine player's final gesture (use final_gesture_buffer majority first, fall back to single-frame or triggered player_gesture)
            final_player_gesture = player_gesture
            # Choose the most frequent non-None value from buffer
            try:
                counts = {}
                for g in final_gesture_buffer:
                    if g:
                        counts[g] = counts.get(g, 0) + 1
                if counts:
                    # Select the gesture with the highest count
                    final_player_gesture = max(counts.items(), key=lambda x: x[1])[0]
                else:
                    # If buffer has no valid detections, attempt a quick detection on current frame as fallback
                    try:
                        final_results = hands.process(frame_rgb)
                        if final_results and final_results.multi_hand_landmarks:
                            handedness_list_final = final_results.multi_handedness if final_results.multi_handedness else [None] * len(final_results.multi_hand_landmarks)
                            hand_landmarks_f = final_results.multi_hand_landmarks[0]
                            hand_handedness_f = handedness_list_final[0] if handedness_list_final else None
                            hand_label_f = None
                            try:
                                hand_label_f = hand_handedness_f.classification[0].label
                            except Exception:
                                hand_label_f = None
                            detected = recognize_hand_gesture(hand_landmarks_f, hand_label_f)
                            if detected:
                                final_player_gesture = detected
                    except Exception:
                        pass
            except Exception:
                # On extreme error, fall back to known player_gesture
                final_player_gesture = player_gesture
            # Clear buffer for next round
            final_gesture_buffer.clear()
            player_gesture = final_player_gesture
            # Show result after reveal
            show_result = True
            result_text = determine_result(final_player_gesture, cat_gesture)
            result_timer = pygame.time.get_ticks()
            # Play win/lose/draw sounds if loaded
            try:
                if result_text == "You Win!" and win_sound:
                    win_sound.play()
                elif result_text == "You Lose!" and lose_sound:
                    lose_sound.play()
                elif result_text == "Draw" and draw_sound:
                    draw_sound.play()
            except Exception:
                # Ignore playback errors to ensure the game continues
                pass
            # Next round requires retriggering
            start_triggered = False

    # =======================
    # Draw cat paw (not shown during countdown)
    # =======================
    if not counting_down:
        screen.blit(cat_hands[current_hand], (cat_hand_x, cat_hand_y))

    # =======================
    # Display result
    # =======================
    if show_result:
    # Pink theme: main color and outline use different shades to stand out
        if result_text == "You Win!":
            fg = (255, 105, 180)  # hotpink
            outline_col = (199, 21, 133)  # medium violet red
            size = 160
        elif result_text == "You Lose!":
            fg = (255, 140, 171)  # lighter pink
            outline_col = (219, 112, 147)
            size = 130
        else:
            fg = (255, 182, 193)  # lightpink
            outline_col = (219, 112, 147)
            size = 110
        font_res = pygame.font.Font(None, size)
        # Center position
        tmp = font_res.render(result_text, True, fg)
        pos = (WINDOW_WIDTH//2 - tmp.get_width()//2, WINDOW_HEIGHT//2 - tmp.get_height()//2)
        draw_text_with_outline(screen, result_text, font_res, pos, fg, outline_col, outline_width=4)
        if pygame.time.get_ticks() - result_timer > 5000:  # show for 5 seconds
            show_result = False
            reset_round()

    # Refresh screen
    pygame.display.flip()
    clock.tick(30)

# Release resources
cap.release()
pygame.quit()
sys.exit()