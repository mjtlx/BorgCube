##########################
#
# BORG CUBE
#
##########################
#
# STEM camp 1-3 July 2022
#
##########################
#
# Murray Taylor
#
##########################

# PiicoDev Libs
from PiicoDev_Unified import sleep_ms # Cross-platform compatible sleep function
#from PiicoDev_RGB import PiicoDev_RGB, wheel   # RGB Leds
from PiicoDev_VL53L1X import PiicoDev_VL53L1X  # distance sensor
from PiicoDev_SSD1306 import *                 # OLED display
from PiicoDev_CAP1203 import PiicoDev_CAP1203  # touch sensor
# import glowbit                                 # Glowbit stick
import glowbit2                                 # Glowbit stick with new brightness command

# micropython libs
import _thread                                 # multi-core support
import random                                  # random fns
from machine import Pin, I2C, UART, Timer      # Access to the GPIO pins, and the base i2c system
import sys                                     # sys.exit()
import array

i2c = I2C(id=0)      # PiicoDev chain on i2c channel 0
#
# Power on self test
#
connected = i2c.scan()  # whats connected
                            # 8. == RGB Leds
                            # 40. == Capacitive touch sensor
                            # 41. == Laser ranger
                            # 60. == OLED display

#
# setup the 'programming' pins
# default 1, if grounded is 0
#
# allow up to 2 grounded (using jumpers from Ground in phys pin 3 and/or phys pin 8
#
#   P2  P3  P4  P5
#    1   1   1   1    normal operation
#    0   x   x   x    No Glowbit
#    x   0   x   x    No Neopixels (TBD)
#    x   x   0   x    No 3watt LEDs
#
P2 = Pin(2, Pin.IN, Pin.PULL_UP)     
P3 = Pin(3, Pin.IN, Pin.PULL_UP)
P4 = Pin(4, Pin.IN, Pin.PULL_UP)
P5 = Pin(5, Pin.IN, Pin.PULL_UP)

n_sticks = 4
stickLEDS = n_sticks * 8    # number of sticks * 8
neoLEDS = 30                # neopixel string  s/b 50 
led3wLEDS = 4               # 3 watt leds

####################################
#
# UART and Sound FX setup
#
uart = UART(0, baudrate=115200, tx=Pin(12), rx=Pin(13))
#initialise MP3 player
uart.write("AT\r\n")               # wakeup
sleep_ms(100)
uart.write("AT+AMP=ON\r\n")        # useful for testing w/o external amp
sleep_ms(100)                      #  - just connect a speaker
uart.write("AT+PLAYMODE=3\r\n")    # single track and stop
sleep_ms(100)
uart.write("AT+VOL=5\r\n")    # single track and stop
sleep_ms(100)

# Audio track durations - run time + 1 second
# track no       1   2  3  4  5  6  7      there is NO track 0
durations = [0, 17, 10, 2, 2, 6, 2, 3 ]

####################################
# define PiicoDev objects
if P5.value() == 1:  # using PiicoDev Ldistance sensor
    distSensor = PiicoDev_VL53L1X()                # initialise distance sensor
touchSensor = PiicoDev_CAP1203(sensitivity=6)  # initialize touch sensor (poss adj sensitiyity 0 = most sensitive, 7 = lowest)
display = create_PiicoDev_SSD1306()

####################################
# GlowBit objects
default_rate = 40
default_brightness = 20

if P2.value() == 1:
    stick = glowbit2.stick(numLEDs = stickLEDS, rateLimitFPS=default_rate)   # default pin=18, sm=0
if P3.value() == 1:
    neo   = glowbit2.stick(numLEDs = neoLEDS,   rateLimitFPS=default_rate, pin=19, sm=2)
    neo.pixelsFill(0); neo.pixelsShow()
if P4.value() == 1:
    led3w = glowbit2.stick(numLEDs = led3wLEDS, rateLimitFPS=default_rate, pin=20, sm=4)
    led3w.pixelsFill(0); sleep_ms(200); led3w.pixelsShow()

