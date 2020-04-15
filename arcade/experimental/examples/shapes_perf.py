"""
This is for testing geometry shader shapes. Please keep.
"""
import time
import random
import arcade
from pyglet import gl

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TTTLE = "Line Test"

# line / lines
# rectangle_filled / rectangle_outline / rectangle_textured
# parabola


def random_pos():
    return random.randrange(0, SCREEN_WIDTH), random.randrange(0, SCREEN_HEIGHT)


def random_color(alpha=127):
    return random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), alpha


def random_radius(range=(5, 25)):
    return random.randrange(*range)


class TestWindow(arcade.Window):

    def __init__(self, width, height, title):
        super().__init__(800, 600, "Test", antialiasing=True, resizable=True, fullscreen=False)
        # Single lines
        self.single_lines_calls = [(*random_pos(), *random_pos(), random_color()) for _ in range(600)]
        # Line list
        self.line_list = [(random.randrange(0, SCREEN_WIDTH), random.randrange(0, SCREEN_HEIGHT)) for _ in range(2 * 10000)]

        # Single ciricle draw calls
        self.single_circle_calls = [(*random_pos(), random_radius(), random_color()) for _ in range(10000)]

        self.frames = 0
        self.execution_time = 0

    def do_draw_line(self):
        for l in self.single_lines_calls:
            arcade.draw_line(l[0], l[1], l[2], l[3], l[4], 10)

    def do_draw_lines(self):
        arcade.draw_lines(self.line_list, (255, 0, 0, 10))

    def do_draw_circle_filled(self):
        for c in self.single_circle_calls:
            arcade.draw_circle_filled(c[0], c[1], c[2], c[3])

    def do_draw_circle_outline(self):
        pass

    def on_draw(self):
        try:
            self.clear()

            start = time.time()

            # Toggle what to test here
            # self.do_draw_line()
            # self.do_draw_lines()
            self.do_draw_circle_filled()

            self.execution_time += time.time() - start
            self.frames += 1

            if self.execution_time > 1.0 and self.frames > 0:
                print(self.frames, round(self.execution_time, 3), round(self.execution_time / self.frames, 3))
                self.execution_time = 0
                self.frames = 0
        except:
            import traceback
            traceback.print_exc()
            exit(0)

    def on_resize(self, width, height):
        gl.glViewport(0, 0, *self.get_framebuffer_size())

    def on_update(self, dt):
        pass


if __name__ == '__main__':
    window = TestWindow(SCREEN_HEIGHT, SCREEN_HEIGHT, TTTLE)
    arcade.run()
