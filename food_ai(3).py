# -*- coding: utf-8 -*-
"""
Food AI — Ingredient Recognizer & Recipe Suggester
=====================================================
A single self-contained file: no separate data files, no API key, no
sign-up, no internet needed after the one-time AI model download.

HOW TO RUN (as a script, for testing):
    pip3 install torch transformers pillow
    python3 food_ai.py

Running it with no arguments opens a native "choose a photo" window.
You can also run it with a path directly:
    python3 food_ai.py path/to/photo.jpg

HOW TO TURN THIS INTO A REAL APP (no code visible, just double-click):
    See the instructions at the very bottom of this file.
"""

import sys
import json
import queue
import threading
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import filedialog

import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

# ---------------------------------------------------------------------------
# 1. INGREDIENTS THE MODEL CAN RECOGNIZE
# ---------------------------------------------------------------------------
INGREDIENTS = [
    "tomato", "onion", "potato", "garlic", "carrot", "eggplant", "bell pepper",
    "cucumber", "lettuce", "spinach", "mushroom", "broccoli", "cabbage",
    "zucchini", "lemon", "lime", "apple", "banana", "egg", "chicken meat",
    "ground beef", "beef steak", "fish", "shrimp", "rice", "pasta", "bread",
    "flour", "cheese", "milk", "yogurt", "butter", "cream", "olive oil",
    "cooking oil", "beans", "lentils", "chickpeas", "walnut", "almond",
    "parsley", "cilantro", "dill", "mint", "basil", "ginger",
    "turmeric powder", "saffron", "cinnamon", "corn", "green peas", "pumpkin",
    "orange", "grapes", "watermelon", "pomegranate", "dates", "honey",
    "sausage", "bacon", "tofu", "avocado",
]

