# Smart Meal Planner

A desktop application that helps you search for recipes, plan meals for the week, generate a combined shopping list, and get AI-powered cooking tips.

---

## Features

- 🔍 Search meals by name, main ingredient, or category (using TheMealDB API)
- 📖 View full recipe details: ingredients, measurements, instructions, and image link
- 🤖 Optional Gemini AI assistant:
  - Simplifies cooking instructions
  - Estimates difficulty (Easy / Medium / Hard)
  - Suggests cheaper/local ingredient substitutes (Nigerian alternatives considered)
- 📅 Plan meals for each day of the week
- 👥 Adjust servings per meal; ingredient quantities scale automatically
- 🛒 Generate a combined shopping list from all planned meals
- 💾 Save and load meal plans, shopping lists, and favourite recipes locally (JSON files)

---

## Requirements

- Python 3.8 or newer (3.10+ recommended)
- The following Python packages:
  - `requests` – for TheMealDB API
  - `google-genai` – for Gemini AI (optional, but required for AI features)

---

## Installation

### Option A: Using a Virtual Environment (Recommended)

A virtual environment keeps your project dependencies isolated from other Python projects.  
This avoids version conflicts and is a good practice.

1. **Navigate to your project folder**  
   ```bash
   cd /path/to/recipe_planner
   ```

2. **Create a virtual environment**  
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment**  
   - **macOS / Linux:**  
     ```bash
     source venv/bin/activate
     ```
   - **Windows:**  
     ```bash
     venv\Scripts\activate
     ```
   After activation, your terminal prompt should show `(venv)`.

4. **Install required packages inside the venv**  
   ```bash
   pip install requests google-genai
   ```

5. **Run the app** (while venv is active)  
   ```bash
   python main.py
   ```

6. **To deactivate the venv later**, simply run:  
   ```bash
   deactivate
   ```

> **Troubleshooting venv issues**:  
> - If VS Code still shows a wrong interpreter after creating venv, press `Cmd+Shift+P` → “Python: Select Interpreter” → choose the one that points to `./venv/bin/python`.  
> - If the terminal doesn’t show `(venv)`, make sure you ran `source venv/bin/activate`.  
> - If you get `ModuleNotFoundError` for `google.genai`, ensure the package is installed **inside** the venv (`pip list | grep google`).  
> - If you prefer to avoid venv, see Option B.

---

### Option B: Global Installation (Simpler, but less isolated)

1. **Make sure Python is installed**  
   ```bash
   python3 --version
   ```
   If not installed, download from [python.org](https://www.python.org/downloads/).

2. **Install required packages globally**  
   ```bash
   pip3 install requests google-genai
   ```
   If `pip3` is not found, try:
   ```bash
   python3 -m pip install requests google-genai
   ```

3. **Run the app**  
   ```bash
   python3 main.py
   ```

---

## Configuration (for AI features)

The app works fine without Gemini. If you want the AI Assistant:

1. Get a free API key from [Google AI Studio](https://aistudio.google.com/).
2. Set the key as an environment variable in your terminal:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```
   (On Windows, use `set GEMINI_API_KEY=your_api_key_here`)

3. The app will automatically detect the key when you run it.

> **Note:** The Gemini model name may change over time. If you get a `404 model not found` error, open `planner.py` and change the line `model="gemini-2.0-flash-lite"` to a currently supported model (e.g., `"gemini-1.5-flash"` or `"gemini-2.0-flash"`). Check the [Google AI models page](https://ai.google.dev/gemini-api/docs/models) for the latest list.

---

## Running the App

Navigate to the project folder in the terminal:
```bash
cd /path/to/recipe_planner
```

Then run:
- **If using venv:** `python main.py` (after activating venv)
- **If using global install:** `python3 main.py`

A window titled **Smart Meal Planner** should open.

---

## How to Use

1. **Search**  
   - Choose search type from dropdown: `name`, `ingredient`, or `category`.
   - Type your query (e.g., "chicken", "rice", "Seafood").
   - Click **Search**. Results appear in the list.

2. **View a Recipe**  
   - Click on any result in the list.
   - The recipe details (name, category, cuisine, ingredients, instructions) appear in the main text area.

3. **AI Assistant (optional)**  
   - With a recipe displayed, click **AI Assistant**.
   - If Gemini is configured, it will add simplified instructions, difficulty, and substitutes to the text area.
   - If not configured, you’ll see a friendly error.

4. **Add to Meal Plan**  
   - Select a day from the dropdown (Monday–Sunday).
   - Enter the number of servings (e.g., 4).
   - Click **Add to Plan**.
   - Repeat for other meals.

5. **View Meal Plan**  
   - Click **Show Meal Plan** to see all planned meals.

6. **Generate Shopping List**  
   - After adding meals to the plan, click **Generate Shopping List**.
   - A new window shows a combined list of ingredients, scaled according to your servings.

7. **Favourites**  
   - With a recipe displayed, click **Add to Favourites** to save it.

8. **Save & Load**  
   - Click **Save All** to save the current meal plan, shopping list, and favourites to JSON files in the project folder.
   - When you restart the app, data is loaded automatically, or click **Load Saved** to refresh.

---

## File Structure

```
python_advanced_prj/
│
├── recipe.py           # Recipe class and API conversion
├── mealdb_client.py    # TheMealDB API communication
├── planner.py          # Meal planning, shopping list, Gemini, JSON helpers
└── main.py             # Tkinter GUI and threading
├── favourites.json          
├── meal_plan.json    
├── shopping_list.json        
└── requirements.txt             
```

- `recipe.py` – defines the `Recipe` object.
- `mealdb_client.py` – handles all HTTP requests to TheMealDB.
- `planner.py` – contains `MealPlanner`, `ShoppingListGenerator`, measurement parsing, file saving/loading, and `GeminiHelper`.
- `main.py` – the graphical interface; connects everything together.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'tkinter'`
Your Python installation lacks Tkinter. On macOS with Homebrew, run:
```bash
brew install python-tk@3.14   # adjust version if needed
```
or reinstall Python from python.org.

### `ModuleNotFoundError: No module named 'google.genai'`
Install the package:
```bash
pip3 install google-genai
```
If using venv, make sure it’s activated and run `pip install google-genai` inside the venv.

### Gemini returns `404 model not found`
The model name in `planner.py` is outdated. Open the file, find the line with `model="..."`, and change it to a currently supported model (e.g., `"gemini-1.5-flash"`).

### App freezes during search
The app uses background threads for network calls, so the GUI should remain responsive. If it freezes, make sure you’re running the latest version of `main.py` (with threading).

### Data not saved/loaded?
Check that the JSON files (`meal_plan.json`, `shopping_list.json`, `favourites.json`) exist in the same folder as `main.py` after clicking **Save All**. If they are missing, check file permissions.

---

## API Keys

- **TheMealDB** uses the free test key `1` by default. No configuration needed.
- **Gemini** requires a key from Google AI Studio. Set it as `GEMINI_API_KEY`.

---

## License

This project is for educational purposes. You are free to modify and share it.
```
