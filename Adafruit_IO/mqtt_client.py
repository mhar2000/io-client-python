# MQTT-based client for Adafruit.IO
# Author: Tony DiCola (tdicola@adafruit.com)
#
# Supports publishing and subscribing to feed changes from Adafruit IO using
# the MQTT protcol.
#
# Depends on the following Python libraries:
# - paho-mqtt: Paho MQTT client for python.
import logging

import paho.mqtt.client as mqtt


SERVICE_HOST   = 'io.adafruit.com'
SERVICE_PORT   = 1883
KEEP_ALIVE_SEC = 3600  # One minute

logger = logging.getLogger(__name__)


class MQTTClient(object):
    """Interface for publishing and subscribing to feed changes on Adafruit IO
    using the MQTT protocol.
    """

    def __init__(self, key):
        """Create instance of MQTT client.

        Required parameters:
        - key: The Adafruit.IO access key for your account.
        - feed_id: The id of the feed to access.
        """
        # Initialize event callbacks to be None so they don't fire.
        self.on_connect    = None
        self.on_disconnect = None
        self.on_message    = None
        # Initialize MQTT client.
        self._client = mqtt.Client()
        self._client.username_pw_set(key)
        self._client.on_connect    = self._mqtt_connect
        self._client.on_disconnect = self._mqtt_disconnect
        self._client.on_message    = self._mqtt_message
        self._connected = False

    def _mqtt_connect(self, client, userdata, flags, rc):
        logger.debug('Client on_connect called.')
        # Check if the result code is success (0) or some error (non-zero) and
        # raise an exception if failed.
        if rc == 0:
            self._connected = True
        else:
            # TODO: Make explicit exception classes for these failures:
            # 0: Connection successful 1: Connection refused - incorrect protocol version 2: Connection refused - invalid client identifier 3: Connection refused - server unavailable 4: Connection refused - bad username or password 5: Connection refused - not authorised 6-255: Currently unused.
            raise RuntimeError('Error connecting to Adafruit IO with rc: {0}'.format(rc))
        # Call the on_connect callback if available.
        if self.on_connect is not None:
            self.on_connect(self)

    def _mqtt_disconnect(self, client, userdata, rc):
        logger.debug('Client on_disconnect called.')
        self._connected = False
        # If this was an unexpected disconnect (non-zero result code) then raise
        # an exception.
        if rc != 0:
            raise RuntimeError('Unexpected disconnect with rc: {0}'.format(rc))
        # Call the on_disconnect callback if available.
        if self.on_disconnect is not None:
            self.on_disconnect(self)

    def _mqtt_message(self, client, userdata, msg):
        logger.debug('Client on_message called.')
        # Parse out the feed id and call on_message callback.
        # Assumes topic looks like "api/feeds/{feed_id}/streams/receive.json"
        if self.on_message is not None and msg.topic.startswith('api/feeds/') \
            and len(msg.topic) >= 31:
            feed_id = msg.topic[10:-21]
            self.on_message(self, feed_id, msg.payload)

    def connect(self, **kwargs):
        """Connect to the Adafruit.IO service.  Must be called before any loop
        or publish operations are called.  Will raise an exception if a 
        connection cannot be made.  Optional keyword arguments will be passed
        to paho-mqtt client connect function.
        """
        # Skip calling connect if already connected.
        if self._connected:
            return
        # Connect to the Adafruit IO MQTT service.
        self._client.connect(SERVICE_HOST, port=SERVICE_PORT, 
            keepalive=KEEP_ALIVE_SEC, **kwargs)

    def is_connected(self):
        """Returns True if connected to Adafruit.IO and False if not connected.
        """
        return self._connected

    def disconnect(self):
        # Disconnect MQTT client if connected.
        if self._connected:
            self._client.disconnect()

    def loop_background(self):
        """Starts a background thread to listen for messages from Adafruit.IO
        and call the appropriate callbacks when feed events occur.  Will return
        immediately and will not block execution.  Should only be called once.
        """
        self._client.loop_start()

    def loop_blocking(self):
        """Listen for messages from Adafruit.IO and call the appropriate
        callbacks when feed events occur.  This call will block execution of
        your program and will not return until disconnect is explicitly called.

        This is useful if your program doesn't need to do anything else except
        listen and respond to Adafruit.IO feed events.  If you need to do other 
        processing, consider using the loop_background function to run a loop
        in the background.
        """
        self._client.loop_forever()

    def loop(self, timeout_sec=1.0):
        """Manually process messages from Adafruit.IO.  This is meant to be used
        inside your own main loop, where you periodically call this function to
        make sure messages are being processed to and from Adafruit_IO.

        The optional timeout_sec parameter specifies at most how long to block 
        execution waiting for messages when this function is called.  The default
        is one second.
        """
        self._client.loop(timeout=timeout_sec)

    def subscribe(self, feed_id):
        """Subscribe to changes on the specified feed.  When the feed is updated
        the on_message function will be called with the feed_id and new value.
        """
        self._client.subscribe('api/feeds/{0}/streams/receive.json'.format(feed_id))

    def publish(self, feed_id, value):
        """Publish a value to a specified feed.

        Required parameters:
        - feed_id: The id of the feed to update.
        - value: The new value to publish to the feed.
        """
        self._client.publish('api/feeds/{0}/streams/send.json'.format(feed_id),
            payload=value)