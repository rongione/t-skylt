from samplebase import SampleBase
from rgbmatrix import graphics, RGBMatrixOptions
import time

class ShowText(SampleBase):

    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()
        self.matrix.brightness = 80

        font = graphics.Font()
        font.LoadFont("test.bdf")

        #color = graphics.Color(196, 46, 246) # GBR 1 ganska bra
        #color = graphics.Color(244, 64, 255)  # GBR 2 lite ljusare än 1
        color = graphics.Color(135, 20, 216)  # GBR mest orange

        pos_x = 2
        pos_y = 25

        #alphabet = "f"
        # alphabet = "abcdefghijklmnopqrstuvwxyzåäö"
        # bigalphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ"
        frame_letter = "21"
        # make it draw the text in a loop

        # Display temperature
        temp_text = "-21°"

        # --- Measure text width dynamically ---
        # DrawText() returns x position immediately after the last drawn pixel
        text_width = graphics.DrawText(canvas, font, 0, 0, white, temp_text)
        text_width -= 0  # since we started at x=0

        # --- Compute x-position for alignment ---
        # Adjust these based on where you want the temperature to appear:
        matrix_width = 64
        temp_y = 12  # example vertical position
        temp_x = matrix_width - text_width

        # --- Draw temperature on matrix ---
        graphics.DrawText(offscreen_canvas, font, temp_x, temp_y, white, temp_text)

        while True:

            triplet = temp_text
            offscreen_canvas.Clear()
            graphics.DrawText(offscreen_canvas, font, temp_x, pos_y, color, triplet)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(2)

if __name__ == "__main__":
    show_text = ShowText("")
    if not show_text.process():
        show_text.print_help()