#
# cross-core link variable
#
g_alert = False    # True if glowbits running
g_timer = False    # true if timer running
g_stop = False

# odd variable
counter = 0
rand = 0
rand2 = 0

#
# POST
#
def post():
    if P2.value() == 1:
        stick.updateRateLimitFPS(20)
        stick.rainbowDemo(2); stick.pixelsFill(0); stick.pixelsShow()   # works ;-)
        stick.updateRateLimitFPS(default_rate)
    sleep_ms(3000)

#
# timer reset
#
def timerdone(t):     #  t is required arg in def statement
    global g_timer
    g_timer = False   # allow another Borg message

tim = Timer(-1,mode=Timer.ONE_SHOT, period=10, callback=timerdone)

#
# CORE 0 process
#
def main_thread():
    global g_alert, g_timer, counter, rand, rand2
   
    if P5.value() == 1:
        dist = distSensor.read() # read the distance in millimetres
    else:
        dist = 3000
        
    touch = touchSensor.read()
    counter += 1
    if counter == 100:
        rand = random.randint(0,15)
        counter = 0
    rand2 = random.randint(0,15)
    
    display.fill(0)
    display.text("distance: ", 0,15,1)
    display.text(str(dist), 80,15,1)
    display.text("touch   : ", 0,30,1)
    display.text(str(touch[1]), 80,30,1)
    display.text(str(touch[2]), 90,30,1)
    display.text(str(touch[3]), 100,30,1)
    display.show()
    
    # distance sensor range 0 - 4000 mm (nominal)
    # 0 ---1000---1500---2000---2500---3000----inf
    if dist < 1000:
        mode(1); level = 1
    elif dist < 1500 :
        mode(2); level = 2
    elif dist < 2000:
        mode(3); level = 3
    elif dist < 2500:
        mode(4); level = 4
    elif dist < 3000:
        mode(5); level = 5
    else:
        mode(6); level = 6

    if touch[1] == 1:
        if g_alert == False:
            g_alert = True
            _thread.start_new_thread(pulse_thread, (2,))  # chaos flash Glowbits
    elif touch[2] == 1:
        if g_timer == False:
            g_timer = True
            play = random.randint(1,7)          # pick a track
                                                # build the play command
            c_num = "% s" % play                #   /  itoa()
            s = "AT+PLAYNUM=" + c_num + "\r\n"  #  /   concatenate
            uart.write(s)                       # /    and send it
            # one shot firing after durations[play] seconds to allow MP3 player to finish
            tim.init(mode=Timer.ONE_SHOT, period=durations[play]*1000, callback=timerdone)
    elif touch[3] == 1:
        if g_alert == False:
            g_alert = True
            _thread.start_new_thread(pulse_thread, (3,)) #(random.randint(2,3),))  # rainbow sweep Glowbits
#    else:

