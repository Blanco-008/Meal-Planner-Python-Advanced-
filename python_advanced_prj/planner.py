# planner.py

import re
import json
import os

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# Measurement helpers

def parse_measure(measure_str):
    """
    Parse a measurement string like "2 cups", "1/2 tbsp", "1 1/2 cups".
    Returns a tuple (quantity_float, unit_string) or (None, original_string) if unparsable.
    """
    measure_str = measure_str.strip()
    if not measure_str:
        return None, ""

    # Pattern to capture:
    # - optional whole number and/or fraction (e.g. "1 1/2", "1/2", "2")
    # - optional unit (letters, possibly with spaces like "tbsp")
    pattern = r"^\s*(\d+(?:\s+\d+/\d+)?|\d+/\d+)?\s*([a-zA-Z].*)?$"
    match = re.match(pattern, measure_str)
    if not match:
        return None, measure_str

    quantity_part = match.group(1)
    unit_part = match.group(2).strip() if match.group(2) else ""

    if not quantity_part:
        # No quantity found – perhaps just a unit or descriptive text
        return None, measure_str

    # Convert the quantity part to a float.
    try:
        if '/' in quantity_part:
            # Could be "1 1/2" or "1/2"
            parts = quantity_part.split()
            if len(parts) == 2:  # whole number + fraction
                whole = float(parts[0])
                fraction = parts[1]
            else:
                whole = 0.0
                fraction = parts[0]
            num, den = fraction.split('/')
            quantity = whole + float(num) / float(den)
        else:
            quantity = float(quantity_part)
    except (ValueError, ZeroDivisionError):
        return None, measure_str

    return quantity, unit_part


def clean_ingredient_name(name):
    """
    Clean an ingredient name: remove extra spaces, punctuation, and lowercase.
    Used to combine duplicate ingredients more reliably.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.lower()


def validate_servings(servings_text):
    """
    Validate a servings input string. Returns an integer if valid, else raises ValueError.
    """
    if not servings_text.strip():
        raise ValueError("Servings cannot be empty.")
    if not re.fullmatch(r"\d+", servings_text.strip()):
        raise ValueError("Servings must be a positive whole number.")
    servings = int(servings_text)
    if servings <= 0:
        raise ValueError("Servings must be greater than zero.")
    return servings


# ----------------------------------------------------------------------
# Meal Planner
# ----------------------------------------------------------------------

class MealPlanner:
    """
    Stores a weekly meal plan: day -> list of (recipe, servings)
    """
    VALID_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self):
        self.plan = {day: [] for day in self.VALID_DAYS}

    def add_meal(self, day, recipe, servings):
        """Add a meal (Recipe object) and servings to the given day."""
        if day not in self.VALID_DAYS:
            raise ValueError(f"Invalid day '{day}'. Use one of {self.VALID_DAYS}.")
        if recipe is None:
            raise ValueError("Recipe cannot be None.")
        servings = validate_servings(str(servings))
        self.plan[day].append({"recipe": recipe, "servings": servings})

    def remove_meal(self, day, index):
        """Remove a meal by its index on a given day."""
        if day not in self.VALID_DAYS:
            raise ValueError(f"Invalid day '{day}'.")
        if 0 <= index < len(self.plan[day]):
            del self.plan[day][index]
        else:
            raise IndexError("Meal index out of range.")

    def get_meals_for_day(self, day):
        """Return a list of meals for a day."""
        if day not in self.VALID_DAYS:
            raise ValueError(f"Invalid day '{day}'.")
        return self.plan[day]

    def get_all_meals(self):
        """Return all planned meals as a flat list of (day, recipe, servings)."""
        all_meals = []
        for day, meals in self.plan.items():
            for entry in meals:
                all_meals.append((day, entry["recipe"], entry["servings"]))
        return all_meals

    def clear(self):
        """Clear the whole plan."""
        self.plan = {day: [] for day in self.VALID_DAYS}


# ----------------------------------------------------------------------
# Shopping List Generator
# ----------------------------------------------------------------------

class ShoppingListGenerator:
    """
    Generates a combined shopping list from a meal plan.
    """
    def __init__(self, meal_planner):
        self.meal_planner = meal_planner

    def generate(self):
        """
        Generate a shopping list by scaling and combining ingredients.
        Returns a list of dicts: {"name": cleaned_name, "quantity": total_qty, "unit": unit}
        or {"name": cleaned_name, "original": original_measure} for unparsable.
        """
        combined = {}   # key: (cleaned_name, unit) or (cleaned_name, "unparsable")

        for day, recipe, servings in self.meal_planner.get_all_meals():
            base_servings = 4  # TheMealDB recipes generally serve 4
            scale_factor = servings / base_servings

            for ing in recipe.ingredients:
                name = ing.get("name", "")
                measure = ing.get("measure", "")
                if not name:
                    continue
                cleaned_name = clean_ingredient_name(name)
                quantity, unit = parse_measure(measure)

                if quantity is None:
                    # Unparsable measurement – keep original text
                    key = (cleaned_name, "unparsable")
                    if key not in combined:
                        combined[key] = {
                            "name": cleaned_name,
                            "quantity": None,
                            "unit": None,
                            "original": measure,
                            "count": 1
                        }
                    else:
                        combined[key]["count"] += 1
                    continue

                scaled_qty = quantity * scale_factor
                unit_key = unit.lower() if unit else ""
                key = (cleaned_name, unit_key)

                if key in combined:
                    combined[key]["quantity"] += scaled_qty
                else:
                    combined[key] = {
                        "name": cleaned_name,
                        "quantity": scaled_qty,
                        "unit": unit,
                        "original": "",
                        "count": 1
                    }

        # Build final list
        shopping_list = []
        for key, data in combined.items():
            if data["quantity"] is None:
                shopping_list.append({
                    "name": data["name"],
                    "quantity": None,
                    "unit": None,
                    "original": data["original"],
                    "count": data["count"]
                })
            else:
                qty = data["quantity"]
                if qty.is_integer():
                    qty_str = str(int(qty))
                else:
                    qty_str = f"{qty:.2f}".rstrip('0').rstrip('.')
                shopping_list.append({
                    "name": data["name"],
                    "quantity": qty_str,
                    "unit": data["unit"],
                    "original": "",
                    "count": data["count"]
                })
        return shopping_list


# ----------------------------------------------------------------------
# JSON file handling
# ----------------------------------------------------------------------

def save_json(data, filename):
    """Save data to a JSON file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except OSError as e:
        raise OSError(f"Could not save file {filename}: {e}")


