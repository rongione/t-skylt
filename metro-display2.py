import requests
import math
from samplebase import SampleBase
from datetime import datetime, timedelta
import time
from rgbmatrix import graphics

# Function to get upcoming METRO departures from API
def preload_departures(site_id):
    """
    Fetches upcoming departures from the SL API for a given site ID.

    Args:
        site_id (int): The site ID for the metro station.
        allowed_modes (String): the allowed transport modes

    Returns:
        tuple: A sorted list of departures and a list of stop deviations.
    """
    url = f"https://transport.integration.sl.se/v1/sites/{site_id}/departures"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        print(f"API Response: {data}")  # Debugging: Log raw API response
    except Exception as e:
        print(f"Error fetching departures: {e}")
        return [], []

    departures = []
    now = datetime.now() + timedelta(hours=1)

    # Extract stop-level deviations
    stop_deviations = [d["message"] for d in data.get("stop_deviations", [])]
    print(f"Stop Deviations: {stop_deviations}")

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

            # Parse departure time
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

    print(f"Parsed Departures: {departures}")
    return sorted(departures, key=lambda x: x['datetime']), stop_deviations


def get_temperature(latitude, longitude):
    """
    Fetches the current temperature for a given latitude and longitude.

    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.

    Returns:
        float or None: The current temperature in Celsius, or None if an error occurs.
    """
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
    """
    Displays scrolling text on an RGB LED matrix, including metro departures,
    deviations, current time, and temperature.
    """

    def run(self):
        # Initialize canvas
        offscreen_canvas = self.matrix.CreateFrameCanvas()

        # Fonts and colors
        font = graphics.Font()
        font.LoadFont("/home/ivorongione/rpi-rgb-led-matrix/bindings/python/samples/test.bdf")
        staticFont = graphics.Font()
        staticFont.LoadFont("/home/ivorongione/rpi-rgb-led-matrix/bindings/python/samples/test.bdf")
        textColor = graphics.Color(135, 20, 216)
        timeColor = graphics.Color(135, 20, 216)

        # Location and site ID
        latitude = 59.2636
        longitude = 18.0868

        # Brightness settings
        day_brightness = 80
        night_brightness = 5
        last_checked_hour = -1

        # Temperature and cache settings
        last_temp_update = -1
        current_temperature = None

        # site_id = self._get_site_id()
        site_id = 9184  # Tallkrogen
        # allowed_modes = self._get_transport_modes()
        departure_cache, deviation_cache = preload_departures(site_id)

        last_cache_update = time.monotonic()
        cache_refresh_interval = 180  # Refresh every 3 minutes

        # Loading screen
        self._show_loading_screen(offscreen_canvas, font, textColor)

        # Scrolling text variables
        scrollPos = offscreen_canvas.width
        showing_deviation = False
        scroll_cycle = 0

        while True:
            offscreen_canvas.Clear()

            # Display clock
            now = datetime.now() + timedelta(hours=1)
            timeText = now.strftime("%H:%M")
            graphics.DrawText(offscreen_canvas, staticFont, 0, 12, timeColor, timeText)

            # Display temperature
            temp_text = f"{current_temperature}°" if current_temperature else "-°"
            temp_x = 50 if len(temp_text) == 2 else 44

            if temp_text[0] == "2" and temp_text[1] != "1":
                temp_x = 42

            graphics.DrawText(offscreen_canvas, staticFont, temp_x, 12, timeColor, temp_text)

            # Decide what text to scroll
            if not showing_deviation and scroll_cycle >= 3 and deviation_cache:
                showing_deviation = True
                scroll_cycle = 0  # Reset counter when switching to deviation

            if showing_deviation:
                my_text = self._format_deviations(deviation_cache)
            else:
                my_text = self._format_departures(departure_cache)

            # Scroll text
            len_scroll_text = graphics.DrawText(offscreen_canvas, font, scrollPos, offscreen_canvas.height - 5,
                                                textColor, my_text)
            scrollPos -= 1

            if scrollPos + len_scroll_text < -1:
                scrollPos = offscreen_canvas.width

                if showing_deviation:
                    showing_deviation = False  # Only show deviation once
                else:
                    scroll_cycle += 1

                # Refresh data if needed
                if time.monotonic() - last_cache_update > cache_refresh_interval:
                    # allowed_modes = self._get_transport_modes()
                    # site_id = self._get_site_id()
                    departure_cache, deviation_cache = preload_departures(site_id)
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

            # Adjust scroll speed
            # time.sleep(0.02 if showing_deviation else 0.03)
            time.sleep(0.02)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)

    def _show_loading_screen(self, canvas, font, color):
        """
        Displays a loading screen animation.

        Args:
            canvas: The canvas to draw on.
            font: The font to use for the text.
            color: The color of the text.
        """
        loading_states = ["loading.  ", "loading.. ", "loading..."]
        loading_index = 0
        start_time = time.monotonic()
        loading_timeout = 5

        while time.monotonic() - start_time < loading_timeout:
            canvas.Clear()
            loading_message = loading_states[loading_index % len(loading_states)]
            loading_index += 1
            text_x = (64 // 2) - (len(loading_message) * 6 // 2)
            text_y = (32 // 2) + 4
            graphics.DrawText(canvas, font, text_x, text_y, color, loading_message)
            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(0.4)

    def _format_departures(self, departures, max_results=4):
        """
        Formats departure data for display.

        Args:
            departures (list): List of departure dictionaries.
            max_results (int): Maximum number of departures to display.

        Returns:
            str: Formatted departure text.
        """
        now = datetime.now() + timedelta(hours=1)
        upcoming = []

        for d in departures:
            minutes_left = math.ceil((d["datetime"] - now).total_seconds() / 60)
            if minutes_left > 0:
                time_display = f"{minutes_left} min" if minutes_left < 30 else d["datetime"].strftime("%H:%M")
                upcoming.append(f"{d['route']} {d['destination']} {time_display}")
            if len(upcoming) >= max_results:
                break

        return "   ".join(upcoming) or " "

    def _get_site_id(self):
        """
        Fetches the current site ID from the local Flask server.
        Falls back to Tallkrogen (9184) if request fails.
        """
        try:
            res = requests.get("http://localhost:8080/get-site", timeout=2)
            return res.json().get("site_id", 9184)
        except Exception as e:
            print(f"Error fetching site_id from local server: {e}")
            return 9184

    def _get_transport_modes(self):
        """
        Fetches the allowed transport modes from the local Flask server.
        Falls back to ["METRO"] if request fails.
        """
        try:
            res = requests.get("http://localhost:8080/get-transport-modes", timeout=2)
            return res.json().get("transport_modes", ["METRO"])
        except Exception as e:
            print(f"Error fetching transport modes from local server: {e}")
            return ["METRO"]

    def _format_deviations(self, deviations, max_results=4):
        """
        Formats deviation messages for display.

        Args:
            deviations (list): List of deviation messages.
            max_results (int): Maximum number of deviations to display.

        Returns:
            str: Formatted deviation text.
        """
        return "   ".join(deviations[:max_results]) or " "


if __name__ == "__main__":
    run_text = RunText()
    if not run_text.process():
        run_text.print_help()