# ---------------------------------------------------------------------------
# 2. LOCAL RECIPE DATABASE
# ---------------------------------------------------------------------------
RECIPES = [
    {
        "name": "Tomato Omelette",
        "ingredients": ["egg", "tomato", "onion", "cooking oil"],
        "time": "15 min",
        "instructions": [
            "Chop the onion and saute in oil until golden.",
            "Add chopped tomato and cook until it releases its juices.",
            "Beat the eggs and pour over the mixture.",
            "Lower the heat, cover, and cook until the eggs are set.",
        ],
    },
    {
        "name": "Cheesy Fried Potatoes",
        "ingredients": ["potato", "cheese", "cooking oil"],
        "time": "25 min",
        "instructions": [
            "Peel the potatoes and cut into strips.",
            "Fry in hot oil until golden and crispy.",
            "Sprinkle grated cheese over the hot potatoes so it melts.",
            "Serve warm.",
        ],
    },
    {
        "name": "Lettuce and Cucumber Salad",
        "ingredients": ["lettuce", "cucumber", "tomato", "lemon", "olive oil"],
        "time": "10 min",
        "instructions": [
            "Chop the lettuce, cucumber, and tomato.",
            "Combine everything in a bowl.",
            "Whisk lemon juice with olive oil and pour over the salad.",
            "Add salt and pepper to taste and toss.",
        ],
    },
    {
        "name": "Simple Beef Stew",
        "ingredients": ["ground beef", "beans", "tomato", "onion"],
        "time": "60 min",
        "instructions": [
            "Chop the onion and saute until golden.",
            "Add ground beef and cook until browned.",
            "Add tomato paste or crushed tomatoes and cook briefly.",
            "Add water and simmer on low heat for about 45 minutes.",
            "Add the beans and simmer for another 10 minutes.",
        ],
    },
    {
        "name": "Homemade Grilled Chicken",
        "ingredients": ["chicken meat", "onion", "lemon", "turmeric powder"],
        "time": "40 min (+ marinating time)",
        "instructions": [
            "Cut the chicken into pieces.",
            "Grate the onion and mix with lemon juice, turmeric, and salt.",
            "Marinate the chicken in this mixture for at least 30 minutes (longer is better).",
            "Grill or pan-fry until fully cooked.",
        ],
    },
    {
        "name": "Pasta with Tomato Sauce",
        "ingredients": ["pasta", "tomato", "onion", "garlic", "cheese"],
        "time": "30 min",
        "instructions": [
            "Cook the pasta according to package instructions.",
            "Saute onion and garlic until soft.",
            "Add tomato and let it break down into a sauce.",
            "Mix the cooked pasta with the sauce.",
            "Top with grated cheese and serve.",
        ],
    },
    {
        "name": "Lentil Soup",
        "ingredients": ["lentils", "onion", "potato"],
        "time": "40 min",
        "instructions": [
            "Chop and saute the onion.",
            "Add lentils and chopped potato.",
            "Add enough water and simmer until soft.",
            "Blend lightly for a creamier texture if desired.",
        ],
    },
    {
        "name": "Potato Egg Patties",
        "ingredients": ["potato", "egg", "onion"],
        "time": "30 min",
        "instructions": [
            "Boil the potatoes, peel, and grate them.",
            "Grate the onion and mix with the potato.",
            "Add the egg and mix well.",
            "Shape into patties and fry both sides in oil until golden.",
        ],
    },
    {
        "name": "Yogurt and Cucumber Dip",
        "ingredients": ["yogurt", "cucumber", "mint"],
        "time": "10 min",
        "instructions": [
            "Grate or finely dice the cucumber.",
            "Mix with yogurt.",
            "Add dried or fresh mint and a pinch of salt.",
        ],
    },
    {
        "name": "Mushroom Soup",
        "ingredients": ["mushroom", "onion", "milk", "butter"],
        "time": "25 min",
        "instructions": [
            "Saute the onion in butter.",
            "Add chopped mushrooms and cook until soft.",
            "Add milk and bring to a gentle simmer.",
            "Season with salt and pepper to taste.",
        ],
    },
    {
        "name": "Fish and Avocado Salad",
        "ingredients": ["fish", "avocado", "lemon"],
        "time": "20 min",
        "instructions": [
            "Season the fish with salt and lemon juice, then pan-fry or grill.",
            "Slice the avocado.",
            "Arrange the fish and avocado together on a plate.",
            "Drizzle with lemon juice and a little olive oil.",
        ],
    },
    {
        "name": "Egg Sandwich",
        "ingredients": ["egg", "bread", "lettuce"],
        "time": "10 min",
        "instructions": [
            "Boil or fry the egg.",
            "Slice the bread.",
            "Layer lettuce and egg inside the bread and serve.",
        ],
    },
    {
        "name": "Simple Chicken and Rice",
        "ingredients": ["rice", "chicken meat", "onion", "turmeric powder"],
        "time": "50 min",
        "instructions": [
            "Saute the chicken with onion and turmeric until it changes color.",
            "Add water and simmer until the chicken is fully cooked.",
            "Cook the rice separately until tender.",
            "Serve the rice and chicken together.",
        ],
    },
    {
        "name": "Braised Spinach",
        "ingredients": ["spinach", "onion", "lemon"],
        "time": "35 min",
        "instructions": [
            "Saute the onion until soft.",
            "Add chopped spinach and let it wilt and release liquid.",
            "Add lemon juice and simmer on low heat.",
        ],
    },
    {
        "name": "Simple Pancakes",
        "ingredients": ["flour", "egg", "milk", "butter"],
        "time": "20 min",
        "instructions": [
            "Whisk flour, egg, and milk together into a smooth batter.",
            "Grease a pan with a little butter.",
            "Pour some batter and cook both sides until golden.",
        ],
    },
    {
        "name": "Fruit Salad",
        "ingredients": ["apple", "banana", "orange", "grapes"],
        "time": "10 min",
        "instructions": [
            "Peel the fruit where needed and chop into bite-sized pieces.",
            "Combine everything in a bowl.",
            "Drizzle with honey if desired.",
        ],
    },
    {
        "name": "Bread, Cheese, and Herbs Plate",
        "ingredients": ["bread", "cheese", "parsley", "mint"],
        "time": "5 min",
        "instructions": [
            "Wash and chop the fresh herbs.",
            "Arrange the bread, cheese, and herbs together on a plate.",
        ],
    },
    {
        "name": "Sauteed Zucchini with Egg",
        "ingredients": ["zucchini", "egg", "onion"],
        "time": "20 min",
        "instructions": [
            "Saute the onion until soft.",
            "Add chopped zucchini and cook until tender.",
            "Beat the eggs, pour over the mixture, and let set.",
        ],
    },
    {
        "name": "Bean and Tomato Stew",
        "ingredients": ["beans", "tomato", "onion", "garlic"],
        "time": "40 min",
        "instructions": [
            "Saute the onion and garlic.",
            "Add tomato and let it break down.",
            "Add the beans (cooked or canned).",
            "Simmer gently for 15 minutes to let the flavors combine.",
        ],
    },
    {
        "name": "Garlic Lemon Shrimp",
        "ingredients": ["shrimp", "garlic", "lemon", "butter"],
        "time": "15 min",
        "instructions": [
            "Melt the butter in a pan and saute the garlic.",
            "Add the shrimp and cook on high heat until pink.",
            "Finish with lemon juice and serve immediately.",
        ],
    },
]