def load_json(filename):
    """Load data from a JSON file. Returns None if file doesn't exist or is invalid."""
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ----------------------------------------------------------------------
# Gemini AI Helper
# ----------------------------------------------------------------------

class GeminiHelper:
    """
    Uses Google Gemini to enhance a recipe with simplified instructions,
    difficulty, and ingredient substitutes.
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key is missing. Set GEMINI_API_KEY or GOOGLE_API_KEY in your environment."
            )
        if genai is None:
            raise ValueError(
                "Gemini SDK is missing. Install it with: pip install google-genai"
            )
        self.client = genai.Client(api_key=self.api_key)

    def enhance_recipe(self, recipe):
        """
        Send recipe info to Gemini and ask for JSON response with three fields:
        simplified_instructions, difficulty, substitutes.
        Returns a dict.
        """
        prompt = f"""
You are a helpful cooking assistant. Given the following recipe, please provide:
1. Simplified cooking instructions (easy to follow steps).
2. A difficulty level: Easy, Medium, or Hard.
3. Cheaper or locally available ingredient substitutes, especially Nigerian/local alternatives if possible.

Recipe:
Name: {recipe.name}
Cuisine: {recipe.cuisine}
Category: {recipe.category}
Ingredients: {recipe.ingredients}
Original Instructions: {recipe.instructions}

Return your answer as a JSON object with exactly these keys:
"simplified_instructions" (string),
"difficulty" (string, one of Easy/Medium/Hard),
"substitutes" (list of strings, each describing a substitute).

Do not include any extra text.
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            response_text = getattr(response, "text", None)
            if not response_text:
                raise ValueError("Gemini returned no text in the response.")

            result = json.loads(response_text)
            required = ["simplified_instructions", "difficulty", "substitutes"]
            if not all(k in result for k in required):
                raise ValueError("Gemini response missing required fields.")
            return result
        except Exception as e:
            raise RuntimeError(f"Gemini failed: {e}")