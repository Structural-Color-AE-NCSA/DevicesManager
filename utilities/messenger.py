import json
import threading
import time

messengers = dict()

class Messenger(object):
    cond = None
    ready = False
    my_message = ""
    _instances = {}

    def __init__(self, title: str):
        # This ensures we only initialize the title once (when the object is created)
        if not hasattr(self, 'initialized'):  # Only initialize if not already done
            self.initialized = True
            self.title = title
    def __new__(cls, title: str):
        # Check if an object with the same title already exists
        if title not in cls._instances:
            # If not, create a new instance and store it
            instance = super(Messenger, cls).__new__(cls)
            instance.title = title
            instance.cond = threading.Condition()
            cls._instances[title] = instance
        # Return the existing or newly created instance
        return cls._instances[title]

    def __set_condition(self):
        self.cond = threading.Condition()

    def get_message(self):
        with self.cond:
            while not self.ready:
                self.cond.wait()
            # print("Consumer: Data is ready, consuming..." + self.my_message)
            self.ready = False  # Reset the condition after consuming
            # time.sleep(1)
            yield self.my_message
    def send_message(self, message):
        with self.cond:
            self.ready = True
            self.my_message = message
            # print("Producer: Data is ready, notifying all.")
            self.cond.notify_all()

def gen_fake_message(messenger):
    producer_thread = threading.Thread(target=gen_data, args=[messenger])
    producer_thread.daemon = True
    producer_thread.start()


def gen_data(obj, cell_id = None, cell_color = None):
    from random import randrange
    print("start to generate messages")
    while True:
        data = dict()
        if cell_id is None:
            data['cell_id'] = randrange(400)
        if cell_color is None:
            data['color'] = 'red'
        # print("send " + json.dumps(data))
        obj.send_message(json.dumps(data))
        time.sleep(2)


def output_data(obj):
    print("start to receive messages")
    while True:
        generator = obj.get_message()
        for item in generator:
            print("Processing:", item)


if __name__ == "__main__":
    messenger = Messenger("test")
    # consumer_thread = threading.Thread(target=output_data, args=[messenger])
    producer_thread = threading.Thread(target=gen_data, args=[messenger])
    # consumer_thread.daemon = True
    producer_thread.daemon = True
    # consumer_thread.start()
    producer_thread.start()

    # consumer_thread.join()
    producer_thread.join()

