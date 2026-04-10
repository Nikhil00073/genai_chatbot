# WAY 2 — using @tool with multiple parameters
# Shows how to pass more than one input to a tool

from langchain_core.tools import tool
import httpx


@tool
def get_weather(city: str) -> str:
    """
    Get the current weather for a given city.
    Use this when the user asks about weather, temperature,
    or climate in any city or location.
    Input should be a city name like 'Delhi' or 'Mumbai'.
    """
    try:
        # using open-meteo — free, no API key needed
        # first get coordinates for the city
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"

        with httpx.Client(timeout=10.0) as client:
            geo_response = client.get(geo_url)
            geo_data = geo_response.json()

        if not geo_data.get("results"):
            return f"Could not find location for city: {city}"

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]

        # now get the weather
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current_weather=true"
        )

        with httpx.Client(timeout=10.0) as client:
            weather_response = client.get(weather_url)
            weather_data = weather_response.json()

        current = weather_data.get("current_weather", {})
        temp    = current.get("temperature", "N/A")
        wind    = current.get("windspeed", "N/A")

        return (
            f"Weather in {city}:\n"
            f"Temperature: {temp}°C\n"
            f"Wind speed: {wind} km/h"
        )

    except Exception as e:
        return f"Could not fetch weather for {city}: {str(e)}"