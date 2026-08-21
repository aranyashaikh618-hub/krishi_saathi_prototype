import random
import time
from datetime import datetime
import requests


def get_season(month: int) -> str:
    """Indian agricultural seasons: Kharif (monsoon), Rabi (winter), Zaid (summer)."""
    if month in (6, 7, 8, 9):
        return "kharif"
    elif month in (10, 11, 12, 1, 2, 3):
        return "rabi"
    else:
        return "zaid"


SEASON_PROFILES = {
    "kharif": {"temp_base": 29.0, "humidity_base": 78.0, "rain_chance": 0.20, "rain_amount": (5, 30), "et_multiplier": 0.8},
    "rabi":   {"temp_base": 20.0, "humidity_base": 55.0, "rain_chance": 0.03, "rain_amount": (2, 10), "et_multiplier": 0.6},
    "zaid":   {"temp_base": 36.0, "humidity_base": 32.0, "rain_chance": 0.02, "rain_amount": (1, 8),  "et_multiplier": 1.4},
}

# How fast each soil type loses moisture (sandy drains quickly, clay retains water)
SOIL_RETENTION = {
    "Sandy": 1.3,
    "Loamy": 1.0,
    "Clay": 0.7,
}

CROP_TYPE = "Wheat"
SOIL_TYPE = "Loamy"
SOIL_PH_BASELINE = 6.5


class VirtualFarm:
    """
    Every reading here is derived from the ones before it — nothing is
    independent random noise:

    - air_temperature drifts slowly toward the season's baseline
    - soil_temperature lags behind air_temperature (soil warms/cools slower)
    - humidity is pulled down when air_temperature rises above baseline
      (hot air holds relative humidity down)
    - rain_chance itself rises when humidity is high (humid air is more
      likely to produce rain — a real feedback loop, not a fixed number)
    - a rain event raises humidity AND soil_moisture together
    - soil_moisture's evaporation rate depends on both air_temperature
      and humidity, and is scaled by how well the soil_type retains water
    - soil_ph barely moves reading to reading, same as in real soil
    """

    def __init__(self):
        self.season = get_season(datetime.now().month)
        profile = SEASON_PROFILES[self.season]

        self.air_temperature = profile["temp_base"]
        self.soil_temperature = profile["temp_base"] - 2.0
        self.humidity = profile["humidity_base"]
        self.soil_moisture = 45.0
        self.rainfall = 0.0
        self.soil_ph = SOIL_PH_BASELINE
        self.crop_age_days = 1

    def update_sensors(self):
        self.season = get_season(datetime.now().month)
        profile = SEASON_PROFILES[self.season]

        # --- Air temperature: small, slow drift toward the season baseline ---
        pull = (profile["temp_base"] - self.air_temperature) * 0.05
        self.air_temperature += pull + random.uniform(-0.25, 0.25)

        # --- Soil temperature: derived from air temperature, lags behind it ---
        soil_pull = (self.air_temperature - 2.0 - self.soil_temperature) * 0.1
        self.soil_temperature += soil_pull + random.uniform(-0.15, 0.15)

        # --- Humidity: derived from how far air_temperature is above baseline ---
        temp_deviation = self.air_temperature - profile["temp_base"]
        target_humidity = profile["humidity_base"] - (temp_deviation * 1.5)
        hum_pull = (target_humidity - self.humidity) * 0.08
        self.humidity += hum_pull + random.uniform(-0.6, 0.6)

        # --- Rain chance: derived from current humidity, not a fixed constant ---
        humidity_factor = max(0.5, min(2.0, self.humidity / profile["humidity_base"]))
        effective_rain_chance = profile["rain_chance"] * humidity_factor

        if random.random() < effective_rain_chance:
            rain_amount = random.uniform(*profile["rain_amount"])
            self.rainfall += rain_amount
            self.humidity += rain_amount * 0.3          # rain raises humidity
            self.soil_moisture += rain_amount * 0.8      # rain raises soil moisture
        else:
            self.rainfall = max(0, self.rainfall - 0.4)  # gauge slowly resets between events

        # --- Soil moisture loss: derived from temp, humidity, and soil_type retention ---
        retention = SOIL_RETENTION.get(SOIL_TYPE, 1.0)
        et_loss = (
            0.12
            + max(0, self.air_temperature - 20) * 0.03
            + max(0, 70 - self.humidity) * 0.012
        ) * profile["et_multiplier"] * retention
        self.soil_moisture -= et_loss

        # Irrigation response when soil gets dry
        if self.soil_moisture < 25 and random.random() < 0.3:
            self.soil_moisture += random.uniform(10, 20)

        # --- Soil pH: barely moves reading to reading, same as real soil ---
        self.soil_ph += random.uniform(-0.02, 0.02)

        # --- Crop age: accelerated for demo purposes (~every 20 readings ≈ "1 day") ---
        if random.random() < 0.05:
            self.crop_age_days += 1

        # Realistic bounds — clamps prevent runaway drift, don't drive behavior
        self.air_temperature = max(8, min(46, self.air_temperature))
        self.soil_temperature = max(8, min(42, self.soil_temperature))
        self.humidity = max(15, min(98, self.humidity))
        self.soil_moisture = max(10, min(88, self.soil_moisture))
        self.rainfall = max(0, min(60, self.rainfall))
        self.soil_ph = max(5.5, min(8.5, self.soil_ph))

    def get_sensor_data(self):
        return {
            "device_id": "AGR001",
            "timestamp": datetime.now().isoformat(),
            "soil_moisture": round(self.soil_moisture, 2),
            "soil_temperature": round(self.soil_temperature, 2),
            "air_temperature": round(self.air_temperature, 2),
            "humidity": round(self.humidity, 2),
            "rainfall": round(self.rainfall, 2),
            "crop_type": CROP_TYPE,
            "crop_age_days": self.crop_age_days,
            "soil_type": SOIL_TYPE,
            "soil_ph": round(self.soil_ph, 2),
        }


farm = VirtualFarm()
BACKEND_URL = "http://127.0.0.1:8000/api/sensor-data"

print(f"AgriSense Virtual Sensor Started — season detected: {farm.season}")
print("----------------------------------")

while True:
    farm.update_sensors()
    sensor_data = farm.get_sensor_data()

    try:
        response = requests.post(BACKEND_URL, json=sensor_data)
        print("Sent:", sensor_data)
        print("Backend replied:", response.status_code, response.json())
    except requests.exceptions.ConnectionError:
        print("Could not reach backend — is uvicorn running?")

    print("----------------------------------")

    time.sleep(5)