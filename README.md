# BorgCube
Borg Cube effects system for STEM camp

A Raspberry Pico used as controller for animating a Borg Cube used in a STEM camp at a 'search and rescue' activity base.

Laser rangefinder - capacitive touch sensors - Pixel arrays - MP3 Player


The glowbit2.py file is an updated library based on the original glowbit.py library by Core Electronics
It includes a new function updateBrightness() (created by Brenton - Core Electronics team) that allows changing the brightness setting of the Glowbit modules that is normally set by the initialisation command.
There is also a fix by myself to the rainbowDemo() function. Removed a hardcoded value and replaced it with the value self.numLEDs .
