"""Logging handler for websocket clients."""

import cherrypy
import json
import logging


class WebSocketLoggingHandler(logging.Handler):
    """Logging handler for websocket clients."""

    def __init__(self):
        super(WebSocketLoggingHandler, self).__init__()

    def emit(self, record):
        """Overridden from Handler; actually emit the log entry."""
        message = self.format(record)
        cherrypy.engine.publish(
            'websocket-broadcast',
            json.dumps({'type': 'log', 'message': message})
        )
