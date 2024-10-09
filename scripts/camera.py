import cv2
import pika
import base64

parameters = pika.URLParameters('amqp://devicesmanager:password@141.142.219.4/%2F')
# parameters = pika.URLParameters('amqp://guest:guest@localhost/%2F')
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# Declare a queue for frames
channel.queue_declare(queue='camera_frames_queue', durable=True)

# Capture video from the camera
camera = cv2.VideoCapture(0)

while True:
    # Read a frame from the camera
    success, frame = camera.read()
    if not success:
        break

    # Encode frame as JPEG
    _, buffer = cv2.imencode('.jpg', frame)

    # Encode frame as base64 to safely transmit over RabbitMQ
    frame_as_text = base64.b64encode(buffer).decode('utf-8')

    # Send the frame to RabbitMQ
    channel.basic_publish(exchange='devices_manager', routing_key='camera_frames_routing_key', body=frame_as_text)
    print("Sent frame to RabbitMQ")

# Release resources
camera.release()
connection.close()