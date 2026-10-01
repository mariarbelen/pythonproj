"""Circle Intersection Visualizer.

Click to draw two circles, then see how they relate: separate, touching,
overlapping, one inside the other, or identical.

For each circle, click once for its center and once on its edge to set the
radius. After both circles are drawn, click anywhere to start over.

Author: Maria Rodriguez
"""

import math
import sys

try:
    import tkinter as tk
except ImportError:  # some Linux installs ship Python without Tk
    tk = None

WIN_WIDTH = 500
WIN_HEIGHT = 500
MIN_RADIUS = 5
COLORS = ("blue", "red")

SEPARATE = "The circles are completely separate."
EXTERNALLY_TANGENT = "The circles touch at a single point (outside)."
INTERSECTING = "The circles intersect at two points."
INTERNALLY_TANGENT = "The circles touch at a single point (inside)."
CONTAINED = "One circle is contained within the other."
COINCIDENT = "The circles are identical."


def classify_circles(x0, y0, r0, x1, y1, r1, tolerance=1e-9):
    """Return a message describing how two circles relate to each other.

    Compares the distance between the centers with the sum and difference
    of the radii. Distances within `tolerance` of each other count as equal.
    """
    if r0 <= 0 or r1 <= 0:
        raise ValueError("radii must be positive")

    dist = math.hypot(x1 - x0, y1 - y0)
    radius_sum = r0 + r1
    radius_diff = abs(r0 - r1)

    if dist <= tolerance and radius_diff <= tolerance:
        return COINCIDENT
    if dist > radius_sum + tolerance:
        return SEPARATE
    if abs(dist - radius_sum) <= tolerance:
        return EXTERNALLY_TANGENT
    if abs(dist - radius_diff) <= tolerance:
        return INTERNALLY_TANGENT
    if dist < radius_diff:
        return CONTAINED
    return INTERSECTING


class CircleApp:
    """Collects clicks, draws the circles and shows the result."""

    def __init__(self, root):
        self.canvas = tk.Canvas(root, width=WIN_WIDTH, height=WIN_HEIGHT, bg="white")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.reset()

    def reset(self):
        self.canvas.delete("all")
        self.circles = []  # list of (x, y, radius)
        self.center = None
        self.show_hint("Click to place the center of the blue circle.")

    def show_hint(self, text):
        self.canvas.delete("hint")
        self.canvas.create_text(10, WIN_HEIGHT - 12, text=text, anchor="w", tags="hint")

    def on_click(self, event):
        if len(self.circles) == 2:
            self.reset()
            return

        color = COLORS[len(self.circles)]
        if self.center is None:
            self.center = (event.x, event.y)
            self.canvas.create_oval(event.x - 2, event.y - 2, event.x + 2, event.y + 2,
                                    fill=color, outline=color)
            self.show_hint(f"Click on the edge of the {color} circle to set its radius.")
            return

        x, y = self.center
        radius = math.hypot(event.x - x, event.y - y)
        if radius < MIN_RADIUS:
            self.show_hint(f"The radius must be at least {MIN_RADIUS} pixels. Click farther away.")
            return

        self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                                outline=color, width=2)
        self.circles.append((x, y, radius))
        self.center = None

        if len(self.circles) == 1:
            self.show_hint("Click to place the center of the red circle.")
        else:
            (x0, y0, r0), (x1, y1, r1) = self.circles
            # Clicks land on whole pixels, so allow one pixel of slack.
            message = classify_circles(x0, y0, r0, x1, y1, r1, tolerance=1.0)
            self.show_hint(message + "  Click to start over.")


def main():
    if tk is None:
        sys.exit("This program needs Tkinter. On Debian/Ubuntu: sudo apt install python3-tk")
    root = tk.Tk()
    root.title("Circle Intersection")
    root.resizable(False, False)
    CircleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
