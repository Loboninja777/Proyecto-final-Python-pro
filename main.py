
from flask import Flask, render_template, request, jsonify, url_for
import requests
from gtts import gTTS
import os
import pandas as pd
import responses

# AGREGAR GRAFICACIÓN DE DATOS CLIMÁTICOS CON CHART.JS (JavaScript) O MATPLOTLIB (Python) DEPENDE CUAL SEA MÁS CÓMODO


app = Flask(__name__)

static_folder = os.path.join(app.root_path, 'static')
if not os.path.exists(static_folder):
    os.makedirs(static_folder)

def geolocalizacion(city):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 1, "language": "en", "format": "json",	"past_days": 7,
	"forecast_days": 14,
}
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        results = data.get("results")
        if not results:
            return None, None
        return results[0]["latitude"], results[0]["longitude"]
    except Exception as e:
        print(f"Error en geolocalizacion: {e}")
        return None, None


def weatherreport(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,surface_pressure",
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        response = responses[0]
        # Process hourly data. The order of variables needs to be the same as requested.
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(1).ValuesAsNumpy()
        hourly_surface_pressure = hourly.Variables(2).ValuesAsNumpy()

        hourly_data = {
        "date": pd.date_range(
            start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
            end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
            freq = pd.Timedelta(seconds = hourly.Interval()),
            inclusive = "left"
        )
    }
        
        hourly_data["temperature_2m"] = hourly_temperature_2m
        hourly_data["precipitation"] = hourly_precipitation
        hourly_data["surface_pressure"] = hourly_surface_pressure
        hourly_dataframe = pd.DataFrame(data = hourly_data)
        print("\nHourly data\n", hourly_dataframe)

        

        if not times:
            return None

        return {
            "temperature": hourly.get("temperature_2m", [None])[0],
            "precipitation": hourly.get("precipitation", [None])[0],
            "pressure": hourly.get("surface_pressure", [None])[0],
            "labels_temperature": [pd.to_datetime(t, unit="s").strftime("%H:%M") for t in times],
            "values_temperature": hourly.get("temperature_2m", [])
        }

    except Exception as e:
        print(f"Error en weatherreport: {e}")
        return None


def generar_audio_clima(weather_data, city):
    if not weather_data:
        return None
    try:
        temp = weather_data.get('temperature')
        precip = weather_data.get('precipitation')
        pressure = weather_data.get('pressure')
        texto = f"El clima en {city} es: {temp} grados Celsius. La precipitación es de {precip} mm. La presión es de {pressure} hPa."
        tts = gTTS(text=texto, lang='es')
        safe_city = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in city).strip().replace(' ', '_')
        filename = f"weather_{safe_city}.mp3"
        path = os.path.join(static_folder, filename)
        tts.save(path)
        return url_for('static', filename=filename)
    except Exception as e:
        print(f"Error en audio: {e}")
        return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_weather", methods=["POST"])
def get_weather():
    city = request.json.get("city")
    if not city:
        return jsonify({"error": "Ingresa una ciudad"}), 400
    
    lat, lon = geolocalizacion(city)
    if lat is None:
        return jsonify({"error": "Ciudad no encontrada"}), 404
    
    weather = weatherreport(lat, lon)
    if weather is None:
        return jsonify({"error": "No se pudo obtener el reporte meteorológico"}), 500
    audio = generar_audio_clima(weather, city)
    
    return jsonify({
        "weather": weather,
        "audio_file": audio
    })

@app.route("/get_fact", methods=["GET"])
def get_fact():
    try:
        res = requests.get("https://uselessfacts.jsph.pl/random.json?language=en", timeout=5)
        return jsonify({"fact": res.json().get("text")})
    except:
        return jsonify({"error": "No se pudo obtener el dato curioso"}), 500

if __name__ == "__main__":
    app.run(debug=True)