#
# mode scripts
# mode(1) <1000mm
# mode(2) <1500mm
# mode(3) <2000mm
# mode(4) <2500mm
# mode(5) <3000mm
# mode(6) >3000mm
#
def mode(level):
    global g_stop
    if level == 1:
        g_stop = False
        # they are really close < 1000mm
        if P4.value() == 1:
            led3w_cycle1()
        if P3.value() == 1:
            neo_idle(255)
    elif level == 2:
        g_stop = False
        # closer < 1500mm
        if P2.value() == 1:
            stick_two()
        if P3.value() == 1:
            neo_idle(127)
        if P4.value() == 1:
            led3w_cycle2()
        if P2.value() == 0 and P3.value() == 0 and P4.value() == 0:
            pass
    elif level == 3:
        # < 2000mm range
        g_stop = False
        if P2.value() == 1:
            stick_idle(level,100)
        if P3.value() == 1:
            neo_idle(127)
        if P4.value() == 1:
            led3w_idle(50)
            led3w_once = True
    elif level == 4:
        # <  2500mm range
        g_stop = False
        if P2.value() == 1:
            stick_idle(level,100)
        if P3.value() == 1:
            neo_idle(50)
        if P4.value() == 1:
            led3w_idle()
            led3w_once = True
        g_timer = False     #force reset
    elif level == 5:
        # < 3000mm
        g_stop = False
        if P2.value() == 1:
            stick_idle(level,50)
        if P3.value() == 1:
            neo_idle()
        if P4.value() == 1:
            led3w_off()
            led3w_once = True
        g_timer = False     #force reset
    elif level == 6:
        # > 3000mm range
        g_stop = True
        if P2.value() == 1:
            stick_idle()   # uses default_brightness
        if P3.value() == 1:
            neo_idle()
        if P4.value() == 1:
            led3w_off()
            led3w_once = True
        g_timer = False     #force reset
    else:
        # default same as level 6
 #   global g_alert
        g_stop = True
        if P2.value() == 1:
            stick_idle()   # uses default_brightness
        if P3.value() == 1:
            neo_idle()
        if P4.value() == 1:
            led3w_off()
            led3w_once = True
        g_timer = False     #force reset

        
###################################
#
# STICK MODES
#
###################################
# "static" variables
stick_idle_counter = 0
stick_ar = array.array("I", [0 for _ in range(stickLEDS)])

def update_stick():
    global stick_ar
    for j in range(int(len(stick_ar))):
        stick.pixelSet(j, stick_ar[j])
    stick.pixelsShow()
        
def stick_two():
    global g_alert
    if g_alert == False:
        g_alert = True
        _thread.start_new_thread(pulse_thread, (1,))   # pulse sweep Glowbits

def stick_idle(mm=6, bb=default_brightness):
    global rand, stick_idle_counter, stick_ar
    global g_alert
    if g_alert == True:
        return
    stick.updateBrightness(bb)
    stick_idle_counter += 1
    if stick_idle_counter == 100:
        stick_rand_string(rand)
        stick_idle_counter = 0
    if mm == 5:
        stick_ar[0] = stick.white()
        stick_ar[1] = stick.black()
    elif mm == 4:
        stick_ar[0] = stick.white()
        stick_ar[1] = stick.white()
        stick_ar[2] = stick.black()
    elif mm == 3:
        stick_ar[0] = stick.white()
        stick_ar[1] = stick.white()
        stick_ar[2] = stick.white()
        stick_ar[3] = stick.white()
    
    update_stick()
        
        

###################################
#
# NEOSTRING MODES
#
###################################
# "static" variables
neo_idle_counter = 0
neo_ar = array.array("I", [0 for _ in range(neoLEDS)])

def update_neo():
    global neo_ar
    for j in range(int(len(neo_ar))):
        neo.pixelSet(j, neo_ar[j])
    neo.pixelsShow()

def neo_off():
    global neo_ar
    for j in range(int(len(neo_ar))):
        neo_ar[j] = neo.black()
    update_neo()

def neo_idle(bb=default_brightness):
    global rand, neo_idle_counter, stick_ar
    global g_alert, g_stop
    if g_alert == True or g_stop == True:
        return
    neo.updateBrightness(bb)
    neo_idle_counter += 1
    if neo_idle_counter == 255:
        neo_rand_string(rand)
        neo_idle_counter = 0

    update_neo()


###################################
#
# led3wLED MODES
#
###################################
# "static" variables
led3w_idle_counter = 0
led3w_cycle_value = 0x000000
led3w_cycle_direction = 1
led3w_once = True
led3w_ar = array.array("I", [0 for _ in range(led3wLEDS)])

def update_led3w():
    global led3w_ar
    for j in range(int(len(led3w_ar))):
        led3w.pixelSet(j, led3w_ar[j])
    led3w.pixelsShow()

def led3w_off():
    global led3w_ar
    for j in range(int(len(led3w_ar))):
        led3w_ar[j] = led3w.black()
    update_led3w()

