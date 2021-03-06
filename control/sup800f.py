"""Functions for communicating with the SUP800F GPS module."""
import collections
import functools
import struct


HEADER_FORMAT = ''.join((
    '!',  # network format (big-endian)
    'BB',  # start of sequence, A0 A1
    'H',  # payload length
))
TAIL_FORMAT = ''.join((
    '!',  # network format (big-endian)
    'B',  # checksum
    'BB',  # end of sequence, 0D 0A
))
MODE_FORMAT = ''.join((
    '!',  # network format (big-endian)
    'B',  # message id, 9 = configure message type
    'B',  # none = 0, NMEA = 1, binary = 2
    'B',  # 0 = SRAM, 1 = SRAM and Flash
))
# I'm not sure why, but the module is returning an extra byte for some
# reason. It's even reporting the payload as one byte too long, so just
# cut an extra byte off.
BINARY_FORMAT = ''.join((
    '!',  # network format (big-endian)
    'xxxx', # The message will have 4 header bytes
    'x',  # message id
    'x',  # message sub id
    'x',  # see above comment
    'f',  # acceleration X
    'f',  # acceleration Y
    'f',  # acceleration Z
    'f',  # magnetic X
    'f',  # magnetic Y
    'f',  # magnetic Z
    'I',  # pressure
    'f',  # temperature
    'xxx', # and 3 checksum bytes
))
BinaryMessage = collections.namedtuple(  # pylint: disable=invalid-name
    'BinaryMessage',
    ' '.join((
        'acceleration_g_x', 'acceleration_g_y', 'acceleration_g_z',
        'magnetic_flux_ut_x', 'magnetic_flux_ut_y', 'magnetic_flux_ut_z',
        'pressure_p',
        'temperature_c',
    ))
)



def format_message(payload):
    """Formats a message for the SUP800F."""
    checksum = functools.reduce(lambda a, b: a ^ b, payload, 0)
    return (
        struct.pack(HEADER_FORMAT, 0xA0, 0xA1, len(payload))
        + payload
        + struct.pack(TAIL_FORMAT, checksum, 0x0D, 0x0A)
    )


def get_message(ser, timeout_bytes=None):
    """Returns a single message."""
    # Keep consuming bytes until we see the header message
    if timeout_bytes is None:
        timeout_bytes = 10000000
    skipped_bytes = 0
    while True:
        if skipped_bytes > timeout_bytes:
            raise ValueError('No binary header found')

        part = ser.read(1)
        skipped_bytes += 1
        if part != b'\xA0':
            continue

        part = ser.read(1)
        skipped_bytes += 1
        if part != b'\xA1':
            continue

        part = ser.read(2)
        skipped_bytes += 2

        payload_length = struct.unpack('!H', part)[0]
        rest = ser.read(payload_length + 3)
        skipped_bytes += payload_length + 3

        if rest[-2:] != b'\r\n':
            print(r"Message didn't end in \r\n")
        return b'\xA0\xA1' + struct.pack('!H', payload_length) + rest


def parse_binary(binary_message):
    """Parses a binary message (temperature, accelerometer, magnetometer, and
    pressure) from the SUP800F module.
    """
    # TODO: I guess the SUP800F also returns navigation data messages? Ignore
    # them for now, but this shouldn't be called
    if binary_message[4] == 0xA8:
        return None
    if binary_message[4] != 0xCF:
        raise EnvironmentError('Invalid id while parsing binary message')
    return BinaryMessage(*struct.unpack(BINARY_FORMAT, binary_message))


def switch_to_nmea_mode(ser):
    """Switches to the NMEA message mode."""
    _change_mode(ser, 1)


def switch_to_binary_mode(ser):
    """Switches to the binary message mode."""
    _change_mode(ser, 2)


def _change_mode(ser, mode):
    """Change reporting mode between NMEA messages or binary (temperature,
    accelerometer and magnetometer) mode.
    """
    for _ in range(3):
        mode_message = struct.pack(MODE_FORMAT, 9, mode, 0)
        ser.write(format_message(mode_message))
        ser.flush()
        if check_response(ser, limit=10):
            return
        self._logger.warn('No response to mode change seen, trying again')
    raise EnvironmentError('Mode change to {} denied'.format(mode))


def check_response(ser, limit=None):
    """Checks for an ack/nack response."""
    response_format = ''.join((
        '!',  # network format (big-endian)
        'xx', # The message will have 2 header bytes
        'H',  # payload length
        'B',  # message id
        'B',  # ack id
        'xxx', # and 3 checksum bytes
    ))

    count = 0
    def check():  # pylint: disable=missing-docstring
        if limit is None:
            return True
        else:
            nonlocal count
            count += 1
            return count <= limit

    while check():
        data = get_message(ser)
        try:
            length, message_id, _ack_id = ( # pylint: disable=unused-variable
                struct.unpack(response_format, data)
            )
        except:  # pylint: disable=bare-except
            continue
        if message_id not in (0x83, 0x84):
            continue
        if message_id == 0x83:
            return True
        else:
            return False
    raise EnvironmentError('No response messages seen')
