# Home Climate Controller

A controlling unit for Air Conditioning management solution I've built around my mobile air conditioner. This uses
RaspberryPI hardware (any model will do) with HC-12 module plugged in through GPIO.

## Features

* Collects measures from [Remote Sensors](https://github.com/pamelus/air-conditioning-sensor) (Serial communication over
  HC-12 433Mhz radio bridge).
* Allows configuring desired indoor temperature.
* Sends on / off commands to the [Air Conditioning Unit](https://github.com/pamelus/air-conditioning-unit) to maintain
  configured indoor temperature.
* Exposes data through websockets for [Home Climate Information Display](https://github.com/ptkoz/infodisplay-ui)
