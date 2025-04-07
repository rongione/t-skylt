import requests
import math
from samplebase import SampleBase
from datetime import datetime, timedelta
import time
from rgbmatrix import graphics

# Function to get upcoming METRO departures from API (longer timeframe)
def preload_departures(site_id):
    url = f"https://transport.integration.sl.se/v1/sites/{site_id}/departures"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"Error fetching departures: {e}")
        return []

    departures = []
    now = datetime.now() + timedelta(hours=1)

    # Extract stop-level deviations
    stop_deviations = [d["message"] for d in data.get("stop_deviations", [])]

    if 'departures' in data:
        for dep in data['departures']:
            line = dep.get("line", {}).get("designation", "–")
            destination = dep.get("destination", "–")
            display_time = dep.get("display", "–")
            state = dep.get("state", "")
            transport_mode = dep.get("line", {}).get("transport_mode", "–")

            # Filter out non-metro and cancelled departures
            is_cancelled = state == "CANCELLED" or display_time.lower() == "inställt"
            if is_cancelled or line == "903":
                continue

            if display_time == "Nu":
                minutes_until = 0
                dep_datetime = now
            elif "min" in display_time:
                minutes_until = int(display_time.split()[0])
                dep_datetime = now + timedelta(minutes=minutes_until)
            elif display_time != "–":
                try:
                    dep_time_today = datetime.strptime(display_time, "%H:%M")
                    dep_datetime = now.replace(hour=dep_time_today.hour, minute=dep_time_today.minute,
                                               second=0, microsecond=0)
                    if dep_datetime < now:
                        dep_datetime += timedelta(days=1)
                    minutes_until = int((dep_datetime - now).total_seconds() // 60)
                except ValueError:
                    continue
            else:
                continue

            if minutes_until > 0:
                departures.append({
                    "route": line,
                    "destination": destination,
                    "minutes": minutes_until,
                    "datetime": dep_datetime,
                })

    return sorted(departures, key=lambda x: x['datetime']), stop_deviations

def get_temperature(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m",
        "timezone": "auto"
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data["current"]["temperature_2m"]
    except Exception as e:
        print(f"Error fetching temperature: {e}")
        return None


class RunText(SampleBase):
    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()

        # Fonts and colors
        font = graphics.Font()
        font.LoadFont("/home/ivorongione/rpi-rgb-led-matrix/bindings/python/samples/test.bdf")
        staticFont = graphics.Font()
        staticFont.LoadFont("/home/ivorongione/rpi-rgb-led-matrix/bindings/python/samples/test.bdf")

        # Mer gul
        #textColor = graphics.Color(244, 64, 255)
        #tempColor = graphics.Color(244, 64, 255)

        # Mer orange
        textColor = graphics.Color(135, 20, 216)
        timeColor = graphics.Color(135, 20, 216)

        # Koordinater för Tallkrogen
        latitude = 59.2636
        longitude = 18.0868

        site_id = 9184 # Tallkrogen
        #site_id = 9287 # Skärholmen
        #site_id = 9001 # T-Centralen
        scrollPos = offscreen_canvas.width

        # Brightness settings
        day_brightness = 80
        night_brightness = 5
        last_checked_hour = -1

        last_temp_update = -1
        current_temperature = None

        # Loading screen
        loading_states = ["loading.  ", "loading.. ", "loading..."]
        loading_index = 0
        start_time = time.monotonic()
        loading_timeout = 5

        while time.monotonic() - start_time < loading_timeout:
            offscreen_canvas.Clear()
            loading_message = loading_states[loading_index % len(loading_states)]
            loading_index += 1
            text_x = (64 // 2) - (len(loading_message) * 6 // 2)
            text_y = (32 // 2) + 4
            graphics.DrawText(offscreen_canvas, font, text_x, text_y, textColor, loading_message)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(0.4)

        # Cache setup
        departure_cache, deviation_cache = preload_departures(site_id)
        # deviation_cache = preload_deviations()
        last_cache_update = time.monotonic()
        cache_refresh_interval = 300  # refresh every 5 minutes

        showing_deviation = False
        scroll_cycle = 0

        # Format function to convert cache into display text
        def format_departures(departures, max_results=4):
            now = datetime.now() + timedelta(hours=1)
            upcoming = []

            for d in departures:
                minutes_left = math.ceil((d["datetime"] - now).total_seconds() / 60)
                if minutes_left > 0:
                    time_display = f"{minutes_left} min" if minutes_left < 30 else d["datetime"].strftime("%H:%M")
                    upcoming.append({
                        "route": d["route"],
                        "destination": d["destination"],
                        "time": time_display
                    })
                if len(upcoming) >= max_results:
                    break

            return "   ".join(
                [f"{d['route']} {d['destination']} {d['time']}" for d in upcoming]
            ) or " "

        def format_deviations(deviations, max_results=4):
            return "   ".join(deviations[:max_results]) or " "


        # ---------- MAIN LOOP ----------
        while True:
            offscreen_canvas.Clear()

            # Clock
            now = datetime.now() + timedelta(hours=1)
            timeText = now.strftime("%H:%M")
            clock_x = 0
            graphics.DrawText(offscreen_canvas, staticFont, clock_x, 12, timeColor, timeText)

            # Temperature
            temp_text = f"{current_temperature}°" if current_temperature else "–°"
            temp_x = 50 if len(temp_text) == 2 else 44
            graphics.DrawText(offscreen_canvas, staticFont, temp_x, 12, timeColor, temp_text)

            # Decide what text to show
            if not showing_deviation and scroll_cycle >= 3 and deviation_cache:
                showing_deviation = True
                scroll_cycle = 0  # reset counter when switching to deviation

            if showing_deviation:
                my_text = format_deviations(deviation_cache)
            else:
                my_text = format_departures(departure_cache)

            # Scroll text
            len_scroll_text = graphics.DrawText(offscreen_canvas, font, scrollPos, offscreen_canvas.height - 5,
                                                textColor, my_text)
            scrollPos -= 1

            if scrollPos + len_scroll_text < -1:
                scrollPos = offscreen_canvas.width

                if showing_deviation:
                    showing_deviation = False  # only show deviation once
                else:
                    scroll_cycle += 1

                # Refresh data if needed
                if time.monotonic() - last_cache_update > cache_refresh_interval or \
                        (departure_cache and (departure_cache[-1]["datetime"] - now).total_seconds() < 1800) or \
                        (deviation_cache and len(deviation_cache) == 0):  # refresh if no deviations

                    # Fetch updated data
                    updated_departures, updated_deviations = preload_departures(site_id)

                    if updated_departures:
                        departure_cache = updated_departures
                        deviation_cache = updated_deviations

                    last_cache_update = time.monotonic()

                # Update brightness and temperature
                current_hour = datetime.now().hour + 1
                if current_hour != last_checked_hour:
                    last_checked_hour = current_hour
                    target_brightness = night_brightness if (23 <= current_hour or current_hour < 7) else day_brightness
                    self.matrix.brightness = target_brightness
                    temp = get_temperature(latitude, longitude)
                    if temp is not None:
                        current_temperature = math.floor(temp) if temp % 1 < 0.5 else round(temp)

            # Faster scroll speed if showing deviation
            time.sleep(0.02 if showing_deviation else 0.03)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)

if __name__ == "__main__":
    run_text = RunText()
    if not run_text.process():
        run_text.print_help()