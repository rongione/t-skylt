import requests
import math
from samplebase import SampleBase
from datetime import datetime, timedelta
import time
from rgbmatrix import graphics


# Function to get upcoming METRO departures
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

    if 'departures' in data:
        for dep in data['departures']:
            line = dep.get("line", {}).get("designation", "–")
            destination = dep.get("destination", "–")
            display_time = dep.get("display", "–")
            state = dep.get("state", "")
            # transport_mode = dep.get("line", {}).get("transport_mode", "–")

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

            if minutes_until >= 0:
                departures.append({
                    "route": line,
                    "destination": destination,
                    "minutes": minutes_until,
                    "datetime": dep_datetime,
                })

    return sorted(departures, key=lambda x: x['datetime'])


class RunText(SampleBase):
    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()

        # Fonts and colors
        font = graphics.Font()
        font.LoadFont("/home/ivorongione/rpi-rgb-led-matrix/bindings/python/samples/5x3.bdf")  # 5x3 font
        text_color = graphics.Color(135, 20, 216)
        time_color = graphics.Color(255, 255, 255)

        site_id = 9184 # Tallkrogen
        # site_id = 9189 # Gullmarsplan
        # site_id = 9287 # Skärholmen
        # site_id = 9001 # T-Centralen
        departure_cache = preload_departures(site_id)
        last_cache_update = time.monotonic()
        cache_refresh_interval = 150

        # Brightness settings
        day_brightness = 70
        night_brightness = 10
        last_checked_hour = -1

        while True:
            offscreen_canvas.Clear()

            # Refresh cache if needed
            now = datetime.now() + timedelta(hours=1)
            if time.monotonic() - last_cache_update > cache_refresh_interval:
                departure_cache = preload_departures(site_id)
                last_cache_update = time.monotonic()

            valid_departures = [
                dep for dep in departure_cache
                if (dep["datetime"] - now).total_seconds() > 0
            ][:6]  # Limit to 5 departures

            current_hour = datetime.now().hour + 1
            if current_hour != last_checked_hour:
                last_checked_hour = current_hour
                target_brightness = night_brightness if (23 <= current_hour or current_hour < 7) else day_brightness
                self.matrix.brightness = target_brightness

            # Show next 5 departures vertically
            y_pos = 6
            counter = 0
            for dep in valid_departures:
                minutes_left = math.ceil((dep["datetime"] - now).total_seconds() / 60)
                time_display = "NU" if minutes_left == 0 else f"{minutes_left}"
                route_display = f"{dep['destination'].upper()}"
                if route_display == 'HÄSSELBY STRAND':
                    route_display = 'HÄSSELBY STR.'
                if route_display == 'FARSTA STRAND':
                    route_display = 'FARSTA STR.'

                # Draw route text on the left
                graphics.DrawText(offscreen_canvas, font, 0, y_pos, text_color, route_display)

                # Draw time remaining on the right
                time_x = 59 if len(time_display) == 1 else 55 # 5 pixels per character
                graphics.DrawText(offscreen_canvas, font, time_x, y_pos, time_color, time_display)

                counter += 1
                y_pos += 6 if counter < 5 else 7

            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(1)


if __name__ == "__main__":
    run_text = RunText()
    if not run_text.process():
        run_text.print_help()
