# main.py
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import os

from mealdb_client import MealDBClient, MealNotFoundError, APIRequestError
from recipe import Recipe
from planner import MealPlanner, ShoppingListGenerator, save_json, load_json, GeminiHelper, validate_servings

class RecipePlannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Meal Planner")
        self.root.geometry("800x700")

        # Backend objects
        self.client = MealDBClient()
        self.planner = MealPlanner()
        self.shopping_list = []
        self.favourites = []          # list of Recipe objects (will be stored as dict)
        self.current_recipe = None    # the recipe currently displayed
        self.result_ids = []   # will hold meal IDs parallel to results list

        # Try to initialise Gemini
        try:
            self.gemini = GeminiHelper()
        except ValueError as e:
            self.gemini = None
            self.gemini_error = str(e)

        # Build GUI
        self.create_widgets()

        # Load saved data
        self.load_all_data()


    # ---------------- GUI creation ----------------
    def create_widgets(self):
        # Search area
        search_frame = ttk.LabelFrame(self.root, text="Search Recipes", padding=10)
        search_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(search_frame, text="Search by:").grid(row=0, column=0, padx=5)
        self.search_type = tk.StringVar(value="name")
        search_combo = ttk.Combobox(search_frame, textvariable=self.search_type, state="readonly",
                                    values=["name", "ingredient", "category"])
        search_combo.grid(row=0, column=1, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.grid(row=0, column=2, padx=5)
        self.search_button = ttk.Button(search_frame, text="Search", command=self.start_search)
        self.search_button.grid(row=0, column=3, padx=5)

        # Search results listbox
        results_frame = ttk.LabelFrame(self.root, text="Results", padding=10)
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.results_list = tk.Listbox(results_frame, height=10)
        self.results_list.pack(fill="both", expand=True)
        self.results_list.bind("<<ListboxSelect>>", self.on_result_select)

        # Recipe display area
        recipe_frame = ttk.LabelFrame(self.root, text="Recipe Details", padding=10)
        recipe_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.recipe_text = scrolledtext.ScrolledText(recipe_frame, wrap=tk.WORD, height=15)
        self.recipe_text.pack(fill="both", expand=True)

        # Buttons for AI and planning
        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(action_frame, text="AI Assistant", command=self.start_gemini).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Add to Favourites", command=self.add_favourite).pack(side=tk.LEFT, padx=5)

        # Plan area
        plan_frame = ttk.LabelFrame(self.root, text="Add to Meal Plan", padding=10)
        plan_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(plan_frame, text="Day:").grid(row=0, column=0)
        self.day_var = tk.StringVar(value="Monday")
        day_combo = ttk.Combobox(plan_frame, textvariable=self.day_var, state="readonly",
                                 values=MealPlanner.VALID_DAYS)
        day_combo.grid(row=0, column=1, padx=5)

        ttk.Label(plan_frame, text="Servings:").grid(row=0, column=2)
        self.servings_entry = ttk.Entry(plan_frame, width=5)
        self.servings_entry.insert(0, "4")
        self.servings_entry.grid(row=0, column=3, padx=5)

        ttk.Button(plan_frame, text="Add to Plan", command=self.add_to_plan).grid(row=0, column=4, padx=5)

        # Bottom buttons
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(bottom_frame, text="Show Meal Plan", command=self.show_meal_plan).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="Generate Shopping List", command=self.generate_shopping_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="Save All", command=self.save_all_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="Load Saved", command=self.load_all_data).pack(side=tk.LEFT, padx=5)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill="x", padx=10, pady=5)

    # ---------------- Threading helper ----------------
    def run_in_background(self, target, *args, callback=None):
        """Run a function in a background thread, then call callback(result) on main thread."""
        def wrapper():
            try:
                result = target(*args)
                if callback:
                    self.root.after(0, callback, result)
            except Exception as e:
                if callback:
                    self.root.after(0, callback, e)  # pass exception
                else:
                    self.root.after(0, self.show_error, str(e))
        threading.Thread(target=wrapper, daemon=True).start()

    # ---------------- Search handling ----------------
    def start_search(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Missing Input", "Please enter a search term.")
            return
        search_type = self.search_type.get()
        self.status_var.set("Searching...")
        self.search_button.config(state=tk.DISABLED)

        # Choose the appropriate client method
        if search_type == "name":
            func = self.client.search_by_name
        elif search_type == "ingredient":
            func = self.client.search_by_ingredient
        else:
            func = self.client.search_by_category

        self.run_in_background(func, query, callback=self.search_complete)

    def search_complete(self, result):
        self.search_button.config(state=tk.NORMAL)
        if isinstance(result, Exception):
            self.status_var.set("Search failed")
            messagebox.showerror("Search Error", str(result))
            return
        # result is list of summaries
        self.results_list.delete(0, tk.END)
        self.result_ids = []
        for meal in result:
            self.results_list.insert(tk.END, f"{meal['name']} (ID: {meal['id']})")
            self.result_ids.append(meal['id'])
        if result:
            self.status_var.set(f"Found {len(result)} results")
        else:
            self.status_var.set("No results")

    def on_result_select(self, event):
        print("Selection event triggered")  # add this line
        selection = self.results_list.curselection()
        if not selection:
            print("No selection")           # add this line
            return
        index = selection[0]
        print(f"Selected index: {index}")   # add this line
        if not hasattr(self, 'result_ids'):
            print("result_ids missing")      # add this line
            return
        meal_id = self.result_ids[index]
        print(f"Meal ID: {meal_id}")         # add this line
        self.status_var.set("Loading recipe...")
        self.run_in_background(self.client.get_recipe, meal_id, callback=self.recipe_loaded)

    def recipe_loaded(self, recipe):
        print("Recipe loaded callback called")
        print("recipe_loaded received:", recipe)
        if isinstance(recipe, Exception):
            messagebox.showerror("Error", str(recipe))
            self.status_var.set("Failed to load recipe")
            return
        self.current_recipe = recipe
        self.display_recipe(recipe)
        self.status_var.set(f"Loaded {recipe.name}")

    def display_recipe(self, recipe):
        """Display recipe details in the text area."""
        print("display_recipe called with:", recipe.name)
        self.recipe_text.delete(1.0, tk.END)
        text = f"{recipe.name}\n"
        text += f"Category: {recipe.category}\n"
        text += f"Cuisine: {recipe.cuisine}\n\n"
        text += "Ingredients:\n"
        for ing in recipe.ingredients:
            text += f"  - {ing['name']}: {ing['measure']}\n"
        text += "\nInstructions:\n"
        text += recipe.instructions
        print("Text to insert (first 200 chars):", text[:200])
        self.recipe_text.insert(tk.END, text)

    # ---------------- Gemini AI ----------------
    def start_gemini(self):
        if not self.current_recipe:
            messagebox.showwarning("No Recipe", "Please select a recipe first.")
            return
        if not self.gemini:
            messagebox.showerror("Gemini Unavailable", self.gemini_error)
            return
        self.status_var.set("Asking Gemini...")
        self.run_in_background(self.gemini.enhance_recipe, self.current_recipe, callback=self.gemini_done)

    def gemini_done(self, result):
        if isinstance(result, Exception):
            self.status_var.set("Gemini failed")
            messagebox.showerror("Gemini Error", str(result))
            return
        # result is dict with keys
        self.status_var.set("Gemini response received")
        text = f"--- AI Enhanced ---\n\nDifficulty: {result['difficulty']}\n\n"
        text += f"Simplified Instructions:\n{result['simplified_instructions']}\n\n"
        text += "Substitutes:\n"
        for sub in result['substitutes']:
            text += f"  - {sub}\n"
        self.recipe_text.insert(tk.END, "\n\n" + text)

    # ---------------- Planning ----------------
    def add_to_plan(self):
        if not self.current_recipe:
            messagebox.showwarning("No Recipe", "Please select a recipe first.")
            return
        day = self.day_var.get()
        servings_text = self.servings_entry.get()
        try:
            servings = validate_servings(servings_text)
        except ValueError as e:
            messagebox.showerror("Invalid Servings", str(e))
            return
        try:
            self.planner.add_meal(day, self.current_recipe, servings)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.status_var.set(f"Added {self.current_recipe.name} to {day} for {servings} people")

    def show_meal_plan(self):
        """Display the current meal plan in a new window."""
        plan_text = self.planner.get_all_meals()
        if not plan_text:
            messagebox.showinfo("Meal Plan", "No meals planned yet.")
            return
        win = tk.Toplevel(self.root)
        win.title("Meal Plan")
        text = scrolledtext.ScrolledText(win, wrap=tk.WORD, width=60, height=20)
        text.pack(fill="both", expand=True, padx=10, pady=10)
        for day, recipe, servings in plan_text:
            text.insert(tk.END, f"{day}: {recipe.name} ({servings} servings)\n")

    def generate_shopping_list(self):
        """Generate and display shopping list."""
        if not self.planner.get_all_meals():
            messagebox.showwarning("No Plan", "Add meals to the plan first.")
            return
        generator = ShoppingListGenerator(self.planner)
        shopping_list = generator.generate()
        self.shopping_list = shopping_list   # store for saving
        # Display in a new window
        win = tk.Toplevel(self.root)
        win.title("Shopping List")
        text = scrolledtext.ScrolledText(win, wrap=tk.WORD, width=60, height=20)
        text.pack(fill="both", expand=True, padx=10, pady=10)
        for item in shopping_list:
            if item['quantity'] is not None:
                text.insert(tk.END, f"{item['name'].capitalize()}: {item['quantity']} {item['unit']}\n")
            else:
                text.insert(tk.END, f"{item['name'].capitalize()}: {item['original']} (unparsable)\n")
        self.status_var.set("Shopping list generated")

    # ---------------- Favourites ----------------
    def add_favourite(self):
        if not self.current_recipe:
            messagebox.showwarning("No Recipe", "Select a recipe first.")
            return
        # Check if already in favourites
        for fav in self.favourites:
            if fav['meal_id'] == self.current_recipe.meal_id:
                messagebox.showinfo("Already Favourite", "This recipe is already in favourites.")
                return
        self.favourites.append({
            "meal_id": self.current_recipe.meal_id,
            "name": self.current_recipe.name,
            "category": self.current_recipe.category,
            "cuisine": self.current_recipe.cuisine,
            "ingredients": self.current_recipe.ingredients,
            "instructions": self.current_recipe.instructions,
            "image_url": self.current_recipe.image_url
        })
        self.status_var.set(f"Added {self.current_recipe.name} to favourites")

    # ---------------- Save/Load ----------------
    def save_all_data(self):
        # Save plan (we need to convert Recipe objects to dictionaries)
        plan_data = {}
        for day, meals in self.planner.plan.items():
            plan_data[day] = []
            for entry in meals:
                recipe = entry['recipe']
                plan_data[day].append({
                    "recipe": {
                        "meal_id": recipe.meal_id,
                        "name": recipe.name,
                        "category": recipe.category,
                        "cuisine": recipe.cuisine,
                        "ingredients": recipe.ingredients,
                        "instructions": recipe.instructions,
                        "image_url": recipe.image_url
                    },
                    "servings": entry['servings']
                })
        try:
            save_json(plan_data, "meal_plan.json")
            save_json(self.shopping_list, "shopping_list.json")
            save_json(self.favourites, "favourites.json")
            self.status_var.set("All data saved")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def load_all_data(self):
        # Load favourites
        favs = load_json("favourites.json")
        if favs is not None:
            self.favourites = favs
        # Load shopping list
        shop = load_json("shopping_list.json")
        if shop is not None:
            self.shopping_list = shop
        # Load meal plan
        plan = load_json("meal_plan.json")
        if plan is not None:
            self.planner = MealPlanner()
            for day, meals in plan.items():
                for entry in meals:
                    recipe_data = entry["recipe"]
                    recipe = Recipe(
                        meal_id=recipe_data["meal_id"],
                        name=recipe_data["name"],
                        category=recipe_data["category"],
                        cuisine=recipe_data["cuisine"],
                        ingredients=recipe_data["ingredients"],
                        instructions=recipe_data["instructions"],
                        image_url=recipe_data["image_url"]
                    )
                    self.planner.add_meal(day, recipe, entry["servings"])
        self.status_var.set("Data loaded")

    # ---------------- Error helper ----------------
    def show_error(self, message):
        messagebox.showerror("Error", message)


if __name__ == "__main__":
    root = tk.Tk()
    app = RecipePlannerApp(root)
    root.mainloop()