MODEL_NAME = "openai/clip-vit-base-patch32"
SIMILARITY_THRESHOLD = 0.22
OUTPUT_HTML = Path(__file__).parent / "result.html"


# ---------------------------------------------------------------------------
# 3. AI LOGIC
# ---------------------------------------------------------------------------

def load_model():
    print("Loading the AI model...")
    model = CLIPModel.from_pretrained(MODEL_NAME)
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    model.eval()
    return model, processor


def detect_ingredients(model, processor, image_path: str) -> list[str]:
    image = Image.open(image_path).convert("RGB")
    prompts = [f"a photo of {name}, a food ingredient" for name in INGREDIENTS]

    inputs = processor(text=prompts, images=image, return_tensors="pt", padding=True)

    with torch.no_grad():
        outputs = model(**inputs)
        image_embeds = outputs.image_embeds / outputs.image_embeds.norm(dim=-1, keepdim=True)
        text_embeds = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)
        similarities = (image_embeds @ text_embeds.T).squeeze(0)

    detected = []
    for name, score in zip(INGREDIENTS, similarities.tolist()):
        if score >= SIMILARITY_THRESHOLD:
            detected.append((name, score))

    detected.sort(key=lambda x: x[1], reverse=True)
    return [name for name, _ in detected]


def match_recipes(detected_ingredients: list[str], top_n: int = 6) -> list[dict]:
    detected_set = set(detected_ingredients)
    scored = []

    for recipe in RECIPES:
        recipe_ingredients = set(recipe["ingredients"])
        matched = recipe_ingredients & detected_set
        if not matched:
            continue
        coverage = len(matched) / len(recipe_ingredients)
        missing = recipe_ingredients - detected_set
        scored.append({
            **recipe,
            "coverage": coverage,
            "matched_count": len(matched),
            "missing": sorted(missing),
        })

    scored.sort(key=lambda r: (r["coverage"], r["matched_count"]), reverse=True)
    return scored[:top_n]


# ---------------------------------------------------------------------------
# 4. HTML REPORT GENERATION
# ---------------------------------------------------------------------------

def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_ingredient_chip(name: str, missing: bool = False) -> str:
    cls = "chip chip-missing" if missing else "chip"
    return f'<span class="{cls}">{esc(name)}</span>'


def render_recipe_card(recipe: dict, index: int) -> str:
    ingredient_chips = "".join(
        render_ingredient_chip(ing, missing=ing in recipe["missing"])
        for ing in recipe["ingredients"]
    )
    steps_html = "".join(
        f'<li><span class="step-num">{i}</span><span>{esc(step)}</span></li>'
        for i, step in enumerate(recipe["instructions"], start=1)
    )
    if recipe["missing"]:
        status_html = f'<div class="status status-missing">Missing: {esc(", ".join(recipe["missing"]))}</div>'
    else:
        status_html = '<div class="status status-ready">You have everything</div>'

    return f"""
    <article class="recipe-card">
      <div class="recipe-card-head">
        <span class="recipe-index">{index:02d}</span>
        <div>
          <h3>{esc(recipe['name'])}</h3>
          <span class="time-badge">⏱ {esc(recipe['time'])}</span>
        </div>
      </div>
      <div class="chip-row">{ingredient_chips}</div>
      {status_html}
      <ol class="steps">{steps_html}</ol>
    </article>
    """


