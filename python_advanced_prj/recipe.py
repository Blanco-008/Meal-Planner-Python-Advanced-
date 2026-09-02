class Recipe:
    """
    A clean representation of a recipe.
    """
    def __init__(self, meal_id, name, category, cuisine, ingredients, instructions, image_url):
        self.meal_id = meal_id          # e.g. "52772"
        self.name = name                # "Chicken Curry"
        self.category = category        # "Chicken"
        self.cuisine = cuisine          # "Indian"
        self.ingredients = ingredients  # list of dicts: {"name": "Rice", "measure": "2 cups"}
        self.instructions = instructions
        self.image_url = image_url

    @classmethod
    def from_api(cls, data):
        """
        Convert TheMealDB's raw JSON (one meal) into a Recipe object.
        """
        meal_id = data.get("idMeal")
        name = data.get("strMeal")
        category = data.get("strCategory")
        cuisine = data.get("strArea")
        image_url = data.get("strMealThumb")
        instructions = data.get("strInstructions", "")

        # TheMealDB stores up to 20 ingredients and 20 measures
        ingredients = []
        for i in range(1, 21):
            ingredient = data.get(f"strIngredient{i}")
            measure = data.get(f"strMeasure{i}")
            # Only add if the ingredient is not empty/None
            if ingredient and ingredient.strip():
                ingredients.append({
                    "name": ingredient.strip(),
                    "measure": measure.strip() if measure else ""
                })

        return cls(meal_id, name, category, cuisine, ingredients, instructions, image_url)

    def __str__(self):
        return f"{self.name} ({self.cuisine})"