# mealdb_client.py
import requests
from recipe import Recipe

class MealNotFoundError(Exception):
    """Raised when no meal is found for the given query."""
    pass

class APIRequestError(Exception):
    """Raised when the API request fails (network, timeout, etc.)."""
    pass

class MealDBClient:
    BASE_URL = "https://www.themealdb.com/api/json/v1/1"

    def __init__(self, timeout=10):
        self.timeout = timeout

    def _get(self, endpoint, params):
        """Helper to perform GET request and handle common errors."""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()  # raises HTTPError for 4xx/5xx
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIRequestError(f"Could not reach TheMealDB: {e}")

    def search_by_name(self, meal_name):
        """
        Search for a meal by name. Returns a list of recipe summaries.
        Each summary is a dict with 'id', 'name', 'thumb'.
        """
        data = self._get("search.php", {"s": meal_name})
        meals = data.get("meals")
        if not meals:
            raise MealNotFoundError(f"No meals found for name '{meal_name}'.")
        return [{"id": m["idMeal"], "name": m["strMeal"], "thumb": m["strMealThumb"]} for m in meals]

    def search_by_ingredient(self, ingredient):
        """
        Search by main ingredient. Returns a list of meal summaries.
        """
        data = self._get("filter.php", {"i": ingredient})
        meals = data.get("meals")
        if not meals:
            raise MealNotFoundError(f"No meals found with ingredient '{ingredient}'.")
        return [{"id": m["idMeal"], "name": m["strMeal"], "thumb": m["strMealThumb"]} for m in meals]

    def search_by_category(self, category):
        """
        Search by category. Returns a list of meal summaries.
        """
        data = self._get("filter.php", {"c": category})
        meals = data.get("meals")
        if not meals:
            raise MealNotFoundError(f"No meals found in category '{category}'.")
        return [{"id": m["idMeal"], "name": m["strMeal"], "thumb": m["strMealThumb"]} for m in meals]

    def get_recipe(self, meal_id):
        """
        Retrieve a full recipe by its ID.
        Returns a Recipe object or raises MealNotFoundError.
        """
        data = self._get("lookup.php", {"i": meal_id})
        meals = data.get("meals")
        if not meals:
            raise MealNotFoundError(f"Meal ID '{meal_id}' not found.")
        # The API returns a list; we take the first (only) meal.
        return Recipe.from_api(meals[0])