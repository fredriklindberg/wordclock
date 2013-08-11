#
# Geolocation using the hostip.info API
#
import json
import urllib2

class Geoloc:

    _cachefmt = "/var/tmp/geoloc-{0}.json"

    _cache_located = False
    _url_located = False

    def __init__(self, ip=None):
        self._ip = ip
        self._lng = float('NaN')
        self._lat = float('NaN')
        self._readcache()
        self.update()

    def _sync(self):
        try:
            data = json.loads(self._data)
            self._lng = float(data['lng'])
            self._lat = float(data['lat'])
        except:
            ""

    def _readcache(self):
        cachename = self._cachefmt.format(self._ip if self._ip else "default")
        try:
            cf = open(cachename, 'r')
            self._data = cf.read()
            cf.close()
            self._sync()
            self._cache_located = True
        except:
            ""

    def _writecache(self):
        cachename = self._cachefmt.format(self._ip if self._ip else "default")
        try:
            cf = open(cachename, 'w')
            cf.write(self._data)
            cf.close()
        except:
            ""

    def update(self):
        try:
            url = 'http://api.hostip.info/get_json.php?position=true?ip='.\
                format(self._ip if self._ip else '')
            data = urllib2.urlopen(url=url, timeout=2)

            self._data = data.read()
            self._sync()
            self._writecache()
            self._url_located = True
        except:
            ""

    def located(self):
        return self.lng != float('NaN') and self.lat != float('NaN')

    @property
    def lat(self):
        if not self._url_located:
            self.update()
        return self._lat

    @property
    def lng(self):
        if not self._url_located:
            self.update()
        return self._lng

