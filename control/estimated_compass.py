"""Estimates readings from the compass, because it's slow to update."""

import time


class EstimatedCompass(object):
    """Estimates readings from the compass, because it's slow to update."""
    DEAD_TIME_S = 0.25
    TRAVEL_RATE_D_S = 90.0

    def __init__(self):
        self._turn_time = None
        self._update_time = None
        self._turn = 0
        self._speed = 0
        self._estimated_compass = None
        self._estimated_heading = None
        self._delay = False
        self._compass_turning = False

    def process_drive_command(self, speed, turn, compass_heading):
        """Takes into account the vehicle's turn."""
        self._speed = speed
        self._turn = turn

        now = time.time()
        self._turn_time = now
        self._update_time = now

        if turn > 0.1 or turn < -0.1:
            self._delay = True
            self._compass_turning = True
            self._estimated_compass = compass_heading
            if self._estimated_heading is None:
                self._estimated_heading = compass_heading

    def get_estimated_heading(self, compass_heading):
        """Returns the estimated heading. If the car has been driving straight
        for a while, this should return the plain compass heading.
        """
        # Because the compass takes so long to update, we'll need to guess the
        # true heading and then incorporate real values once it's had a chance
        # to catch up. Let's assume the compass is dead for .25 seconds then
        # travels 90 degrees per second, and that the car turns 90 degrees per
        # second. The latter formula should take into account the car's speed
        # and turn rate, but we'll have to take more observations to tweak it.
        if not self._compass_turning:
            return compass_heading

        now = time.time()
        time_diff_s = now - self._update_time
        self._update_time = now

        # Import here to prevent circular imports
        from telemetry import Telemetry

        self._estimated_heading += Telemetry.wrap_degrees(
            self._car_turn_rate_d_s() * time_diff_s
        )

        if self._delay:
            if self._turn_time + EstimatedCompass.DEAD_TIME_S <= now:
                self._delay = False
        else:
            step_d = self._compass_turn_rate_d_s() * time_diff_s
            self._estimated_compass += step_d

            if Telemetry.difference_d(
                self._estimated_compass,
                self._estimated_heading
            ) < abs(step_d):
                self._compass_turning = False

        return self._estimated_heading

    def _car_turn_rate_d_s(self):
        """Returns the approximate turn rate of the car in degrees per second
        for the given speed and turn value.
        """
        # TODO: Validate this with some observations of the car and incorporate
        # speed
        return self._turn * 90.0

    def _compass_turn_rate_d_s(self):
        """Returns the approximate turn rate of the compass in degrees per
        second for the given speed and turn value.
        """
        # TODO: Validate this with some observations of the compass
        return 90.0