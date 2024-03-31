import gevent.monkey
gevent.monkey.patch_all()

import aichat_app
workers = 5    
worker_class = "gevent"
bind = "0.0.0.0:5000"
def on_starting(server):
    aichat_app.init()
