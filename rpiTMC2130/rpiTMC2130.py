import warnings
import spidev
import RPi.GPIO as gpio
import serial


def generate_message(drivers, steps, max_speed, acceleration):
    message = b"S"
    for driver in range(drivers):
        message += steps[driver].to_bytes(4, byteorder="big", signed=True)
        message += max_speed[driver].to_bytes(2, byteorder="big")
        message += acceleration[driver].to_bytes(2, byteorder="big")
    message += b"E"
    return message


class ResetWarning(Warning):
    pass


class DriverError(Warning):
    pass


class TMC2130:
    def _get_default_registers(self):
        default_zero_registers = [
            0x00,
            0x10,
            0x11,
            0x13,
            0x14,
            0x15,
            0x2D,
            0x33,
            0x6C,
            0x6D,
            0x6E,
            0x72,
        ]  # a list of writeable registers that are zero at reset
        registers = {address: 0 for address in default_zero_registers}

        registers[0x60] = 0xAAAAB554  # TMC2130 datasheet page 30 & 79
        registers[0x61] = 0x4A9554AA
        registers[0x62] = 0x24492929
        registers[0x63] = 0x10104222
        registers[0x64] = 0xFBFFFFFF
        registers[0x65] = 0xB5BB777D
        registers[0x66] = 0x49295556
        registers[0x67] = 0x00404222
        registers[0x68] = 0xFFFF8056
        registers[0x69] = 0x00F70000
        registers[0x70] = 0x00050480  # TMC2130 datasheet page 31

        return registers

    def __init__(self, spi_bus, spi_device, *driver_pins):
        """Initializes the driver.

        Args:
            spi_bus: The SPI bus to use.
            spi_device: The SPI device to use.
            *driver_pins: A dictionary for each stepper driver describing its pins. The amount of dictionaries defines the number of drivers to control. This number has to be exactly the same as what is programmed into the arduino, otherwise the motors won't move. Many drivers can be controlled by one single TMC2130_ class, in which case the drivers are assumed to be wired in a SPI daisy chain configuration. The dictionary is defined thusly:
                
                ``DIAG0``
                    The DIAG0 pin. Optional. TODO describe what it is used for
                ``DIAG1``
                    The DIAG1 pin. Optional.

        Raises:
            DriverError: If a connection with the stepper drivers could not be established.
            SerialException: If the serial port for communicating with the arduino could not be opened.
        """
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.mode = 3
        self.spi.max_speed_hz = 1000000

        self.spi.xfer([0] * 5 * len(driver_pins))
        response = self.spi.xfer([0] * 5 * len(driver_pins))
        for i in range(len(driver_pins)):
            if not response[i * 5] & 1:
                warnings.warn(
                    "Driver appears to have been accessed since its last power on. You should run reset_registers to make sure all settings are synced.",
                    ResetWarning,
                )

        self.spi.xfer([0x01] * 5 * len(driver_pins))
        self.spi.xfer([0x01] * 5 * len(driver_pins))
        response = self.spi.xfer([0x01] * 5 * len(driver_pins))

        for i in range(len(driver_pins)):
            if response[i * 5] & 1:
                raise DriverError(
                    f"Could not establish an SPI connection driver {i} (zero indexed)."
                )

        self.sdd = serial.Serial("/dev/ttyS0", 115200)
        self.sdd.timeout = 60

        self.driver_count = len(driver_pins)
        self.driver_gpios = []
        self.last_driver_registers = []
        self.driver_registers = []

        for driver in driver_pins:

            if type(driver) != dict:
                raise TypeError

            self.driver_gpios.append(driver)  # TODO init gpios

            # initializing registers to power on defaults
            registers = self._get_default_registers()

            self.driver_registers.append(registers.copy())
            self.last_driver_registers.append(registers.copy())

    def commit(self):
        """Commits any register changes since last commit for all drivers."""

        driver_transmissions = [[] for _ in range(self.driver_count)]

        for driver in range(self.driver_count):
            for register, value in self.driver_registers[driver].items():
                if self.last_driver_registers[driver][register] == value:
                    continue

                driver_transmissions[driver].append(
                    [register + 0x80] + [value >> i & 0xFF for i in range(24, -8, -8)]
                )
                self.last_driver_registers[driver][register] = value

        transmission_count = max(
            [len(transmissions) for transmissions in driver_transmissions]
        )

        for i in range(transmission_count):
            current_transmission = []
            for driver in range(self.driver_count):
                current_transmission = (
                    driver_transmissions[driver][i]
                    if len(driver_transmissions[driver]) > i
                    else [0] * 5
                ) + current_transmission

            self.spi.xfer(current_transmission)

    def reset_registers(self, driver=0):
        """Resets registers of the specified driver to power on defaults.
        
        args:
            driver: The index of the driver to reset.
        """

        if not (0 <= driver < self.driver_count):
            raise IndexError(
                f"Driver {driver} does not exist. There are {self.driver_count} drivers."
            )

        self.driver_registers[driver] = self._get_default_registers()

    def _wait_for_sdd(self):
        response = self.sdd.read(1)
        if response != b"D":
            raise RuntimeError(f"Got invalid response from sdd: {response}")

    def step(self, steps):
        """Drives all motors a given amount of steps.

        Note that microstepping settings affect how much one step actually is. TODO recommend the function that factors in microstepping

        args:
            steps: An array with as many items as there are drivers with the number of steps to drive each motor by. If negative, drives the motor in the opposite direction.
        """

        if len(steps) != self.driver_count:
            raise ValueError("Steps array length does not match number of motors.")

        self.sdd.reset_input_buffer()
        self.sdd.write(
            generate_message(
                self.driver_count, steps, [2000, 2000, 2000], [2000, 2000, 2000]
            )
        )
        self._wait_for_sdd()
