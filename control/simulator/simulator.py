"""Simulates the car with telemetry."""
import math
import mock
import time

from command import Command
from telemetry import Telemetry

# pylint: disable=missing-docstring
# pylint: disable=no-self-use
# pylint: disable=protected-access
# pylint: disable=superfluous-parens
# pylint: disable=too-few-public-methods


class FakeLogger(object):
    def debug(self, message):
        pass
    def info(self, message):
        print(message)
    def warning(self, message):
        print(message)
    def error(self, message):
        print(message)


class FakeSocket(object):
    def send(self, message):
        pass


class TelemetrySimulator(object):
    def __init__(self, first_way_point):
        self._latitude, self._longitude = first_way_point
        self._latitude -= 0.001
        self._heading = 0.0
        self._last_command_time = time.time()
        self._throttle = 0.0
        self._turn = 0.0

        self.update_count = 1000
        self.command = None

    def get_raw_data(self):
        raise NotImplementedError

    def get_data(self):
        values = {
            'heading': self._heading,
            'latitude': self._latitude,
            'longitude': self._longitude,
        }
        return values

    def process_drive_command(self, throttle, turn):
        print(
            'Throttle: {throttle}, turn: {turn}'.format(
                throttle=throttle,
                turn=turn,
            )
        )
        self._throttle = throttle
        self._turn = turn

    def _update_position(self):
        self.update_count -= 1
        if self.update_count <= 0:
            assert self.command is not None
            self.command.kill()

        diff_time_s = 1.0

        if self._throttle > 0.0:
            self._heading += self._turn * 20.0
            self._heading = Telemetry.wrap_degrees(self._heading)

            point = (0, diff_time_s * self._throttle * 1.0 / Telemetry.m_per_d_latitude())
            radians = math.radians(self._heading)
            point = Telemetry.rotate_radians_clockwise(point, radians)
            self._latitude += point[1]
            self._longitude += point[0]

    def is_stopped(self):
        return False


def main():
    """Main function."""
    fake_logger = FakeLogger()
    box = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
    waypoints = [(x * .001 + 10, y * .001 + 10) for x, y in box]
    telemetry_simulator = TelemetrySimulator(waypoints[0])
    fake_socket = FakeSocket()
    command = Command(
        telemetry_simulator,
        fake_socket,
        fake_logger,
        sleep_time_milliseconds=1,
        waypoints=waypoints,
    )
    telemetry_simulator.command = command
    command._wait = mock.Mock(side_effect=telemetry_simulator._update_position)
    command.run_course()
    command.run()


if __name__ == '__main__':
    main()
