#!/usr/bin/env python
# Copyright (C) 2013 Fredrik Lindberg <fli@shapeshifter.se>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#
from optparse import OptionParser
import os
import sys
import signal
import math
import sets
from time import sleep
from datetime import datetime, timedelta, time
from LedStrip import *
from geoloc import Geoloc
from sun import Sun
import pytz
import tzlocal

pidfile = "/var/run/clock.pid"

words = {
    'it is' : { 'leds' : [3,4], 'text' : 'it is' },
    'half' : { 'leds' : [1,2], 'text': 'half' },
    'ten'  : { 'leds' : [0], 'text' : 'ten' },
    'a quarter' : { 'leds' : [5,6,7], 'text' : 'a quarter' },
    'twenty' : { 'leds' : [8,9], 'text' : 'twenty' },
    'five'   : { 'leds' : [13,14], 'text' : 'five', },
    'minutes' : { 'leds' : [11,12], 'text' : 'minutes', },
    'to' : { 'leds' : [10], 'text' : 'to', },
    'past' : { 'leds' : [15,16], 'text' : 'past', },
    'hour_one' : { 'leds' : [17], 'text' : 'one', },
    'hour_two' : { 'leds' : [18], 'text' : 'two', },
    'hour_three' : { 'leds' : [21], 'text' : 'three', },
    'hour_four' : { 'leds' : [20], 'text' : 'four', },
    'hour_five' : { 'leds' : [19], 'text' : 'five', },
    'hour_six' : { 'leds' : [22], 'text' : 'six', },
    'hour_seven' : { 'leds' : [23], 'text' : 'seven', },
    'hour_eight' : { 'leds' : [24], 'text' : 'eight', },
    'hour_nine' : { 'leds' : [28], 'text' : 'nine', },
    'hour_ten' : { 'leds' : [27], 'text' : 'ten', },
    'hour_eleven' : { 'leds' : [25,26], 'text' : 'eleven', },
    'hour_twelve' : { 'leds' : [29,30], 'text' : 'twelve', },
    'o clock' : { 'leds' : [31,32,33], 'text' : 'o\'clock', },
    'minute 1' : { 'leds' : [37], 'text' : '.', },
    'minute 2' : { 'leds' : [36], 'text' : '.', },
    'minute 3' : { 'leds' : [35], 'text' : '.', },
    'minute 4' : { 'leds' : [34], 'text' : '.', }
}

hours = {
    0 : [ words['hour_twelve'] ],
    1 : [ words['hour_one'] ],
    2 : [ words['hour_two'] ],
    3 : [ words['hour_three'] ],
    4 : [ words['hour_four'] ],
    5 : [ words['hour_five'] ],
    6 : [ words['hour_six'] ],
    7 : [ words['hour_seven'] ],
    8 : [ words['hour_eight'] ],
    9 : [ words['hour_nine'] ],
    10 : [ words['hour_ten'] ],
    11 : [ words['hour_eleven'] ],
    12 : [ words['hour_twelve'] ],
}

minutes = {
    0 : [ words['o clock'] ],
    5 : [ words['five'], words['minutes'], words['past'] ],
    10 : [ words['ten'], words['minutes'], words['past'] ],
    15 : [ words['a quarter'], words['past'] ],
    20 : [ words['twenty'], words['minutes'], words['past'] ],
    25 : [ words['twenty'], words['five'], words['minutes'], words['past'] ],
    30 : [ words['half'], words['past'] ],
    35 : [ words['twenty'], words['five'], words['minutes'], words['to'] ],
    40 : [ words['twenty'], words['minutes'], words['to'] ],
    45 : [ words['a quarter'], words['to'] ],
    50 : [ words['ten'], words['minutes'], words['to'] ],
    55 : [ words['five'], words['minutes'], words['to'] ],
}

# "Night time" between 21 and 7, lights are dimmed even more during
# this time.  The fadein/fadeout follows a bezier curve with a rapid
# fade out and a slow fade in.
night = [21, 7]

def fadeto(ledStrip, pixel, color, step):
    cur = ledStrip.getPixel(pixel)
    new = cur

    for i in range(0, 3):
        diff = color[i] - cur[i]
        tmp = abs(diff) if step[i] > abs(diff) else step[i]
        new[i] = cur[i] - tmp if diff <= 0 else cur[i] + tmp

    ledStrip.setPixel(pixel, new)
    return new == color

def fade(ledStrip, pixels, step):
    res = True
    for pixel in pixels:
        if not fadeto(ledStrip, pixel[0], pixel[1], step):
            res = False
    return res

def bezier(xys):
    n = len(xys)
    combinations = [1, 10, 45, 120, 210, 252, 210, 120, 45, 10, 1]
    def bezier(ts):
        result = []
        for t in ts:
            tpowers = (t**i for i in range(n))
            upowers = reversed([(1-t)**i for i in range(n)])
            coefs = [c*a*b for c, a, b in zip(combinations, tpowers, upowers)]
            result.append(
                tuple(sum([coef*p for coef, p in zip(coefs, ps)]) for ps in zip(*xys)))
        return result
    return bezier

