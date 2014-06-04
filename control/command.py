"""Class to control the RC car."""

import collections
import math
import threading
import time

from dune_warrior import command
from telemetry import Telemetry

# pylint: disable=superfluous-parens


class Command(threading.Thread):
    """Processes telemetry data and controls the RC car."""

    def __init__(
        self,
        telemetry,
        send_socket,
        commands,
        sleep_time_milliseconds=None
    ):
        """Create the Command thread. send_socket is just a wrapper around
        some other kind of socket that has a simple "send" method.
        """
        super(Command, self).__init__()

        self._valid_commands = {'start', 'stop'}
        self._telemetry = telemetry
        if sleep_time_milliseconds is None:
            self._sleep_time_seconds = .02
        else:
            self._sleep_time_seconds = sleep_time_milliseconds / 1000.0
        self._send_socket = send_socket
        self._commands = commands
        self._run = True
        self._run_course = False
        self._last_iteration_seconds = None
        self._waypoints = collections.deque()
        self._last_command = None

    def handle_message(self, message):
        """Handles command messages, e.g. 'start' or 'stop'."""
        # TODO: Process the message and stop using test data
        if 'command' not in message:
            print('No command in command message')
            return

        if message['command'] not in self._valid_commands:
            print(
                'Unknown command: "{command}"'.format(
                    command=message['command']
                )
            )
            return

        if message['command'] == 'start':
            self.run_course()
        elif message['command'] == 'stop':
            self.stop()


    @staticmethod
    def is_turn_left(our_bearing_d, goal_bearing_d):
        return True

    @staticmethod
    def relative_degrees(
        latitude_d_1,
        longitude_d_1,
        latitude_d_2,
        longitude_d_2
    ):
        """Computes the relative degrees from the first waypoint to the second,
        where north is 0.
        """
        relative_y_m = latitude_d_1 - latitude_d_2
        relative_x_m = longitude_d_1 - longitude_d_2
        degrees = math.degrees(math.atan(relative_y_m / relative_x_m))
        if relative_x_m > 0.0:
            if relative_y_m > 0.0:
                return 90.0 - degrees
            else:
                return 90.0 + degrees
        else:
            if relative_y_m > 0.0:
                return 270.0 + degrees
            else:
                return 180.0 + degrees

    @staticmethod
    def _generate_test_waypoints(position_d, meters, points_count):
        """Generates a generator of test waypoints originating from the current
        position.
        """
        m_per_d_longitude = Telemetry.latitude_to_m_per_d_longitude(position_d[0])

        step_d = 360.0 / points_count
        step_r = math.radians(step_d)

        step_m = (meters, 0.0)
        last_waypoint_d = (
            position_d[0] + step_m[1] / Telemetry.M_PER_D_LATITUDE,
            position_d[1] + step_m[0] / m_per_d_longitude
        )
        waypoints = collections.deque()
        for _ in range(4):
            waypoints.append(last_waypoint_d)
            step_m = Telemetry.rotate_radians(step_m, step_r)
            last_waypoint_d = (
                last_waypoint_d[0] + step_m[1] / Telemetry.M_PER_D_LATITUDE,
                last_waypoint_d[1] + step_m[0] / m_per_d_longitude
            )

        return waypoints

    def run(self):
        """Run in a thread, controls the RC car."""
        try:
            while self._run:

                while self._run and not self._run_course:
                    time.sleep(self._sleep_time_seconds)

                if not self._run:
                    return

                print('Running course iteration')

                telemetry = self._telemetry.get_data()
                position_d = (telemetry['latitude'], telemetry['longitude'])
                self._waypoints = self._generate_test_waypoints(
                    position_d,
                    5,
                    4
                )

                while self._run and self._run_course:
                    self._last_iteration_seconds = time.time()
                    self._run_course_iteration()
                    time.sleep(self._sleep_time_seconds)
                print('Stopping course')

        # For testing, I want stack dumps, so don't catch anything
        except ZeroDivisionError as exception:
        #except Exception as exception:
            print('Command thread had exception, ignoring: ' + str(exception))

    def _run_course_iteration(self):
        """Runs a single iteration of the course navigation loop."""
        speed = 0.25
        telemetry = self._telemetry.get_data()
        current_waypoint = self._waypoints[0]
        distance = Telemetry.distance_m(
            telemetry['latitude'],
            telemetry['longitude'],
            current_waypoint[0],
            current_waypoint[1]
        )
        if distance < 0.5:
            print('Reached ' + str(current_waypoint))
            self._waypoints.popleft()
            if len(self._waypoints) == 0:
                print('Stopping')
                self.send_command(0.0, 0.0)
            else:
                # I know I shouldn't use recursion here, but I'm lazy
                self._run_course_iteration()
            return

        degrees = self.relative_degrees(
            telemetry['latitude'],
            telemetry['longitude'],
            current_waypoint[0],
            current_waypoint[1]
        )

        if 'heading' not in telemetry:
            return
        heading_d = telemetry['heading']

        diff_d = abs(heading_d - degrees)
        if diff_d > 180.0:
            diff_d -= 180.0

        if diff_d < 10.0:
            self.send_command(speed, 0.0)
            return

        turn = min(diff_d / 20.0, 1.0)
        if Telemetry.is_turn_left(heading_d, degrees):
            turn = -turn
        self.send_command(speed, turn)

    def run_course(self):
        """Starts the RC car running the course."""
        self._run_course = True

    def stop(self):
        """Stops the RC car from running the course."""
        self.send_command(0.0, 0.0)
        self._run_course = False

    def kill(self):
        """Kills the thread."""
        self._run = False

    def send_command(self, throttle, turn):
        """Sends a command to the RC car. Throttle should be a float between
        -1.0 for reverse and 1.0 for forward. Turn should be a float between
        -1.0 for left and 1.0 for right.
        """
        assert -1.0 <= throttle <= 1.0
        assert -1.0 <= turn <= 1.0

        self._telemetry.process_drive_command(throttle, turn)

        throttle = int(throttle * 16.0 + 16.0)
        # Turning too sharply causes the servo to push harder than it can go,
        # so limit this
        turn = int(turn * 24.0 + 32.0)

        if self._last_command is not None:
            last_command = self._last_command
            if last_command[0] == throttle and last_command[1] == turn:
                return
        self._last_command = (throttle, turn)
        print(
            'throttle:{throttle} turn:{turn} time:{time}'.format(
                throttle=throttle,
                turn=turn,
                time=time.time()
            )
        )

        self._send_socket.send(command(throttle, turn))
