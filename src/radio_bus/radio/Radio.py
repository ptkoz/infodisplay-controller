import logging
from time import sleep
# pylint: disable=E0401,E0611
from serial import Serial  # type: ignore
# pylint: disable=E0401
from RPi import GPIO  # type: ignore
from .OutboundMessage import OutboundMessage


class Radio:
    """
    Class responsible for handling radio communication over HC-12 adapter available
    as UART device in the system.
    """

    def __init__(self, serial_device: str, gpio_service_pin: int):
        """
        :param str serial_device: A path to the serial device which represents HC-12 device
        :param int gpio_service_pin: A GPIO pit that connects to HC-12 service PIN
        """
        self.serial = Serial(serial_device, baudrate=4800, timeout=None)
        self.__gpio_service_pin = gpio_service_pin

    def setup_device(self) -> None:
        """
        Sets up the device before it can be used.
        """
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.__gpio_service_pin, GPIO.OUT)
        GPIO.output(self.__gpio_service_pin, GPIO.LOW)
        # entering config mode may last 40 milliseconds
        sleep(0.04)

        # flush buffers just in case
        self.serial.flushInput()
        self.serial.flushOutput()

        # Set the desired modes and log the output
        self.serial.write(b'AT+C003\r')
        logging.info('Radio setup: %s', self.serial.readline().decode().strip())
        self.serial.write(b'AT+FU3\r')
        logging.info('Radio setup: %s', self.serial.readline().decode().strip())
        self.serial.write(b'AT+P8\r')
        logging.info('Radio setup: %s', self.serial.readline().decode().strip())
        self.serial.write(b'AT+B4800\r')
        logging.info('Radio setup: %s', self.serial.readline().decode().strip())

        GPIO.output(17, GPIO.HIGH)

        # exiting config mode may last 80 milliseconds
        sleep(0.08)

        # again, flush the buffers just in case
        self.serial.flushInput()
        self.serial.flushOutput()

    def send(self, msg: OutboundMessage) -> None:
        """
        Sends given outbound message through radio
        """
        self.serial.write(msg.encoded_data)