def daemonize():
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("Could not fork: %s" % e.strerror)
        sys.exit(1)

    os.chdir("/")
    os.setsid()
    os.umask(0)

parser = OptionParser(usage="%prog [options]")
parser.add_option("-d", "--dry-run", dest="dryrun",
    default=False, action="store_true",
  help="Dry run/debug mode (no led output)")
(opts, args) = parser.parse_args()

if not opts.dryrun:
    daemonize()

running = True
def cleanup(sig, frame):
    global running
    running = False
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

if not opts.dryrun:
    pid = str(os.getpid())
    file(pidfile, 'w+').write("%s\n" % pid)
    ledStrip = LedStrip_WS2801("/dev/spidev0.0", 40)
else:
    ledStrip = LedStrip_Dummy(40)
ledStrip.update()

loc = Geoloc()
tz = tzlocal.get_localzone()
timezone = pytz.timezone(str(tz))

# Current brightness
is_night = False
is_night_time = False

prev_leds = []
while running:
    d = timezone.localize(datetime.now())
    utc = d.astimezone(pytz.utc)
    cur = d.timetuple()

    if loc.located():
        night_b = d.replace(hour=night[0], minute=0, second=0)
        night_e = d.replace(hour=night[1], minute=0, second=0)
        sun = Sun(lat=loc.lat, long=loc.lng)

        sunrise = sun.sunrise(utc)
        sunset = sun.sunset(utc)
        if d > sunrise:
            sunrise = sun.sunrise(utc + timedelta(days=1))
        else:
            sunset = sun.sunset(utc - timedelta(days=1))

        if d > night_e:
            night_e = night_e + timedelta(days=1)
        else:
            night_b = night_b - timedelta(days=1)

        is_night = sunset < d < sunrise
        night_length = sunrise - sunset

        is_night_time = night_b < d < night_e
        night_time_length = night_e - night_b


    def get_scaling_bezier(cur, begin, length, scale):
        ntl_m = length.seconds / 60.0
        cur_m = (cur - begin).seconds / 60
        ts = [t/ntl_m for t in range(int(ntl_m)+1)]
        # Bezier curve with a rapid increase and a slow decrease
        b = bezier([
            (-1,0),
            (-0.99, 1.20),
            (-0.98, 1),
            (-0.90, 1),
            (-0.5, 1),
            (-0.25, 1),
            (0, 1),
            (0.5, 1),
            (0.75, 1),
            (1, 1),
            (1, 0),
        ])
        points = b(ts)
        y = map(lambda p: p[1], points)
        return scale - (scale * y[cur_m]) + (1 - scale)

    def get_scaling_gauss(cur, begin, length, scale):
        halfway = (length / 2).seconds
        remain = halfway - (cur - begin).seconds
        prog = float(abs(remain)) / float(halfway)
        prog = prog * -1 if remain > 0 else prog * 1
        # Gaussian function over [-1, 1] with y max at ~1
        x = 0.365 * math.e - (math.pow(prog, 2) / 2 * math.pow(1.39, 2))
        return scale - (scale * (x)) + (1 - scale)

    brightness = 1.0
    if is_night:
        n_scale = get_scaling_gauss(d, sunset, night_length, 0.95)
        brightness = brightness * n_scale

    if is_night_time:
        nt_scale = get_scaling_bezier(d, night_b, night_time_length, 0.90)
        brightness = brightness * nt_scale

    min_5 = round(cur.tm_min / 5) * 5
    min_rest = int(cur.tm_min - min_5)
    hour = cur.tm_hour - 12 if cur.tm_hour > 12 else cur.tm_hour
    hour = (hour + 1) % 12 if min_5 > 30 else hour

    leds = [words['it is']] + minutes[min_5] + hours[hour]
    for i in range(0, min_rest):
        leds += [ words['minute ' + str(i+1)] ]

    cur = sets.Set(reduce(lambda x,y: x+y, map(lambda x: x['leds'], leds), []))
    prev = sets.Set(reduce(lambda x,y: x+y, \
        map(lambda x: x['leds'], prev_leds), []))

    # r,b,g
    color = [int(255 * brightness),\
        int(255 * brightness), int(255 * brightness)]

    if len(cur.difference(prev)) > 0:
        fadein = map(lambda x: [x, color], cur)
    else:
        fadein = []
    fadeout = map(lambda x: [x, [0, 0, 0]], prev.difference(cur))

    if len(fadein) > 0 and opts.dryrun:
        print " ".join(map(lambda x: x['text'] , leds))

    while running:
        res = {}
        res[0] = fade(ledStrip, fadein, [3, 3, 3])
        res[1] = fade(ledStrip, fadeout, [12, 12, 12])
        ledStrip.update()
        if res[0] and res[1]: break
        sleep(0.03);

    prev_leds = leds
    sleep(1)

ledStrip.setAll([0, 0, 0])
ledStrip.update()
ledStrip.close()
try:
    os.remove(pidfile)
except:
    ""
