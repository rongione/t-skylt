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
        pos_y = 20

        #alphabet = "f"
        alphabet = "abcdefghijklmnopqrstuvwxyzåäö"
        bigalphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ"
        frame_letter = "r"
        graphics.DrawText(offscreen_canvas, font, 20, 10, color, frame_letter)

        while True:
            for letter in alphabet:
                triplet = frame_letter + letter + frame_letter
                offscreen_canvas.Clear()
                graphics.DrawText(offscreen_canvas, font, pos_x, pos_y, color, triplet)
                offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)
                time.sleep(1)

if __name__ == "__main__":
    show_text = ShowText("")
    if not show_text.process():
        show_text.print_help()