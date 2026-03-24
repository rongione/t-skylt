import requests
import math
from samplebase import SampleBase
from datetime import datetime, timedelta
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
            data.get("site_id", 9189),
            data.get("transport_modes", ["METRO"])
        )
    except Exception as e:
        print(f"Error getting data from cloud: {e}")
        return [], [], 9184, ["METRO"]

class RunText(SampleBase):
    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("/path/to/your/font.bdf")
        text_color = graphics.Color(135, 20, 216)
        time_color = graphics.Color(255, 255, 255)

        departure_cache, deviation_cache, site_id, allowed_modes = get_departures_from_cloud()
        print("Departure cache after fetching:", departure_cache)
        last_cache_update = time.monotonic()
        cache_refresh_interval = 120

        day_brightness = 70
        night_brightness = 10
        last_checked_hour = -1

        while True:
            offscreen_canvas.Clear()
            now = datetime.utcnow()

            if time.monotonic() - last_cache_update > cache_refresh_interval:
                departure_cache, deviation_cache, site_id, allowed_modes = get_departures_from_cloud()
                last_cache_update = time.monotonic()

            valid_departures = []
            for dep in departure_cache:
                try:
                    dep_time = datetime.fromisoformat(dep["datetime"])
                    seconds_left = (dep_time - now).total_seconds()
                    if seconds_left > 0:
                        valid_departures.append(dep)
                except Exception as e:
                    print(f"Error parsing departure datetime: {dep['datetime']}, error: {e}")

            current_hour = (datetime.utcnow() + timedelta(hours=2)).hour
            if current_hour != last_checked_hour:
                last_checked_hour = current_hour
                target_brightness = night_brightness if (23 <= current_hour or current_hour < 7) else day_brightness
                self.matrix.brightness = target_brightness

            y_pos = 6
            counter = 0
            for dep in valid_departures[:6]:
                dep_time = datetime.fromisoformat(dep["datetime"])
                minutes_left = math.ceil((dep_time - now).total_seconds() / 60)
                time_display = "NU" if minutes_left == 0 else f"{minutes_left}"
                route_display = f"{dep['destination'].upper()}"
                if route_display == 'HÄSSELBY STRAND':
                    route_display = 'HÄSSELBY STR.'
                if route_display == 'FARSTA STRAND':
                    route_display = 'FARSTA STR.'

                graphics.DrawText(offscreen_canvas, font, 0, y_pos, text_color, route_display)
                time_x = 59 if len(time_display) == 1 else 55
                graphics.DrawText(offscreen_canvas, font, time_x, y_pos, time_color, time_display)

                counter += 1
                y_pos += 6 if counter < 5 else 7

            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(1)


if __name__ == "__main__":
    run_text = RunText()
    if not run_text.process():
        run_text.print_help()
