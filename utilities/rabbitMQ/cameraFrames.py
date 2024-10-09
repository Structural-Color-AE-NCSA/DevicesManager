import threading
import json
import base64
import time
from .connector import DeviceConnector


class CameraFrames(object):
    def __init__(self, socketio):
        self.socketio = socketio
        queue_name = 'camera_frames_queue'
        routing_key = 'camera_frames_routing_key'
        frames_updates = DeviceConnector(queue_name, routing_key, self.on_frame_message)
        frames_updates.connect()
        self.start_listen(frames_updates)

    def start_listen(self, target):
        thread = threading.Thread(target=target.consume)
        thread.daemon = True
        thread.start()

    def on_frame_message(self, ch, method, properties, body):
        img_data = base64.b64decode(body)
        img_str = base64.b64encode(img_data).decode('utf-8')
        self.socketio.emit('camera_frame', {'frame': img_str})
        time.sleep(0.03)
