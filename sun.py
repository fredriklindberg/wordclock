#
#    Calculate sunrise and sunset based on equations from NOAA
#    http://www.srrb.noaa.gov/highlights/sunrise/calcdetails.html
#
# Based upon code from
# http://michelanders.blogspot.se/2010/12/calulating-sunrise-and-sunset-in-python.html
#
from math import cos,sin,acos,asin,tan
from math import degrees as deg, radians as rad
from datetime import date,datetime,time
import pytz
import tzlocal

class Sun:
    def __init__(self, lat, long):
        self.lat=lat
        self.long=long

    def sunrise(self, day=datetime.utcnow(), tz=None):
        if tz == None:
            tz = tzlocal.get_localzone()
        timezone = pytz.timezone(str(tz))

        self.when = day
        self.__calc()

        time = self.sunrise_t
        utc = pytz.utc
        sunrise_utc = utc.localize(datetime(year=day.year, month=day.month,
            day=day.day, hour=time.hour, minute=time.minute,
            second=time.second))

        return sunrise_utc.astimezone(timezone)

    def sunset(self, day=datetime.utcnow(), tz=None):
        if tz == None:
            tz = tzlocal.get_localzone()
        timezone = pytz.timezone(str(tz))

        self.when = day
        self.__calc()

        time = self.sunset_t
        utc = pytz.utc
        sunset_utc = utc.localize(datetime(year=day.year, month=day.month,
            day=day.day, hour=time.hour, minute=time.minute,
            second=time.second))

        return sunset_utc.astimezone(timezone)

    def solarnoon(self, day=datetime.utcnow(), tz=None):
        if tz == None:
            tz = tzlocal.get_localzone()
        timezone = pytz.timezone(str(tz))

        self.when = day
        self.__calc()

        time = self.solarnoon_t
        utc = pytz.utc
        solarnoon_utc = utc.localize(datetime(year=day.year, month=day.month,
            day=day.day, hour=time.hour, minute=time.minute,
            second=time.second))

        return solarnoon_utc.astimezone(timezone)

    def __calc(self):
        """
        Perform the actual calculations for sunrise, sunset and
        a number of related quantities.

        The results are stored in the instance variables
        sunrise_t, sunset_t and solarnoon_t
        """

        when = self.when

        # datetime days are numbered in the Gregorian calendar
        # while the calculations from NOAA are distibuted as
        # OpenOffice spreadsheets with days numbered from
        # 1/1/1900. The difference are those numbers taken for
        # 18/12/2010
        day = when.toordinal() - (734124 - 40529)
        t = when.time()
        time = (t.hour + t.minute/60.0 + t.second/3600.0)/24.0

        longitude = self.long     # in decimal degrees, east is positive
        latitude = self.lat       # in decimal degrees, north is positive

        Jday = day + 2415018.5 + time/24 # Julian day
        Jcent = (Jday - 2451545) / 36525 # Julian century

        Manom = 357.52911 + Jcent * (35999.05029 - 0.0001537 * Jcent)
        Mlong = 280.46646 + Jcent * (36000.76983 + Jcent * 0.0003032) % 360
        Eccent = 0.016708634 - Jcent * (0.000042037 + 0.0001537 * Jcent)
        Mobliq = 23 + (26 + ((21.448 - Jcent * (46.815 + Jcent *\
            (0.00059 - Jcent * 0.001813)))) / 60) / 60
        obliq = Mobliq + 0.00256 * cos(rad(125.04 - 1934.136 * Jcent))
        vary = tan(rad(obliq / 2)) * tan(rad(obliq / 2))
        Seqcent = sin(rad(Manom)) * (1.914602 - Jcent *\
            (0.004817 + 0.000014 * Jcent)) + sin(rad(2 * Manom)) *\
            (0.019993 - 0.000101 * Jcent) + sin(rad(3 * Manom)) * 0.000289
        Struelong = Mlong + Seqcent
        Sapplong = Struelong - 0.00569-0.00478 * sin(rad(125.04 - 1934.136 * Jcent))
        declination = deg(asin(sin(rad(obliq)) * sin(rad(Sapplong))))

        eqtime = 4 * deg(vary * sin(2 * rad(Mlong)) - 2 * Eccent *\
            sin(rad(Manom)) + 4 * Eccent * vary * sin(rad(Manom)) *\
            cos(2*rad(Mlong)) - 0.5 * vary * vary * sin(4 * rad(Mlong)) -\
            1.25 * Eccent * Eccent * sin(2 * rad(Manom)))
        hourangle = deg(acos(cos(rad(90.833)) / (cos(rad(latitude)) *\
            cos(rad(declination))) - tan(rad(latitude)) * tan(rad(declination))))

        solarnoon_t = (720 - 4 * longitude-eqtime) / 1440
        sunrise_t  = solarnoon_t-hourangle * 4 / 1440
        sunset_t   = solarnoon_t+hourangle * 4 / 1440

        def decimaltotime(day):
            global time
            hours  = 24.0 * day
            h = int(hours)
            minutes = (hours-h) * 60
            m = int(minutes)
            seconds = (minutes-m) * 60
            s = int(seconds)
            return time(hour=h, minute=m, second=s)

        self.solarnoon_t = decimaltotime(solarnoon_t)
        self.sunrise_t = decimaltotime(sunrise_t)
        self.sunset_t = decimaltotime(sunset_t)
