import os, logging
import wsgiref.handlers
from xml.dom import minidom
import twilio

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import urlfetch

# BASE_URL = "http://76.121.171.19:8080"
BASE_URL = "http://sostranslate.appspot.com/"
WEATHER_API_URL = "http://weather.yahooapis.com/forecastrss?p="
WEATHER_API_NS = "http://xml.weather.yahoo.com/ns/rss/1.0"
# Twilio REST API version
API_VERSION = '2008-08-01'

# Twilio AccountSid and AuthToken
ACCOUNT_SID = 'AC7fd034aa236598bd0d090f907ea14169'
ACCOUNT_TOKEN = 'WITHOLDEN'

# Outgoing Caller ID previously validated with Twilio
CALLER_ID = '2488948772';

# Create a Twilio REST account object using your Twilio account ID and token
# FIXME need ACCOUNT_TOKEN
account = twilio.Account(ACCOUNT_SID, ACCOUNT_TOKEN)


class WeatherPage(webapp.RequestHandler):
    """
    Accepts input digits from the caller, fetches the weather from an
    external site, and reads back the weather to the caller
    """
    def get(self):
        self.post()
    
    def _error(self, msg, redirecturl=None):
        templatevalues = {
            'msg': msg,
            'redirecturl': redirecturl
        }
        xml_response(self, 'error.xml', templatevalues)
    
    def _fetch(self, zipcode):
        url = WEATHER_API_URL + zipcode
        result = urlfetch.fetch(url)
        if result.status_code != 200:
            return None
        return result.content
    
    def _parse(self, xml):
        dom = minidom.parseString(xml)
        conditions = dom.getElementsByTagNameNS(WEATHER_API_NS,
            'condition')[0]
        location = dom.getElementsByTagNameNS(WEATHER_API_NS,
            'location')[0]
        return {
            'location': '%s, %s' % (location.getAttribute('city'),
                location.getAttribute('region')),
            'conditions': conditions.getAttribute('text'),
            'temp': conditions.getAttribute('temp')
        }
    # @start snippet
    def post(self):
        zipcode = self.request.get('Digits')
        if not zipcode:
            self._error("Invalid zip code.", BASE_URL)
            return
        
        # strip off extra digits and keys from the Digits we got back
        zipcode = zipcode.replace('#', '').replace('*', '')[:5]
        
        weatherxml = self._fetch(zipcode)
        if not weatherxml:
            self._error("Error fetching weather. Good Bye.")
            return
        
        try:
            weather = self._parse(weatherxml)
            r = twilio.Response()
            r.append(twilio.Say("It is currently %s degrees fahrenheit and %s in %s" % (weather['temp'], weather['conditions'], weather['location'])))
            self.response.out.write(r)
            logging.info("responding with: %s" % r)
            # xml_response(self, 'weather.xml', self._parse(weatherxml))
        except Exception, e:
            self._error("Error parsing weather. Good Bye.: %s" % e)
        # @end snippet

# @start snippet
def xml_response(handler, page, templatevalues=None):
    """
    Renders an XML response using a provided template page and values
    """
    path = os.path.join(os.path.dirname(__file__), page)
    handler.response.headers["Content-Type"] = "text/xml"
    r = template.render(path, templatevalues)
    handler.response.out.write(r)
    logging.info("responding with: %s" % r)

class Sms(webapp.RequestHandler):
    """
        Receives an sms message and setups up a call.
    """
    def get(self):
        self.post()
    
    def post(self):
        """
            this is supposed to call a number and then start a conference.
            not working.
            after one texts  7982-7765 test to 14155992671 the service should call a number and try to connect a conference call
        """
        d = {
            'Caller' : CALLER_ID,
            'Called' : '2483835847',
            'Url' : 'http://demo.twilio.com/voicerecorder/makerecording.php',
        }
        logging.info("calling: %s" % d)
        try:
            print account.request('/%s/Accounts/%s/Calls' % \
                                      (API_VERSION, ACCOUNT_SID), 'POST', d)
        except Exception, e:
            print e
            print e.read()
        # r = twilio.Response()
        # r.addDial(number="2488948772")
        # r.addSay(text='Hello there')
        # r.addDial(number="2483835847").addConference(name='Conference test1')
        # r.addSms(msg='this is just a test', to='2488948772')
        # r.append(twilio.Redirect())
        # logging.info(r)
        # self.response.out.write('<?xml  version="1.0" encoding="UTF-8"?>\r\n' + str(r))
        # self.response.out.write(r)

class GatherPage(webapp.RequestHandler):
    """
    Initial user greeting.  Plays the welcome audio file then reads the
    "enter zip code" message.  The Play and Say are wrapped in a Gather
    verb to collect the 5 digit zip code from the caller.  The Gather
    will post the results to /weather
    """
    def get(self):
        self.post()
    
    def post(self):
        r = twilio.Response()
        g = r.append(twilio.Gather(numDigits=5, method="POST", action="%sweather" % BASE_URL))
        g.append(twilio.Say("Please enter your 5 digit zipcode to hear the weather."))
        r.append(twilio.Redirect())
        self.response.out.write(r)
        logging.info("trying to gather data from user: %s" % r)
# @end snippet

def main():
	# @start snippet
    application = webapp.WSGIApplication([ \
        ('/', GatherPage),
        ('/sms', Sms),
        ('/weather', WeatherPage)],
        debug=True)
    # @end snippet
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
