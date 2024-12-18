#weather_service.py
import os
import requests
from datetime import datetime, timedelta

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv('WEATHER_API_KEY')
        if not self.api_key:
            raise ValueError("OpenWeather API key not found in environment variables")

    def get_weather(self, city, forecast_days=0):
        """Get current weather or forecast for a specific city"""
        try:
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={self.api_key}"
            geo_response = requests.get(geo_url)
            geo_data = geo_response.json()
            
            if not geo_data:
                return f"Could not find location: {city}"
                
            lat = geo_data[0]['lat']
            lon = geo_data[0]['lon']
            
            if forecast_days == 0:
                return self._get_current_weather(lat, lon)
            else:
                return self._get_forecast(lat, lon, forecast_days)
                
        except Exception as e:
            return f"Error getting weather data: {str(e)}"

    def _get_current_weather(self, lat, lon):
        """Get current weather for given coordinates"""
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
        response = requests.get(weather_url)
        data = response.json()
        
        return {
            'temperature': data['main']['temp'],
            'description': data['weather'][0]['description'],
            'humidity': data['main']['humidity'],
            'wind_speed': data['wind']['speed']
        }

    def _get_forecast(self, lat, lon, forecast_days):
        """Get weather forecast for given coordinates and days ahead"""
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
        response = requests.get(forecast_url)
        data = response.json()
        
        target_date = datetime.now() + timedelta(days=forecast_days)
        target_forecasts = [item for item in data['list'] 
                          if datetime.fromtimestamp(item['dt']).date() == target_date.date()]
        
        if not target_forecasts:
            return f"No forecast available for {forecast_days} days ahead"
            
        avg_temp = sum(item['main']['temp'] for item in target_forecasts) / len(target_forecasts)
        weather_desc = target_forecasts[0]['weather'][0]['description']
        
        return {
            'temperature': avg_temp,
            'description': weather_desc,
            'date': target_date.strftime('%Y-%m-%d')
        }

    def parse_weather_query(self, text):
        """Parse the weather query to extract city and time"""
        text = text.lower()
        
        tomorrow_indicators = ['tomorrow', 'next day']
        future_indicators = ['day after', 'next week', 'in \d+ days']
        
        words = text.split()
        city = None
        forecast_days = 0
        
        if any(indicator in text for indicator in tomorrow_indicators):
            forecast_days = 1
        elif 'day after' in text:
            forecast_days = 2
        
        for word in words:
            if word not in ['weather', 'temperature', 'forecast', 'in', 'at', 'tomorrow', 'today']:
                city = word
                break
        
        return city, forecast_days

    def format_weather_response(self, weather_data, city, forecast_days=0):
        """Format weather data into a readable response"""
        if isinstance(weather_data, dict):
            if forecast_days == 0:
                response = f"Current weather in {city.title()}: {weather_data['temperature']}°C, {weather_data['description']}. "
                response += f"Humidity: {weather_data['humidity']}%, Wind Speed: {weather_data['wind_speed']} m/s"
            else:
                response = f"Weather forecast for {city.title()} on {weather_data['date']}: "
                response += f"{weather_data['temperature']}°C, {weather_data['description']}"
            return response
        return weather_data 