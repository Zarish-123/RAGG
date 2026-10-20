
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather MCP Server")

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


async def geocode_city(city: str) -> dict:
    """Convert a city name into geographic coordinates."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            GEOCODING_URL,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])

    if not results:
        return {"error": f"Location not found: {city}"}

    place = results[0]

    return {
        "name": place["name"],
        "country": place.get("country", "Unknown"),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "timezone": place.get("timezone", "auto"),
    }


def describe_weather(code: int) -> str:
    """Translate a WMO weather code into a readable description."""
    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snowfall",
        73: "Moderate snowfall",
        75: "Heavy snowfall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }

    return descriptions.get(code, f"Unknown weather code: {code}")


@mcp.tool()
async def search_location(city: str) -> dict:
    """Find a city and return its country, coordinates, and timezone."""
    return await geocode_city(city)


@mcp.tool()
async def get_current_weather(city: str) -> dict:
    """Get current temperature, feels-like temperature, humidity,
    wind speed, precipitation, and weather conditions for a city."""
    try:
        location = await geocode_city(city)

        if "error" in location:
            return location

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                WEATHER_URL,
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "current": (
                        "temperature_2m,relative_humidity_2m,"
                        "apparent_temperature,is_day,precipitation,"
                        "weather_code,wind_speed_10m"
                    ),
                    "timezone": location["timezone"],
                },
            )
            response.raise_for_status()
            data = response.json()

        current = data.get("current", {})
        code = current.get("weather_code")

        return {
            "city": location["name"],
            "country": location["country"],
            "time": current.get("time"),
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "precipitation_mm": current.get("precipitation"),
            "conditions": (
                describe_weather(code) if code is not None else "Unknown"
            ),
            "is_day": current.get("is_day"),
        }

    except httpx.HTTPError as exc:
        return {"error": f"Weather API request failed: {exc}"}


@mcp.tool()
async def get_weather_forecast(
    city: str,
    days: int = 3,
) -> dict:
    """Get a daily weather forecast. Choose between 1 and 7 days."""
    if not 1 <= days <= 7:
        return {"error": "days must be between 1 and 7"}

    try:
        location = await geocode_city(city)

        if "error" in location:
            return location

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                WEATHER_URL,
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "daily": (
                        "weather_code,temperature_2m_max,"
                        "temperature_2m_min,precipitation_probability_max"
                    ),
                    "forecast_days": days,
                    "timezone": location["timezone"],
                },
            )
            response.raise_for_status()
            data = response.json()

        daily = data.get("daily", {})
        forecast = []

        dates = daily.get("time", [])

        for i, date in enumerate(dates):
            code = daily["weather_code"][i]

            forecast.append({
                "date": date,
                "conditions": describe_weather(code),
                "max_temperature_c": daily["temperature_2m_max"][i],
                "min_temperature_c": daily["temperature_2m_min"][i],
                "precipitation_probability_percent": (
                    daily["precipitation_probability_max"][i]
                ),
            })

        return {
            "city": location["name"],
            "country": location["country"],
            "forecast": forecast,
        }

    except httpx.HTTPError as exc:
        return {"error": f"Forecast API request failed: {exc}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