def led3w_idle(bb=default_brightness):
    global rand, led3w_idle_counter, led3w_ar
    global g_alert, g_stop
    if g_alert == True or g_stop == True:
        return
    led3w.updateBrightness(bb)
    led3w_idle_counter += 1
    if led3w_idle_counter == 42:
        led3w_rand_string(rand)
        led3w_idle_counter = 0
    update_led3w()

def led3w_cycle1():
    global led3w_ar, led3w_cycle_value, led3w_cycle_direction
    led3w.updateBrightness(1.0)
    for j in range(int(len(led3w_ar))):
        led3w_ar[j] &= 0xFF0000   # turn off Green and Blue
    led3w_cycle_value += (0x030000 * led3w_cycle_direction)
    for j in range(int(len(led3w_ar))):
        led3w_ar[j] = led3w_cycle_value
    if led3w_cycle_value > 0x800000:
        led3w_cycle_direction = -1
    elif led3w_cycle_value < 0x0F0000:
        led3w_cycle_direction = 1
    update_led3w()

def led3w_cycle2():
    global led3w_ar, led3w_cycle_value, led3w_cycle_direction, led3w_once
    led3w.updateBrightness(100)
    if led3w_once:
        for j in range(int(len(led3w_ar))):
            led3w_ar[j] = led3w.black()
        once = False
    led3w_cycle_value += (0x030303 * led3w_cycle_direction)
    for j in range(int(len(led3w_ar))):
        led3w_ar[j] = led3w_cycle_value
    if led3w_cycle_value > 0xEFEFEF:
        led3w_cycle_direction = -1
    elif led3w_cycle_value < 0x0F0F0F:
        led3w_cycle_direction = 1
    update_led3w()

#
# CORE 1 process
# - started as needed by CORE 0 process
# - runs once and exits
#
def pulse_thread(id):
    global g_alert, rand2

    if id == 1:
        stick.updateRateLimitFPS(80)
        stick.updateBrightness(1.0)
        stick.pulseDemo(); stick.pixelsFill(0); stick.pixelsShow()
        stick.updateRateLimitFPS(default_rate)
        stick.updateBrightness(default_brightness)
    elif id == 2:
        stick.updateRateLimitFPS(default_rate)
        stick.updateBrightness(1.0)
        stick.chaos()
        stick.updateBrightness(default_brightness)
    elif id == 3:
        stick.updateRateLimitFPS(default_rate)
        stick.rainbowDemo(2); stick.pixelsFill(0); stick.pixelsShow()
    else:
        # bad id - do nothing
        g_alert = False
    # cleanup and exit thread
    g_alert = False
    return

def rotate_colours():
 # this will step through a selection of colours and return the next in sequence
 # for the rand_string fn to use
    black = 0x000000
    red = 0xFF0000 
    blue = 0x0000FF
    green = 0x00FF00
    # secondaries
    yellow_s = 0xFFFF00
    magenta_s = 0xFF00FF
    cyan_s = 0x00FFFF
    #proportions
    magenta = 0xFF0077   # 2R:1B
    violet = 0xFF00FF    # 1R:1B
    purple = 0x7700FF    # 1R:2B
    teal = 0x7777FF      # 1Y:2B
    chartreuse = 0x33FF77  # 2Y:1B

    colours = [black, red, green, blue, yellow_s, magenta_s, cyan_s, magenta, violet, purple, teal, chartreuse, ]
# this selects from specific set defined above
    return colours[random.randint(0, (len(colours)-1))]

# this just picks a random colour
# optionally limited to a subset of possibles
def stick_random_colour(ss=0):
    if ss == 0:     # default any colour
        colour = stick.wheel(random.randint(0,255))
    elif ss == 1:   ## blue-green limited for neoLEDS
        colour = stick.wheel(random.randint(55,190))
    else:            # default - anything else
        colour = stick.wheel(random.randint(0,255))
    
    if random.randint(0,63) == 42:   # occasionally set it black
        colour = stick.black()
    print("stick_random_colour is ", hex(colour))
    return colour

