# Weather-Aware Cuisine Recommender:
## Use Case Introduction
The goal of this project is to build a weather-aware cuisine recommender system that provides personalized dish and restaurant recommendations based on the current weather conditions in a given city. The system will leverage real-time weather data, user input for cuisine preferences, and a knowledge base of dishes and restaurants to generate tailored recommendations.

### Local Setup (with uv)

1. Create and activate a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
2. Install [uv](https://github.com/astral-sh/uv) if not already installed:
    ```bash
    pip install uv
    ```
3. Sync dependencies using uv and `pyproject.toml`:
    ```bash
    uv sync
    ```

### Streamlit deployment

1. Run the Streamlit application:
    ```bash
    streamlit run streamlit_app.py
    ```
2. Open the browser and go to `http://localhost:8501/` to see the application.
3. The application is now running locally.

## MCP RecipeRecommender Tools (TheMealDB + OpenFoodFacts)

### Usage
- The MCP RecipeRecommender server is located at `app/servers/mcp-recipes/server.py`.
- Tools implemented:
    - `get_recipes(ingredients)` → TheMealDB
    - `where_to_order(dish)` → mock delivery options
    - `get_ingredients_shopping_list(dish)` → TheMealDB + OpenFoodFacts
    - `compare_options(dish)` → cost/time/healthiness comparison

### Example Copilot prompts
- Use the MCP RecipeRecommender tools: find recipes using chicken, rice and show me top 3.
- Call get_ingredients_shopping_list for Chicken Biryani and summarize what I need to buy.
- Run compare_options for Chicken Biryani and tell me whether I should cook or order tonight.
- Use where_to_order("Pad Thai") and sort by ETA.

## Weather-Aware Cuisine Recommender: Input & Output Example

### Input
- User types a natural language request in the Streamlit chat, e.g.:
  > recommend italian in Mumbai

### Output
- The app extracts the cuisine and city, fetches real weather data, and uses GPT to recommend dishes and restaurants. The output is formatted as:

```
Extracted cuisine: Italian, city: Mumbai

Cuisine: Italian
City: Mumbai
Weather: 26.5°C, Mainly clear (Humidity: 64%)

Weather-matched dish recommendations:
- Insalata Caprese - Cecconi's Mumbai & CinCin BKC & Celini Grand Hyatt
- Linguine ai Frutti di Mare - Trattoria Taj Colaba & Romano's JW Marriott Juhu & Gustoso Kemps Corner
- Margherita Pizza (Wood-Fired) - Pizza By The Bay Marine Drive & Olive Bar & Kitchen Khar & Cecconi's Mumbai
```

- The recommendations are tailored to the weather and city, and include top local restaurants for each dish.

## Weather-Aware Cuisine Recommender: How It Works

- The current approach takes only **city** and **cuisine** as input from the user (e.g., "recommend italian in Mumbai").
- The system extracts these two fields, fetches real weather data for the city, and uses them to generate recommendations.
- While the main example is weather-matched dish recommendations, this architecture can be extended to any city/cuisine-based recommendation logic (e.g., events, local specialties, or other city-aware suggestions).
- The weather-aware recommender is just one use case; the input/output format is general and can support other city/cuisine-based features in the future.

---

## References:
- https://streamlit.io/
- https://www.themealdb.com/api.php
- https://world.openfoodfacts.org/
- https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/
- https://makefiletutorial.com/#makefile-cookbook
- https://scikit-learn.org/stable/modules/svm.html
- https://open-meteo.com/en/docs