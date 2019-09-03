from .wrappers import SPIWrapper, GPIOWrapper


class TMC2130:

    spi_class = SPIWrapper
    gpio_class = GPIOWrapper

    driver_count = 0
    driver_pins = []
    last_driver_registers = []
    driver_registers = []

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
            *driver_pins: A dictionary for each stepper driver describing its pins. Many drivers can be controlled by one single TMC2130_ class, in which case the drivers are assumed to be wired in a SPI daisy chain configuration. The dictionary is defined thusly:
                
                ``step``
                    The STEP pin.
                ``dir``
                    The DIR pin. Optinal. If not specified, stepper direction will be controlled via SPI. This slows down operation when direction is changed often, so only use if no physical pins can be spared.
                ``DIAG0``
                    The DIAG0 pin. Optional. TODO describe what it is used for
                ``DIAG1``
                    The DIAG1 pin. Optional.
        """
        self.spi = self.spi_class(spi_bus, spi_device)

        self.driver_count = len(driver_pins)

        for driver in driver_pins:

            if type(driver) != dict:
                raise TypeError
            if "step" not in driver:
                raise ValueError

            self.driver_pins.append(driver)

            # initializing registers to power on defaults
            registers = self._get_default_registers()

            self.driver_registers.append(registers.copy())
            self.last_driver_registers.append(registers.copy())

    def commit(self):
        """Commits any settings that were changed after the last commit for all drivers, as in applies settings after they are changed."""

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

            self.spi.transfer(current_transmission)

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
