import requests
import math
from samplebase import SampleBase
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import time
from rgbmatrix import graphics

def get_departures_from_cloud():
    url = "serverurl"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        return (
            data.get("departures", []),
            data.get("deviations", []),
            data.get("site_id", 9184),  # Default to Tallkrogen
            data.get("transport_modes", ["METRO"])  # Default to metro
        )
    except Exception as e:
        print(f"Error getting data from cloud: {e}")
        return [], [], 9184, ["METRO"]

def get_temperature(latitude, longitude):
    """
    Fetches the current temperature for a given latitude and longitude from the server.

    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.

    Returns:
        float or None: The current temperature in Celsius, or None if an error occurs.
    """
    url = "serverurl"
    params = {
        "latitude": latitude,
        "longitude": longitude
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("temperature")
    except Exception as e:
        print(f"Error fetching temperature from server: {e}")
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
        font.LoadFont("/path/to/your/font.bdf")
        staticFont = graphics.Font()
        staticFont.LoadFont("/path/to/your/font.bdf")
        textColor = graphics.Color(135, 20, 216)
        timeColor = graphics.Color(135, 20, 216)

        # lat, long for Tallkrogen
        latitude = 59.2636
        longitude = 18.0868

        # Brightness settings
        day_brightness = 80
        night_brightness = 5
        last_checked_hour = -1

        # Temperature and cache settings
        last_temp_update = -1

        temp = get_temperature(latitude, longitude)
        if temp is not None:
            current_temperature = math.floor(temp) if temp % 1 < 0.5 else round(temp)
        departure_cache, deviation_cache, site_id, allowed_modes = get_departures_from_cloud()
        print("Departure cache after fetching:", departure_cache)  # Debug print

        last_cache_update = time.monotonic()
        cache_refresh_interval = 120  # Refresh every 2 minutes

        # Loading screen
        self._show_loading_screen(offscreen_canvas, font, textColor)

        # Scrolling text variables
        scrollPos = offscreen_canvas.width
        showing_deviation = False
        scroll_cycle = 0

        while True:
            offscreen_canvas.Clear()

            # Display clock
            now = datetime.now(ZoneInfo("Europe/Stockholm"))
            timeText = now.strftime("%H:%M")
            graphics.DrawText(offscreen_canvas, staticFont, 0, 12, timeColor, timeText)

            # Display temperature
            temp_text = f"{current_temperature}°" if current_temperature != None else "-°"

            # Räkna ut horisontell position
            text_width = graphics.DrawText(offscreen_canvas, font, 0, 0, timeColor, temp_text)
            text_width -= 0  # since we started at x=0

            matrix_width = 64
            temp_x = matrix_width - text_width

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
                    departure_cache, deviation_cache, site_id, allowed_modes = get_departures_from_cloud()
                    temp = get_temperature(latitude, longitude)
                    if temp is not None:
                        current_temperature = math.floor(temp) if temp % 1 < 0.5 else round(temp)
                    last_cache_update = time.monotonic()

                # Update brightness and temperature
                current_hour = datetime.now().hour + 1
                if current_hour != last_checked_hour:
                    last_checked_hour = current_hour
                    target_brightness = night_brightness if (22 <= current_hour or current_hour < 7) else day_brightness
                    self.matrix.brightness = target_brightness

            # Adjust scroll speed
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
        now = datetime.now(timezone.utc)
        upcoming = []

        for d in departures:
            try:
                # Ensure the datetime field exists and is valid
                dep_time = datetime.fromisoformat(d["datetime"]).replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, KeyError) as e:
                continue

            # Calculate time left until departure
            seconds_left = (dep_time - now).total_seconds()

            # Allow 30 seconds tolerance to prevent flicker
            if seconds_left > -30:
                minutes_left = max(0, math.ceil(seconds_left / 60))

                time_display = (
                    f"{minutes_left} min"
                    if minutes_left < 30
                    else dep_time.strftime("%H:%M")
                )

                upcoming.append(f"{d['route']} {d['destination']} {time_display}")

            if len(upcoming) >= max_results:
                break

        return "   ".join(upcoming) or " "

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