# this just picks a random colour
# optionally limited to a subset of possibles
def neo_random_colour(ss=0):
    if ss == 0:     # default any colour
        colour = neo.wheel(random.randint(0,255))
    elif ss == 1:   ## blue-green limited for neoLEDS
        colour = neo.wheel(random.randint(55,190))
    else:            # default - anything else
        colour = neo.wheel(random.randint(0,255))
    
    if random.randint(0,63) == 42:   # occasionally set it black
        colour = neo.black()
#    print("neo_random_colour is ", hex(colour))
    return colour

# this just picks a random colour
# optionally limited to a subset of possibles
def led3w_random_colour(ss=0):
    if ss == 0:     # default any colour
        colour = led3w.wheel(random.randint(0,255))
    elif ss == 1:   ## blue-green limited for neoLEDS
        colour = led3w.wheel(random.randint(55,190))
    else:            # default - anything else
        colour = led3w.wheel(random.randint(0,255))
    
    if random.randint(0,63) == 42:   # occasionally set it black
        colour = led3w.black()
##    print("led3w_random_colour is ", hex(colour))
    return colour

# use this as one of possibles for stasis box to slowly change colour of neopixel string
# variation would be to offset every led by wheel value+1 or +2
slowcount=0
def slowroll():
    global slowcount
    stick.pixelsFill(stick.wheel(slowcount))
    stick.pixelsShow()
    slowcount += 2
    if slowcount >= 255:
        slowcount = 0

def stick_slowroll2():
    global slowcount, rand2
    for i in range(stickLEDS-1, -1, -1):
        stick.pixelSet(i+1, stick.getPixel(i))
    stick.pixelSet(0,stick.wheel(slowcount))
    stick.pixelsShow()
    slowcount += 5
    if (rand2 % 5 ) == 0:
       stick_flash2()
    elif rand2 == 13:
       stick_flash_restore()
    if slowcount >= 255:
        slowcount = 0

#
# flash whole stick
#
def stick_flash_restore():
    save = []
    for i in range(0,stickLEDS):
        save.append(stick.getPixel(i))   #save the current colours
    stick.pixelsFill(0)                  # blank the LEDS
    stick.updateBrightness(1.0)          # set to max brightness
    stick.pixelSet(0, stick.white())     # set the zero'th pixel to white
    stick.pixelsShow()                   # turn it on !
    sleep_ms(100)                        # for a 1/10th second
    stick.pixelsFill(0)                  # blank the LEDS
    stick.pixelSet(stickLEDS-1, stick.white())  # set the last pixel to white
    stick.pixelsShow()                   # turn it on !
    sleep_ms(100)                        # for a 1/10th second
    stick.pixelsFill(stick.white())      # set ALL pixels to white
    stick.pixelsShow()                   # turn them on !
    sleep_ms(100)                        # for a 1/10th second
    stick.updateBrightness(default_brightness)  # reset the brightness
    for i in range(0,stickLEDS):
        stick.pixelSet(i, save[i])       # restore the saved colours
    stick.pixelsShow()                   # turn them back on !
    del save                             # cleanup

#
# flash random pixel
#
def stick_flash2():
    save = []
    i = random.randint(0,stickLEDS-1)
    save.append(stick.getPixel(i))
    stick.pixelSet(i, stick.white())
    stick.pixelsShow()
    sleep_ms(100)
    stick.pixelSet(i, stick.black())
    stick.pixelsShow()
    sleep_ms(100)
    stick.pixelSet(i, stick.white())
    stick.pixelsShow()
    sleep_ms(100)
    stick.pixelSet(i, save[0])
    stick.pixelsShow()
    del save

