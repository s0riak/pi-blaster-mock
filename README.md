# pi-blaster-mock
## Introduction
This is a very simple mock for pi-blaster (https://github.com/sarfata/pi-blaster).

pi-blaster-mock can be used while developing applications based on pi-blaster, to see the results pi-blaster would send to an LED in a very basic UI.

pi-blaster-mock is written in python and uses TK to display the rgb colors, which would be set by pi-blaster, in a simple TK window:

![UI of pi-blaster-mock](https://raw.githubusercontent.com/s0riak/pi-blaster-mock/master/pi-blaster-mock.png)


## Usage
To start pi-blaster-mock execute:

    sudo python3 pi-blaster-mock

pi-blaster-mock requires 'sudo' to acquire the fifo-device at /dev/pi-blaster.
The device is created if non-existent and removed on exit.

It's currently only tested on Ubuntu 15.10.
