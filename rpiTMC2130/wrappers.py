import spidev
import RPi.GPIO as gpio


class GPIOModeError(Exception):
    pass


class SPIWrapper:
    def __init__(self, bus, device):
        """Initializes the SPI device.

        args:
            bus: The SPI bus to use.
            device: The SPI device to use.
        """

        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.mode = 3
        self.spi.max_speed_hz = 1000000

    def transfer(self, bytes_list):
        """Preforms an SPI transaction.

        args:
            bytes_list: A list of the bytes to send to the SPI device. 

        returns:
            A list of bytes recieved from the SPI device.
        """
        return self.spi.xfer(bytes_list)


class GPIOWrapper:
    # pylint: disable=no-member

    def __init__(self, pin, output=True):
        """Initializes a GPIO pin.

        args:
            pin: The GPIO pin to bind to.
            output: ``True`` if this pin is an output, ``False`` if it is an input.
        """

        self.pin = pin
        self.output = output

        gpio.setmode(gpio.BOARD)
        if output:
            gpio.setup(self.pin, gpio.OUT)
        else:
            gpio.setup(self.pin, gpio.IN)

    def write(self, bit):
        """Writes a bit to the GPIO pin.

        Only works for output GPIO pins.

        args:
            bit: The bit to write.

        raises:
            GPIOModeError: If this method is accessed when the pin is in input mode.
        """

        if not self.output:
            raise GPIOModeError("This method only works for a GPIO pin in output mode.")

        gpio.output(self.pin, bit)

    def read(self):
        """Reads a bit from the GPIO pin.

        Only works for input GPIO pins.

        returns:
            The state of the GPIO pin.

        raises:
            GPIOModeError: If this method is accessed when the pin is in output mode.
        """

        if self.output:
            raise GPIOModeError("This method only works for a GPIO pin in input mode.")

        return gpio.input(self.pin)
