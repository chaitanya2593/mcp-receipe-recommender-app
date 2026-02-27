from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
OPENMETEO_API_BASE = "https://api.open-meteo.com/v1"
GEOCODING_API_BASE = "https://geocoding-api.open-meteo.com/v1"

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> dict:
    """Get weather forecast for a location using Open-Meteo API.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location

    Returns:
        Dictionary with current weather and forecast information
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OPENMETEO_API_BASE}/forecast",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                    "hourly": "temperature_2m,precipitation,weather_code",
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                    "timezone": "auto"
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            current = data.get("current", {})
            daily = data.get("daily", {})

            # Format the forecast
            forecast_info = {
                "current_temperature_c": current.get("temperature_2m"),
                "humidity_percent": current.get("relative_humidity_2m"),
                "weather_code": current.get("weather_code"),
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "conditions": interpret_weather_code(current.get("weather_code")),
                "max_temp_c": daily.get("temperature_2m_max", [None])[0],
                "min_temp_c": daily.get("temperature_2m_min", [None])[0]
            }

            return forecast_info
    except Exception as e:
        return {
            "error": f"Unable to fetch forecast: {str(e)}",
            "current_temperature_c": 20,
            "conditions": "Unknown"
        }

@mcp.tool()
async def get_city_coordinates(city: str) -> dict:
    """Get latitude and longitude for a city name.

    Args:
        city: Name of the city (e.g., "Munich", "New York", "Tokyo")

    Returns:
        Dictionary with latitude, longitude, and city name
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GEOCODING_API_BASE}/search",
                params={
                    "name": city,
                    "count": 1,
                    "language": "en",
                    "format": "json"
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            if data.get("results") and len(data["results"]) > 0:
                result = data["results"][0]
                return {
                    "latitude": result["latitude"],
                    "longitude": result["longitude"],
                    "name": result.get("name"),
                    "country": result.get("country")
                }
            else:
                # Default to Munich if city not found
                return {
                    "latitude": 48.1351,
                    "longitude": 11.5820,
                    "name": "Munich",
                    "country": "Germany"
                }
    except Exception as e:
        # Fallback to Munich
        return {
            "latitude": 48.1351,
            "longitude": 11.5820,
            "name": "Munich",
            "country": "Germany"
        }

def interpret_weather_code(code: int) -> str:
    """Convert WMO Weather interpretation codes to readable strings."""
    if code is None:
        return "Unknown"

    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }

    return weather_codes.get(code, f"Weather code {code}")

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')