def render_html(detected_ingredients: list[str], matches: list[dict]) -> str:
    detected_chips = (
        "".join(render_ingredient_chip(name) for name in detected_ingredients)
        if detected_ingredients
        else '<p class="empty-note">No familiar ingredients were found.</p>'
    )
    if matches:
        cards_html = "".join(render_recipe_card(r, i) for i, r in enumerate(matches, start=1))
    else:
        cards_html = '<p class="empty-note">No matching recipe was found.</p>'

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<title>What Should I Cook?</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --ink: #201d18; --paper: #faf3e3; --paper-soft: #f1e7d0;
    --night: #1b1a17; --night-soft: #26241f;
    --saffron: #d9a441; --saffron-dim: #b8862f;
    --herb: #566b3f; --herb-soft: #e4ead9;
    --clay: #b5563e; --muted: #a99d84;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: 'Vazirmatn', -apple-system, 'Segoe UI', Arial, sans-serif;
          background: var(--paper); color: var(--ink); }}
  .hero {{ background: var(--night); color: var(--paper); padding: 64px 24px 96px;
           text-align: center; position: relative; overflow: hidden; }}
  .hero::after {{ content: ""; position: absolute; left: 0; right: 0; bottom: -1px; height: 60px;
    background: var(--paper);
    clip-path: polygon(0 100%, 100% 100%, 100% 0, 95% 40%, 90% 10%, 85% 45%, 80% 15%, 75% 40%,
      70% 10%, 65% 45%, 60% 15%, 55% 40%, 50% 10%, 45% 45%, 40% 15%, 35% 40%,
      30% 10%, 25% 45%, 20% 15%, 15% 40%, 10% 10%, 5% 45%, 0 15%); }}
  .eyebrow {{ letter-spacing: 4px; color: var(--saffron); font-size: 13px; font-weight: 600;
              margin-bottom: 18px; text-transform: uppercase; }}
  .hero h1 {{ font-size: clamp(34px, 6vw, 56px); font-weight: 800; margin: 0 0 12px; }}
  .hero p.sub {{ color: var(--muted); font-size: 16px; margin: 0 0 36px; }}
  .detected-panel {{ max-width: 720px; margin: 0 auto; background: var(--night-soft);
    border: 1px solid #3a3730; border-radius: 18px; padding: 22px 26px; }}
  .detected-panel h2 {{ font-size: 14px; color: var(--saffron); margin: 0 0 14px;
    font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
  .chip-row {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }}
  .chip {{ background: var(--herb-soft); color: var(--herb); border: 1px solid #cdd9bc;
    padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 600;
    text-transform: capitalize; }}
  .detected-panel .chip {{ background: #33312a; color: var(--paper); border-color: #47443a; }}
  .chip-missing {{ background: #f5e3dc !important; color: var(--clay) !important;
    border-color: #e6c4b6 !important; text-decoration: line-through; opacity: 0.85; }}
  main {{ max-width: 980px; margin: -40px auto 0; padding: 0 24px 80px; position: relative; }}
  .section-title {{ text-align: center; font-size: 26px; font-weight: 800; margin: 24px 0 36px; }}
  .recipe-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 22px; }}
  .recipe-card {{ background: #fffdf8; border: 1px solid #e9dfc8; border-radius: 18px;
    padding: 24px; box-shadow: 0 1px 3px rgba(32, 29, 24, 0.06); }}
  .recipe-card-head {{ display: flex; align-items: flex-start; gap: 14px; margin-bottom: 16px; }}
  .recipe-index {{ font-size: 13px; font-weight: 800; color: var(--saffron-dim); background: #fbeed2;
    border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center;
    justify-content: center; flex-shrink: 0; }}
  .recipe-card h3 {{ margin: 0 0 6px; font-size: 19px; font-weight: 800; }}
  .time-badge {{ font-size: 12px; color: var(--muted); font-weight: 600; }}
  .recipe-card .chip-row {{ justify-content: flex-start; margin-bottom: 14px; }}
  .status {{ font-size: 12.5px; font-weight: 700; padding: 7px 12px; border-radius: 10px;
    margin-bottom: 16px; display: inline-block; }}
  .status-ready {{ background: var(--herb-soft); color: var(--herb); }}
  .status-missing {{ background: #f5e3dc; color: var(--clay); }}
  .steps {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }}
  .steps li {{ display: flex; gap: 10px; font-size: 14px; line-height: 1.7; color: #3a352c; }}
  .step-num {{ flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%; background: var(--paper-soft);
    color: var(--ink); font-size: 11px; font-weight: 800; display: flex; align-items: center;
    justify-content: center; margin-top: 2px; }}
  .empty-note {{ text-align: center; color: var(--muted); font-size: 15px; }}
  footer {{ text-align: center; padding: 30px; color: var(--muted); font-size: 12.5px; }}
  @media (max-width: 480px) {{ .hero {{ padding: 48px 16px 90px; }} main {{ padding: 0 14px 60px; }} }}
</style>
</head>
<body>
  <section class="hero">
    <div class="eyebrow">Ingredient Detection</div>
    <h1>What Should I Cook?</h1>
    <p class="sub">Based on your photo, here's what I found</p>
    <div class="detected-panel">
      <h2>Detected Ingredients</h2>
      <div class="chip-row">{detected_chips}</div>
    </div>
  </section>
  <main>
    <h2 class="section-title">Recipes You Can Make</h2>
    <div class="recipe-grid">{cards_html}</div>
  </main>
  <footer>Built entirely offline — no internet connection required</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# 5. THE APP WINDOW (a proper welcome screen, not just a file dialog)
# ---------------------------------------------------------------------------
# Colors match the saffron / dark-kitchen theme used in the HTML report.
BG_NIGHT = "#1b1a17"
BG_NIGHT_SOFT = "#26241f"
SAFFRON = "#d9a441"
SAFFRON_HOVER = "#e8b75a"
CREAM = "#faf3e3"
MUTED = "#a99d84"


class FoodAIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Food AI")
        self.root.geometry("480x420")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_NIGHT)

        self.status_queue = None
        self.build_home_screen()

    # -- screen builders -----------------------------------------------

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def build_home_screen(self):
        self.clear_window()

        wrapper = tk.Frame(self.root, bg=BG_NIGHT)
        wrapper.pack(expand=True, fill="both", padx=32, pady=32)

        tk.Label(
            wrapper, text="🍳", font=("Helvetica", 48), bg=BG_NIGHT,
        ).pack(pady=(20, 6))

        tk.Label(
            wrapper, text="Food AI", font=("Helvetica", 26, "bold"),
            fg=CREAM, bg=BG_NIGHT,
        ).pack()

        tk.Label(
            wrapper,
            text="Snap a photo of your ingredients and I'll tell\nyou what you can cook.",
            font=("Helvetica", 12), fg=MUTED, bg=BG_NIGHT, justify="center",
        ).pack(pady=(8, 28))

        self.select_button = tk.Button(
            wrapper, text="📷  Select a Photo", font=("Helvetica", 13, "bold"),
            fg=BG_NIGHT, bg=SAFFRON, activebackground=SAFFRON_HOVER,
            activeforeground=BG_NIGHT, relief="flat", bd=0,
            padx=24, pady=12, cursor="hand2",
            command=self.on_choose_photo,
        )
        self.select_button.pack()

        tk.Label(
            wrapper, text="Works completely offline — no account, no cost",
            font=("Helvetica", 10), fg=MUTED, bg=BG_NIGHT,
        ).pack(side="bottom", pady=(20, 0))

    def build_processing_screen(self):
        self.clear_window()

        wrapper = tk.Frame(self.root, bg=BG_NIGHT)
        wrapper.pack(expand=True, fill="both", padx=32, pady=32)

        tk.Label(
            wrapper, text="🔎", font=("Helvetica", 40), bg=BG_NIGHT,
        ).pack(pady=(40, 10))

        self.status_label = tk.Label(
            wrapper, text="Getting started...", font=("Helvetica", 13),
            fg=CREAM, bg=BG_NIGHT, wraplength=380, justify="center",
        )
        self.status_label.pack(pady=6)

        tk.Label(
            wrapper, text="(the first run downloads the AI model — please be patient)",
            font=("Helvetica", 10), fg=MUTED, bg=BG_NIGHT,
        ).pack(pady=(4, 0))

    def build_done_screen(self, error: str | None = None):
        self.clear_window()

        wrapper = tk.Frame(self.root, bg=BG_NIGHT)
        wrapper.pack(expand=True, fill="both", padx=32, pady=32)

        if error:
            tk.Label(wrapper, text="⚠️", font=("Helvetica", 40), bg=BG_NIGHT).pack(pady=(20, 10))
            tk.Label(
                wrapper, text="Something went wrong", font=("Helvetica", 16, "bold"),
                fg=CREAM, bg=BG_NIGHT,
            ).pack()
            tk.Label(
                wrapper, text=error, font=("Helvetica", 10), fg=MUTED, bg=BG_NIGHT,
                wraplength=380, justify="center",
            ).pack(pady=(6, 24))
        else:
            tk.Label(wrapper, text="✅", font=("Helvetica", 40), bg=BG_NIGHT).pack(pady=(20, 10))
            tk.Label(
                wrapper, text="Done!", font=("Helvetica", 18, "bold"),
                fg=CREAM, bg=BG_NIGHT,
            ).pack()
            tk.Label(
                wrapper, text="Your results just opened in the browser.",
                font=("Helvetica", 12), fg=MUTED, bg=BG_NIGHT,
            ).pack(pady=(4, 24))

        tk.Button(
            wrapper, text="Try Another Photo", font=("Helvetica", 12, "bold"),
            fg=BG_NIGHT, bg=SAFFRON, activebackground=SAFFRON_HOVER,
            relief="flat", bd=0, padx=18, pady=10,
            command=self.build_home_screen,
        ).pack()

    # -- actions ----------------------------------------------------------

    def on_choose_photo(self):
        path = filedialog.askopenfilename(
            title="Choose a food photo",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp *.gif")],
        )
        if not path:
            return

        self.build_processing_screen()
        self.status_queue = queue.Queue()

        thread = threading.Thread(target=self._run_pipeline, args=(path,), daemon=True)
        thread.start()
        self.root.after(150, self._poll_status)

    def _run_pipeline(self, image_path: str):
        try:
            self.status_queue.put(("status", "Loading the AI model..."))
            model, processor = load_model()

            self.status_queue.put(("status", "Analyzing the image..."))
            detected = detect_ingredients(model, processor, image_path)
            matches = match_recipes(detected)

            html = render_html(detected, matches)
            OUTPUT_HTML.write_text(html, encoding="utf-8")

            self.status_queue.put(("status", "Opening your browser..."))
            webbrowser.open(f"file://{OUTPUT_HTML.resolve()}")

            self.status_queue.put(("done", None))
        except Exception as exc:  # noqa: BLE001
            self.status_queue.put(("error", str(exc)))

    def _poll_status(self):
        try:
            while True:
                kind, payload = self.status_queue.get_nowait()
                if kind == "status":
                    self.status_label.config(text=payload)
                elif kind == "done":
                    self.build_done_screen()
                    return
                elif kind == "error":
                    self.build_done_screen(error=payload)
                    return
        except queue.Empty:
            pass
        self.root.after(150, self._poll_status)


# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def main():
    # Running with a file path argument still works for quick command-line
    # testing, without opening the window.
    if len(sys.argv) >= 2:
        image_path = sys.argv[1]
        if not Path(image_path).exists():
            print(f"Image file not found: {image_path}")
            sys.exit(1)

        model, processor = load_model()
        print("Analyzing the image...")
        detected = detect_ingredients(model, processor, image_path)
        matches = match_recipes(detected)
        html = render_html(detected, matches)
        OUTPUT_HTML.write_text(html, encoding="utf-8")
        print(f"Result saved to: {OUTPUT_HTML}")
        webbrowser.open(f"file://{OUTPUT_HTML.resolve()}")
        return

    # No argument given -> launch the full app window
    root = tk.Tk()
    FoodAIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# HOW TO TURN THIS FILE INTO A REAL, DOUBLE-CLICKABLE APP (macOS)
# ---------------------------------------------------------------------------
# You need to run these commands on YOUR OWN Mac (this can't be built
# remotely — the app has to be built on the same type of computer it will
# run on).
#
# 1. Open Terminal and go to the folder with this file:
#       cd path/to/this/folder
#
# 2. Install the tool that builds the app:
#       pip3 install pyinstaller
#
# 3. Build it:
#       pyinstaller --onefile --windowed --name "Food AI" food_ai.py
#
# 4. Wait for it to finish (can take a few minutes). When done, look inside
#    the new "dist" folder — you'll find "Food AI.app". That's your real,
#    double-clickable application. No code is visible; it behaves like any
#    other Mac app icon.
#
# 5. (Optional) Drag "Food AI.app" into your Applications folder, or the
#    Dock, so it's always easy to open.
#
# 6. The first time you open it, macOS may block it ("unidentified
#    developer"). Right-click the app, choose "Open", then click "Open"
#    again in the popup. You only need to do this once.
#
# 7. Double-clicking the app opens a "choose a photo" window directly —
#    no terminal, no code. Pick a photo, wait a few seconds, and the
#    result opens in your browser automatically.
# ---------------------------------------------------------------------------
