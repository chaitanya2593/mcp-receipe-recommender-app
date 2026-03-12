# MCP with Stock Prediction and Recipe Recommender

## Use Case Introduction
The goal of this project is to develop a Streamlit application that predicts stock prices using historical data and provides recipe recommendations using TheMealDB and OpenFoodFacts APIs. The application leverages machine learning and MCP (Model-Compute-Predict) tools for both stock and recipe use cases.

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

## References:
- https://streamlit.io/
- https://www.themealdb.com/api.php
- https://world.openfoodfacts.org/
- https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/
- https://makefiletutorial.com/#makefile-cookbook
- https://scikit-learn.org/stable/modules/svm.html