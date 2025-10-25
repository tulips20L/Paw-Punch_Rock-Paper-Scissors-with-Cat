# Paw-Punch — Cat Paw Rock Paper Scissors

Paw-Punch is a cute, camera-driven Rock-Paper-Scissors game where you play against a cat paw.
The game uses your webcam and MediaPipe Hands to recognize your hand gesture (rock / paper / scissors),
and Pygame for the UI, animation and optional sound effects.

Features
- Real-time webcam preview
- MediaPipe-based hand gesture recognition with simple smoothing to reduce jitter
- Cute cat-paw animations (assets in `assets/`)
- Optional sound effects and background music (put audio files into `sounds/`)

Quick start
1. Create and activate a Python virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the game:

```powershell
python .\scripts\Paw-Punch.py
```

Gameplay
- When the window opens, show your hand to the camera to trigger a round. A short countdown will start.
- During the reveal the game samples several frames and uses a majority vote to decide your final gesture.
- The cat paw will randomly choose rock/paper/scissors and the result will be shown on screen.

Troubleshooting
- Camera errors: ensure no other application is using the webcam. If your device uses a different camera index, change `cv2.VideoCapture(0)` in `scripts/Paw-Punch.py` (try `1`, `2`, ...).
- Audio problems: some remote or headless environments don't support audio; the script will continue even if mixer initialization fails.
- Recognition instability: try increasing buffer sizes or adjusting thresholds inside `recognize_hand_gesture` (look for THRESH_Y and THRESH_THUMB_X).

Files of interest
- `scripts/Paw-Punch.py` — main script
- `assets/` — images used by the UI (Background.png, Cat Hands.png)
- `sounds/` — optional audio files (Cat_Meow.wav, Win.wav, Lose.wav, Draw.wav, Hopeful.mp3)
- `requirements.txt` — Python package dependencies

Contributing ideas
- Add more polished animations
- Collect gesture examples to train a small classifier for more robust recognition
- Add options UI to tune thresholds and buffer lengths

Enjoy playing with the cat paw! 🐱

Attribution
- Images / artwork (Cat Hands, etc.): https://nj-prod.itch.io/rock-paper-scissors
- Sound effects (SFX pack): https://coffeevalenbat.itch.io/sweet-sounds-sfx-pack
- Background music: https://freepd.com