#
# this fn loads the stick_ar array, but does NOT update the actual LEDS
#
def stick_rand_string(n):
    global stick_ar
    new_colour = rotate_colours()
    if n == 0:              # all same
        for j in range(int(len(stick_ar))):
            stick_ar[j] = new_colour
    elif (n % 2) == 0:      # div by 2
        for j in range(int(len(stick_ar))):
            if (j % 2) == 0:
                stick_ar[j] = new_colour
    elif (n % 3) == 0:      # div by 3
        for j in range(int(len(stick_ar))):
            if (j % 3) == 0:
                stick_ar[j] = new_colour
    elif (n % 4) == 0:      # div by 5
        for j in range(int(len(stick_ar))):
            if (j % 4) == 0:
                stick_ar[j] = new_colour
    elif n in {1,7,11,13}:  # prime numbers not otherwise handled ;-(
        for j in range(int(len(stick_ar))):
            if (j % 2) == 0:
                stick_ar[n % (j+1)] = new_colour

#
# this fn loads the neo_ar array, but does NOT update the actual LEDS
#
def neo_rand_string(n):
    global neo_ar
    new_colour = neo_random_colour(1)   # pick a random blur-green colour
    if n == 0:              # all same
        for j in range(int(len(neo_ar))):
            neo_ar[j] = new_colour
    elif (n % 2) == 0:      # div by 2
        for j in range(int(len(neo_ar))):
            if (j % 2) == 0:
                neo_ar[j] = new_colour
    elif (n % 3) == 0:      # div by 3
        for j in range(int(len(neo_ar))):
            if (j % 3) == 0:
                neo_ar[j] = new_colour
    elif (n % 4) == 0:      # div by 5
        for j in range(int(len(neo_ar))):
            if (j % 4) == 0:
                neo_ar[j] = new_colour
    elif n in {1,7,11,13}:  # prime numbers not otherwise handled ;-(
        for j in range(int(len(neo_ar))):
            if (j % 2) == 0:
                neo_ar[n % (j+1)] = new_colour

########
#
# this fn loads the led3w_ar array, but does NOT update the actual LEDS
#
def led3w_rand_string(n):
    global led3w_ar
    new_colour = led3w_random_colour(1)   # pick a random blur-green colour
    if n == 0:              # all same
        for j in range(int(len(led3w_ar))):
            led3w_ar[j] = new_colour
    elif (n % 2) == 0:      # div by 2
            led3w_ar[0] = new_colour
    elif (n % 3) == 0:      # div by 3
            led3w_ar[1] = new_colour
    elif (n % 4) == 0:      # div by 5
            led3w_ar[2] = new_colour
    elif n in {1,7,11,13}:  # prime numbers not otherwise handled ;-(
            led3w_ar[3] = new_colour


#####################################
#####################################
##  START HERE
#####################################
#####################################
#
# POST
#
print("running post ...")
display.text("running POST", 0,30,1)
display.show()
post()
print("glowbit P2.value() = ",P2.value())
print("neo     P3.value() = ",P3.value())
print("led3w   P4.value() = ",P4.value())

display.fill(0)
display.text("glowbit = ", 0,0,1)
display.text(str(P2.value()),80,0,1)
display.text("neo     = ", 0,15,1)
display.text(str(P3.value()),80,15,1)
display.text("led3w   = ", 0,30,1)
display.text(str(P4.value()),80,30,1)
display.show()

##neo.pixelsFill(neo.red()); neo.pixelsShow()
##sleep_ms(1000)
##neo.pixelsFill(neo.green()); neo.pixelsShow()
##sleep_ms(1000)
##neo.pixelsFill(neo.blue()); neo.pixelsShow()
##sleep_ms(1000)
##neo.pixelsFill(0); neo.pixelsShow()

#
# Launch Core 0 process
#
print("Launch!")
if P2.value() == 1:
    stick.pixelsFill(0); stick.pixelsShow()
if P3.value() == 1:
    neo.pixelsFill(0); sleep_ms(200); neo.pixelsShow()
if P4.value() == 1:
    led3w.pixelsFill(0); sleep_ms(200); led3w.pixelsShow()

sleep_ms(2000)

while True:
    main_thread()
