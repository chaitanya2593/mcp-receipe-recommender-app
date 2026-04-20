"""Tests for app/servers/weather_server.py — pure logic, no network calls."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.servers.weather_server import interpret_weather_code, get_city_coordinates, get_forecast


# ---------------------------------------------------------------------------
# interpret_weather_code
# ---------------------------------------------------------------------------

class TestInterpretWeatherCode:
    def test_known_codes(self):
        assert interpret_weather_code(0) == "Clear sky"
        assert interpret_weather_code(3) == "Overcast"
        assert interpret_weather_code(61) == "Slight rain"
        assert interpret_weather_code(95) == "Thunderstorm"

    def test_none_returns_unknown(self):
        assert interpret_weather_code(None) == "Unknown"

    def test_unknown_code_returns_fallback(self):
        assert interpret_weather_code(999) == "Weather code 999"

    def test_all_defined_codes_return_strings(self):
        defined = [0, 1, 2, 3, 45, 48, 51, 53, 55, 61, 63, 65,
                   71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99]
        for code in defined:
            result = interpret_weather_code(code)
            assert isinstance(result, str) and result != f"Weather code {code}"


# ---------------------------------------------------------------------------
# get_city_coordinates — mock httpx so no real network calls happen
# ---------------------------------------------------------------------------

class TestGetCityCoordinates:
    @pytest.mark.asyncio
    async def test_returns_coordinates_for_known_city(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [{"latitude": 48.1351, "longitude": 11.5820, "name": "Munich", "country": "Germany"}]
        }

        with patch("app.servers.weather_server.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_city_coordinates("Munich")

        assert result["latitude"] == 48.1351
        assert result["longitude"] == 11.5820
        assert result["name"] == "Munich"

    @pytest.mark.asyncio
    async def test_fallback_when_no_results(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": []}

        with patch("app.servers.weather_server.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_city_coordinates("NonExistentCity")

        # Should fall back to Munich defaults
        assert result["name"] == "Munich"
        assert "latitude" in result

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self):
        with patch("app.servers.weather_server.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("network error"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_city_coordinates("Anywhere")

        assert result["name"] == "Munich"


# ---------------------------------------------------------------------------
# get_forecast — mock httpx
# ---------------------------------------------------------------------------

class TestGetForecast:
    @pytest.mark.asyncio
    async def test_returns_forecast_fields(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "current": {
                "temperature_2m": 15.0,
                "relative_humidity_2m": 60,
                "weather_code": 2,
                "wind_speed_10m": 12.5,
            },
            "daily": {
                "temperature_2m_max": [18.0],
                "temperature_2m_min": [10.0],
                "weather_code": [2],
            }
        }

        with patch("app.servers.weather_server.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_forecast(48.1351, 11.5820)

        assert result["current_temperature_c"] == 15.0
        assert result["conditions"] == "Partly cloudy"
        assert result["humidity_percent"] == 60
        assert result["wind_speed_kmh"] == 12.5

    @pytest.mark.asyncio
    async def test_returns_error_dict_on_exception(self):
        with patch("app.servers.weather_server.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("timeout"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_forecast(0.0, 0.0)

        assert "error" in result
        assert result["current_temperature_c"] == 20  # fallback value
