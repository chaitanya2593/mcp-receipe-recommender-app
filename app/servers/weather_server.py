from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import httpx
from cuisine_rules import recommend

app = FastAPI(title="Weather+Cuisine Tool Server", version="1.0.0")

class WeatherResponse(BaseModel):
    city: str
    latitude: float
    longitude: float
    temperature_c: float
    conditions: str

class RecoRequest(BaseModel):
    cuisine: str
    city: str

class RecoResponse(BaseModel):
    cuisine: str
    city: str
    temperature_c: float
    conditions: str
    recommendations: list[str]

# --- Tool 1: get_weather(city) ---
@app.get("/tools/get_weather", response_model=WeatherResponse)
async def get_weather(city: str = Query(..., min_length=1)):
    # Geocode (Open-Meteo geocoding)
    async with httpx.AsyncClient(timeout=15) as client:
        geo = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )
        geo.raise_for_status()
        gdata = geo.json()
        if not gdata.get("results"):
            raise HTTPException(status_code=404, detail=f"City '{city}' not found")
        r0 = gdata["results"][0]
        lat, lon, resolved = r0["latitude"], r0["longitude"], r0["name"]

        # Current weather
        wx = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": True},
        )
        wx.raise_for_status()
        c = wx.json().get("current_weather", {})
        temp_c = c.get("temperature")
        code = c.get("weathercode")

    # Map WMO weather code to simple description
    WMO = {
        0: "clear", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
        45: "fog", 48: "rime fog", 51: "light drizzle", 53: "drizzle",
        55: "dense drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
        71: "light snow", 73: "snow", 75: "heavy snow", 95: "thunderstorm",
    }
    conditions = WMO.get(code, "unknown")
    return WeatherResponse(
        city=resolved, latitude=lat, longitude=lon,
        temperature_c=float(temp_c), conditions=conditions
    )

# --- Tool 2: recommend_dishes(cuisine, city) ---
@app.post("/tools/recommend", response_model=RecoResponse)
async def recommend_endpoint(payload: RecoRequest):
    wx = await get_weather(payload.city)  # reuse endpoint logic
    dishes = recommend(payload.cuisine, wx.temperature_c, wx.conditions)
    return RecoResponse(
        cuisine=payload.cuisine, city=wx.city,
        temperature_c=wx.temperature_c, conditions=wx.conditions,
        recommendations=dishes
    )

# Local run:
# uvicorn weather_server:app --reload --port 8080

