from __future__ import annotations
import math
import re
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"
OFF_SEARCH = "https://world.openfoodfacts.org/cgi/search.pl"
mcp = FastMCP("RecipeRecommender")

# ---------- Pydantic models ----------
class Recipe(BaseModel):
    dish: str
    category: Optional[str] = None
    area: Optional[str] = None
    thumbnail: Optional[str] = None
    instructions: Optional[str] = None
    ingredients: List[Dict[str, str]] = Field(default_factory=list)
    source_url: Optional[str] = None

class OrderOption(BaseModel):
    provider: str
    price_eur: float
    eta_minutes: int
    rating: float
    link: Optional[str] = None

class ShoppingItem(BaseModel):
    ingredient: str
    measure: Optional[str] = None
    brand_or_best_match: Optional[str] = None
    price_est_eur: Optional[float] = None
    dietary_flags: List[str] = Field(default_factory=list)
    buy_url: Optional[str] = None

class Comparison(BaseModel):
    dish: str
    order_cost_eur: float
    order_eta_minutes: int
    cook_cost_eur: float
    cook_time_minutes: int
    healthiness_score: float
    recommendation: str

# ---------- Utilities ----------
def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _extract_ingredients(meal: Dict[str, Any]) -> List[Dict[str, str]]:
    items = []
    for i in range(1, 21):
        ing = _norm(meal.get(f"strIngredient{i}"))
        meas = _norm(meal.get(f"strMeasure{i}"))
        if ing:
            items.append({"ingredient": ing, "measure": meas or None})
    return items

async def _themealdb_search_by_ingredients(client: httpx.AsyncClient, ingredients: List[str]) -> List[Recipe]:
    ing_param = ",".join(sorted(set([i.strip() for i in ingredients if i.strip()])))
    if not ing_param:
        return []
    r = await client.get(f"{MEALDB_BASE}/filter.php", params={"i": ing_param}, timeout=30)
    r.raise_for_status()
    data = r.json()
    meals = data.get("meals") or []
    recipes: List[Recipe] = []
    for m in meals[:8]:
        meal_id = m.get("idMeal")
        if not meal_id:
            continue
        det = await client.get(f"{MEALDB_BASE}/lookup.php", params={"i": meal_id}, timeout=30)
        det.raise_for_status()
        detj = det.json()
        full = (detj.get("meals") or [None])[0]
        if not full:
            continue
        recipes.append(
            Recipe(
                dish=_norm(full.get("strMeal")),
                category=_norm(full.get("strCategory")),
                area=_norm(full.get("strArea")),
                thumbnail=_norm(full.get("strMealThumb")),
                instructions=_norm(full.get("strInstructions")),
                ingredients=_extract_ingredients(full),
                source_url=_norm(full.get("strSource") or full.get("strYoutube")),
            )
        )
    return recipes

