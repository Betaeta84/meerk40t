from .cutobject import CutObject


class DwellCut(CutObject):
    def __init__(self, start_point, settings=None, passes=1, parent=None):
        CutObject.__init__(
            self,
            start_point,
            start_point,
            settings=settings,
            passes=passes,
            parent=parent,
        )
        self.first = True  # Dwell cuts are standalone
        self.last = True
        self.raster_step = 0

    def reversible(self):
        return False

    def reverse(self):
        pass

    def generate(self):
        yield "rapid_mode"
        start = self.start
        yield "move_abs", start[0], start[1]
        yield "dwell", self.dwell_time
