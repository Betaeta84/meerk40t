"""
GRBL Driver

Governs the generic commands issued by laserjob and spooler and converts that into regular GRBL Gcode output.
"""

import time

from ..core.cutcode import (
    CubicCut,
    DwellCut,
    GotoCut,
    HomeCut,
    InputCut,
    LineCut,
    OutputCut,
    QuadCut,
    SetOriginCut,
    WaitCut,
)
from ..core.parameters import Parameters
from ..core.plotplanner import PlotPlanner
from ..core.units import UNITS_PER_INCH, UNITS_PER_MIL, UNITS_PER_MM
from ..device.basedevice import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING


class GRBLDriver(Parameters):
    def __init__(self, service, **kwargs):
        super().__init__(**kwargs)
        self.service = service
        self.name = str(service)
        self.hold = False
        self.paused = False
        self.native_x = 0
        self.native_y = 0
        self.origin_x = 0
        self.origin_y = 0
        self.stepper_step_size = UNITS_PER_MIL
        # TODO: Update self.settings to use updated parameters values.
        self.plot_planner = PlotPlanner(single=True, smooth=False, ppi=False, shift=False, group=True)
        self.queue = []
        self.plot_data = None

        self.on_value = 0
        self.power_dirty = True
        self.speed_dirty = True
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True

        self._absolute = True
        self.feed_mode = None
        self.feed_convert = None
        self._g94_feedrate()  # G93 DEFAULT, mm mode

        self.unit_scale = None
        self.units = None
        self._g21_units_mm()
        self._g91_absolute()

        self.grbl = self.service.channel("grbl", pure=True)
        self.grbl_realtime = self.service.channel("grbl-realtime", pure=True)

        self.move_mode = 0
        self.reply = None
        self.elements = None

    def __repr__(self):
        return f"GRBLDriver({self.name})"

    def hold_work(self, priority):
        """
        Required.

        Spooler check. to see if the work cycle should be held.

        @return: hold?
        """
        return priority <= 0 and (self.paused or self.hold)

    def move_ori(self, x, y):
        """
        Requests laser move to origin offset position x,y in physical units

        @param x:
        @param y:
        @return:
        """
        self._g91_absolute()
        self._clean()
        old_current = self.service.current
        x, y = self.service.physical_to_device_position(x, y)
        self._move(self.origin_x + x, self.origin_y + y)
        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        self._g91_absolute()
        self._clean()
        old_current = self.service.current
        x, y = self.service.physical_to_device_position(x, y)
        self._move(x, y)
        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def move_rel(self, dx, dy):
        """
        Requests laser move relative position dx, dy in physical units

        @param dx:
        @param dy:
        @return:
        """
        self._g90_relative()
        self._clean()
        old_current = self.service.current

        dx, dy = self.service.physical_to_device_length(dx, dy)
        # self.rapid_mode()
        self._move(dx, dy)

        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def dwell(self, time_in_ms):
        """
        Requests that the laser fire in place for the given time period. This could be done in a series of commands,
        move to a location, turn laser on, wait, turn laser off. However, some drivers have specific laser-in-place
        commands so calling dwell is preferred.

        @param time_in_ms:
        @return:
        """
        self.laser_on()  # This can't be sent early since these are timed operations.
        self.wait(time_in_ms)
        self.laser_off()

    def laser_off(self, *values):
        """
        Turn laser off in place.

        @param values:
        @return:
        """
        self.grbl("M3\r")

    def laser_on(self, *values):
        """
        Turn laser on in place.

        @param values:
        @return:
        """
        self.grbl("M5\r")

    def plot(self, plot):
        """
        Gives the driver a bit of cutcode that should be plotted.
        @param plot:
        @return:
        """
        self.queue.append(plot)

    def plot_start(self):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """
        self._g91_absolute()
        self._g94_feedrate()
        self._clean()
        if self.service.use_m3:
            self.grbl("M3\r")
        else:
            self.grbl("M4\r")
        for q in self.queue:
            x = self.native_x
            y = self.native_y
            start_x, start_y = q.start
            if x != start_x or y != start_y:
                self.on_value = 0
                self.power_dirty = True
                self.move_mode = 0
                self._move(start_x, start_y)
            if self.on_value != 1.0:
                self.power_dirty = True
            self.on_value = 1.0
            if q.power != self.power:
                self.set("power", q.power)
            if (
                q.speed != self.speed
                or q.raster_step_x != self.raster_step_x
                or q.raster_step_y != self.raster_step_y
            ):
                self.set("speed", q.speed)
            # TODO: Update method of q.settings to match.
            self.settings.update(q.settings)
            if isinstance(q, LineCut):
                self.move_mode = 1
                self._move(*q.end)
            elif isinstance(q, (QuadCut, CubicCut)):
                self.move_mode = 1
                interp = self.service.interpolate
                step_size = 1.0 / float(interp)
                t = step_size
                for p in range(int(interp)):
                    while self.paused:
                        time.sleep(0.05)
                    self._move(*q.point(t))
                    t += step_size
                last_x, last_y = q.end
                self._move(last_x, last_y)
            elif isinstance(q, WaitCut):
                self.wait(q.dwell_time)
            elif isinstance(q, HomeCut):
                self.home()
            elif isinstance(q, GotoCut):
                start = q.start
                self._move(self.origin_x + start[0], self.origin_y + start[1])
            elif isinstance(q, SetOriginCut):
                if q.set_current:
                    x = self.native_x
                    y = self.native_y
                else:
                    x, y = q.start
                self.set_origin(x, y)
            elif isinstance(q, DwellCut):
                self.dwell(q.dwell_time)
            elif isinstance(q, (InputCut, OutputCut)):
                # GRBL has no core GPIO functionality
                pass
            else:
                self.plot_planner.push(q)
                for x, y, on in self.plot_planner.gen():
                    while self.paused:
                        time.sleep(0.05)
                    if on > 1:
                        # Special Command.
                        if on & PLOT_FINISH:  # Plot planner is ending.
                            break
                        elif on & PLOT_SETTING:  # Plot planner settings have changed.
                            # TODO: Create copy of dict with corrected attributes.
                            p_set = Parameters(self.plot_planner.settings)
                            if p_set.power != self.power:
                                self.set("power", p_set.power)
                            if (
                                p_set.speed != self.speed
                                or p_set.raster_step_x != self.raster_step_x
                                or p_set.raster_step_y != self.raster_step_y
                            ):
                                self.set("speed", p_set.speed)
                            self.settings.update(p_set.settings)
                        elif on & (
                            PLOT_RAPID | PLOT_JOG
                        ):  # Plot planner requests position change.
                            self.move_mode = 0
                            self._move(x, y)
                        continue
                    if on == 0:
                        self.move_mode = 0
                    else:
                        self.move_mode = 1
                    if self.on_value != on:
                        self.power_dirty = True
                    self.on_value = on
                    self._move(x, y)
        self.queue.clear()

        self.grbl("G1 S0\r")
        self.grbl("M5\r")
        self.power_dirty = True
        self.speed_dirty = True
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True
        return False

    def blob(self, data_type, data):
        """
        This is intended to send a blob of gcode to be processed and executed.

        @param data_type:
        @param data:
        @return:
        """
        if data_type != "gcode":
            return
        for line in data:
            # TODO: Process line does not exist as a function.
            self.process_line(line)

    def home(self):
        """
        Home the laser.

        @return:
        """
        self.native_x = 0
        self.native_y = 0
        self.grbl("G28\r")

    def rapid_mode(self, *values):
        """
        Rapid mode sets the laser to rapid state. This is usually moving the laser around without it executing a large
        batch of commands.

        @param values:
        @return:
        """

    def finished_mode(self, *values):
        """
        Finished mode is after a large batch of jobs is done.

        @param values:
        @return:
        """
        self.grbl("M5\r")

    def program_mode(self, *values):
        """
        Program mode is the state lasers often use to send a large batch of commands.
        @param values:
        @return:
        """
        self.grbl("M3\r")

    def raster_mode(self, *values):
        """
        Raster mode is a special form of program mode that suggests the batch of commands will be a raster operation
        many lasers have specialty values
        @param values:
        @return:
        """

    def set(self, key, value):
        """
        Sets a laser parameter this could be speed, power, wobble, number_of_unicorns, or any unknown parameters for
        yet to be written drivers.
        @param key:
        @param value:
        @return:
        """
        if key == "power":
            self.power_dirty = True
        if key == "speed":
            self.speed_dirty = True
        self.settings[key] = value

    def set_origin(self, x, y):
        """
        This should set the origin position.

        @param x:
        @param y:
        @return:
        """
        self.origin_x = x
        self.origin_y = y

    def wait(self, time_in_ms):
        """
        Wait asks that the work be stalled or current process held for the time time_in_ms in ms. If wait_finished is
        called first this will attempt to stall the machine while performing no work. If the driver in question permits
        waits to be placed within code this should insert waits into the current job. Returning instantly rather than
        holding the processes.

        @param time_in_ms:
        @return:
        """
        self.grbl(f"G04 S{time_in_ms / 1000.0}\r")

    def wait_finish(self, *values):
        """
        Wait finish should hold the calling thread until the current work has completed. Or otherwise prevent any data
        from being sent with returning True for the until that criteria is met.

        @param values:
        @return:
        """
        pass

    def function(self, function):
        """
        This command asks that this function be executed at the appropriate time within the spooled cycle.

        @param function:
        @return:
        """
        function()

    def beep(self):
        """
        Wants a system beep to be issued.
        This command asks that a beep be executed at the appropriate time within the spooled cycle.

        @return:
        """
        self.service("beep\n")

    def console(self, value):
        """
        This asks that the console command be executed at the appropriate time within the spooled cycle.

        @param value: console command
        @return:
        """
        self.service(value)

    def signal(self, signal, *args):
        """
        This asks that this signal be broadcast at the appropriate time within the spooling cycle.

        @param signal:
        @param args:
        @return:
        """
        self.service.signal(signal, *args)

    def pause(self, *args):
        """
        Asks that the laser be paused.

        @param args:
        @return:
        """
        self.paused = True
        self.grbl_realtime("!")

    def resume(self, *args):
        """
        Asks that the laser be resumed.

        To work this command should usually be put into the realtime work queue for the laser.

        @param args:
        @return:
        """
        self.paused = False
        self.grbl_realtime("~")

    def reset(self, *args):
        """
        This command asks that this device be emergency stopped and reset. Usually that queue data from the spooler be
        deleted.
        Asks that the device resets, and clears all current work.

        @param args:
        @return:
        """
        self.service.spooler.clear_queue()
        self.plot_planner.clear()
        self.grbl_realtime("\x18")
        self.paused = False

    def clear_alarm(self):
        """
        GRBL clear alarm signal.

        @return:
        """
        self.grbl_realtime("$X\n")

    def status(self):
        """
        Asks that this device status be updated.

        @return:
        """
        self.grbl_realtime("?")

        parts = list()
        parts.append(f"x={self.native_x}")
        parts.append(f"y={self.native_y}")
        parts.append(f"speed={self.settings.get('speed', 0.0)}")
        parts.append(f"power={self.settings.get('power', 0)}")
        status = ";".join(parts)
        self.service.signal("driver;status", status)

    ####################
    # PROTECTED DRIVER CODE
    ####################

    def _move(self, x, y, absolute=False):
        if self._absolute:
            self.native_x = x
            self.native_y = y
        else:
            self.native_x += x
            self.native_y += y
        line = []
        if self.move_mode == 0:
            line.append("G0")
        else:
            line.append("G1")
        x /= self.unit_scale
        y /= self.unit_scale
        line.append(f"X{x:.3f}")
        line.append(f"Y{y:.3f}")
        if self.power_dirty:
            if self.power is not None:
                line.append(f"S{self.power * self.on_value:.1f}")
            self.power_dirty = False
        if self.speed_dirty:
            line.append(f"F{self.feed_convert(self.speed):.1f}")
            self.speed_dirty = False
        self.grbl(" ".join(line) + "\r")

    def _clean(self):
        if self.absolute_dirty:
            if self._absolute:
                self.grbl("G90\r")
            else:
                self.grbl("G91\r")
        self.absolute_dirty = False

        if self.feedrate_dirty:
            if self.feed_mode == 94:
                self.grbl("G94\r")
            else:
                self.grbl("G93\r")
        self.feedrate_dirty = False

        if self.units_dirty:
            if self.units == 20:
                self.grbl("G20\r")
            else:
                self.grbl("G21\r")
        self.units_dirty = False

    def _g90_relative(self):
        if not self._absolute:
            return
        self._absolute = False
        self.absolute_dirty = True

    def _g91_absolute(self):
        if self._absolute:
            return
        self._absolute = True
        self.absolute_dirty = True

    def _g93_mms_to_minutes_per_gunits(self, mms):
        millimeters_per_minute = 60.0 * mms
        distance = UNITS_PER_MIL / self.stepper_step_size
        return distance / millimeters_per_minute

    def _g93_feedrate(self):
        if self.feed_mode == 93:
            return
        self.feed_mode = 93
        # Feed Rate in Minutes / Unit
        self.feed_convert = self._g93_mms_to_minutes_per_gunits
        self.feedrate_dirty = True

    def _g94_mms_to_gunits_per_minute(self, mms):
        millimeters_per_minute = 60.0 * mms
        distance = UNITS_PER_MIL / self.stepper_step_size
        return millimeters_per_minute / distance

    def _g94_feedrate(self):
        if self.feed_mode == 94:
            return
        self.feed_mode = 94
        # Feed Rate in Units / Minute
        self.feed_convert = self._g94_mms_to_gunits_per_minute
        # units to mm, seconds to minutes.
        self.feedrate_dirty = True

    def _g20_units_inch(self):
        self.units = 20
        self.unit_scale = UNITS_PER_INCH / self.stepper_step_size  # g20 is inch mode.
        self.units_dirty = True

    def _g21_units_mm(self):
        self.units = 21
        self.unit_scale = UNITS_PER_MM / self.stepper_step_size  # g21 is mm mode.
        self.units_dirty = True