async def _openfoodfacts_best_match(client: httpx.AsyncClient, ingredient: str) -> Dict[str, Any]:
    params = {
        "search_terms": ingredient,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 5
    }
    r = await client.get(OFF_SEARCH, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    products = data.get("products") or []
    best = None
    best_score = -1
    for p in products:
        grade = (p.get("nutrition_grades") or "c").lower()
        grade_score = {"a": 3, "b": 2, "c": 1, "d": 0, "e": -1}.get(grade, 0)
        labels = (p.get("labels_tags") or [])
        completeness = int(p.get("complete", 0))
        score = grade_score * 2 + completeness + (1 if labels else 0)
        if score > best_score:
            best, best_score = p, score
    return best or {}

def _estimate_price(ingredient: str, measure: Optional[str]) -> float:
    base = 1.5
    ing = ingredient.lower()
    if any(k in ing for k in ["chicken", "beef", "prawn", "fish"]): base = 4.0
    if any(k in ing for k in ["rice", "pasta", "flour"]): base = 1.0
    if any(k in ing for k in ["spice", "salt", "pepper"]): base = 0.5
    qty_boost = 1.0
    if measure:
        m = measure.lower()
        if re.search(r"\bkg|\b500g|\b400g|\b1 lb", m): qty_boost = 2.0
        elif re.search(r"\bml|\b200ml|\bcup|\btbsp|\btsp", m): qty_boost = 1.1
    return round(base * qty_boost, 2)

def _healthiness_from_off(product: Dict[str, Any]) -> List[str]:
    flags = []
    grade = (product.get("nutrition_grades") or "").upper()
    if grade:
        flags.append(f"nutrition_grade_{grade}")
    if product.get("labels_tags"):
        labels = [t.split(":")[-1] for t in product["labels_tags"]]
        flags.extend(labels[:3])
    return flags

# ---------- MCP Tools ----------
@mcp.tool()
async def get_recipes(ingredients: List[str]) -> List[Recipe]:
    """
    Given a list of ingredients, return candidate recipes (TheMealDB).
    """
    async with httpx.AsyncClient() as client:
        return await _themealdb_search_by_ingredients(client, ingredients)

@mcp.tool()
async def where_to_order(dish: str) -> List[OrderOption]:
    """
    Mock delivery options (swap for real providers later).
    """
    name = dish.strip() or "Dish"
    options = [
        OrderOption(provider="Lieferando", price_eur=13.9, eta_minutes=30, rating=4.4, link=f"https://www.lieferando.de/"),
        OrderOption(provider="DoorDash",  price_eur=14.5, eta_minutes=28, rating=4.2, link=f"https://www.doordash.com/"),
        OrderOption(provider="UberEats",  price_eur=15.9, eta_minutes=22, rating=4.1, link=f"https://www.ubereats.com/"),
    ]
    return options

@mcp.tool()
async def get_ingredients_shopping_list(dish: str) -> List[ShoppingItem]:
    """
    Build a shopping list for a dish: for each ingredient, fetch best match from OpenFoodFacts,
    estimate price, and include dietary flags + a generic buy URL.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{MEALDB_BASE}/search.php", params={"s": dish}, timeout=30)
        r.raise_for_status()
        meals = (r.json().get("meals") or [])
        if not meals:
            return []
        ingredients = _extract_ingredients(meals[0])
        items: List[ShoppingItem] = []
        for ing in ingredients:
            prod = await _openfoodfacts_best_match(client, ing["ingredient"])
            flags = _healthiness_from_off(prod)
            price = _estimate_price(ing["ingredient"], ing.get("measure"))
            buy_url = prod.get("url") or prod.get("link") or "https://www.google.com/search?q=" + httpx.QueryParams({"q": ing["ingredient"]}).get("q")
            items.append(ShoppingItem(
                ingredient=ing["ingredient"],
                measure=ing.get("measure"),
                brand_or_best_match=prod.get("product_name"),
                price_est_eur=price,
                dietary_flags=flags,
                buy_url=buy_url
            ))
        return items

@mcp.tool()
async def compare_options(dish: str) -> Comparison:
    """
    Compare 'order vs cook' for a dish: cost, time, simple healthiness proxy, and recommendation.
    """
    orders = await where_to_order(dish)
    order_cost = min(o.price_eur for o in orders) if orders else 15.0
    order_eta = min(o.eta_minutes for o in orders) if orders else 30
    shopping = await get_ingredients_shopping_list(dish)
    cook_cost = round(sum((i.price_est_eur or 0.0) for i in shopping), 2) if shopping else 8.0
    cook_time = 45
    flag_count = sum(len(i.dietary_flags) for i in shopping)
    healthiness = round(min(10.0, 4.0 + math.log1p(flag_count)), 1)
    if order_eta <= 25 and order_cost <= cook_cost * 1.6:
        reco = "Order it if you value speed; cost premium is reasonable."
    elif cook_cost <= order_cost * 0.7:
        reco = "Cook it—cheaper and likely healthier."
    else:
        reco = "Either works; choose based on time vs. cost."
    return Comparison(
        dish=dish,
        order_cost_eur=order_cost,
        order_eta_minutes=order_eta,
        cook_cost_eur=cook_cost,
        cook_time_minutes=cook_time,
        healthiness_score=healthiness,
        recommendation=reco,
    )

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()

