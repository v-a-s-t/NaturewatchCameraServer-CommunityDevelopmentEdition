#!naturewatchenv/bin/python
import json
import os
import logging
import sys
from ChangeDetector import ChangeDetector
from CameraController import CameraController
import time
from urllib.parse import urlparse, parse_qs
from flask import Flask, send_from_directory, Response

# NatureCam implementation
# changeDetectorInstance = ChangeDetector(config)

isTimeSet = False

camera_controller = CameraController(use_splitter_port=True)

# Flask
app = Flask(__name__, static_folder='www/')



# Serve static website
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


def generate_mjpg():
    while camera_controller.is_alive():
        try:
            frame = camera_controller.get_image_binary()
            yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + bytearray(frame) + b'\r\n')
        except BrokenPipeError:
            app.logger.info("Client disconnected from camera feed.")
            break
        except ConnectionResetError:
            app.logger.info("Camera feed connection reset by peer.")
            break


@app.route('/feed')
def feed():
    app.logger.info("Serving camera feed...")
    return Response(generate_mjpg(), mimetype='multipart/x-mixed-replace; boundary=frame')


def setup_logger(name, log_file, level=logging.INFO):
    """Function setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

'''
# Handle HTTP requests.
class CamHandler(BaseHTTPRequestHandler):
    type_map = {
        '.js': 'text/javascript',
        '.css': 'text/css',
        '.html': 'text/html',
        '.jpg': 'image/jpeg',
    }

    # Options
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        print(self.path)
        base, ext = os.path.splitext(self.path)

        # Serve root website
        if self.path == '/':
            with open('index.html', 'rb') as file:
                print("Served website.")
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(file.read())
            return

        # Serve web files
        elif ext in self.type_map:
            file_name = self.path[1:]
            with open(file_name, 'rb') as file:
                print("Served file " + file_name)

                self.send_response(200)
                for extension, content_type in self.type_map.items():
                    if self.path.endswith(extension):
                        self.send_header('Content-type', content_type)

                self.end_headers()
                self.wfile.write(file.read())
            return

        # List photos directory
        elif self.path.startswith('/photos/'):
            data = {
                'total': 0,
                'files': []
            }
            files = [
                f for f in sorted(os.listdir('photos/'))
                if os.path.isfile(os.path.join('photos/', f)) and f.endswith('.jpg')
            ]
            if len(files) > 0:
                start, end = self._get_start_and_end(files)
                data['total'] = len(files)
                data['files'] = files[start:end]
            result = json.dumps(data)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(result.encode("utf-8"))
            print("Served photo directory contents.")
            return

        # Serve camera stream
        elif self.path.endswith('.mjpg'):
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            print("Serving mjpg...")
            while True:
                try:
                    img = changeDetectorInstance.get_current_image()
                    # r, buf = cv2.imencode(".jpg", img)
                    r, buf = (None, None)
                    self.wfile.write(b'--jpgboundary\r\n')
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', str(len(buf)))
                    self.end_headers()
                    self.wfile.write(bytearray(buf))
                    self.wfile.write(b'\r\n')
                    time.sleep(config["stream_delay"])
                except KeyboardInterrupt:
                    break
                except BrokenPipeError:
                    print("Client disconnected from stream.")
                    break
                except ConnectionResetError:
                    print("Connection reset by peer.")
                    break
            return

        # Camera control request - Less sensitivity
        elif self.path.endswith('less'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'success')
            changeDetectorInstance.minWidth = config["less_sensitivity"]
            changeDetectorInstance.minHeight = config["less_sensitivity"]
            print("Changed sensitivity to less")
            return

        # Camera control request - More sensitivity
        elif self.path.endswith('more'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'success')
            changeDetectorInstance.minWidth = config["more_sensitivity"]
            changeDetectorInstance.minHeight = config["more_sensitivity"]
            print("Changed sensitivity to more")
            return

        # Camera control request - Default sensitivity
        elif self.path.endswith('default'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'success')
            changeDetectorInstance.minWidth = config["min_width"]
            changeDetectorInstance.minHeight = config["min_width"]
            print("Changed sensitivity to default")
            return

        # Camera control request - Start recording
        elif self.path.endswith('start'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'success')
            changeDetectorInstance.arm()
            print("Started recording.")
            return

        # Camera control request - Stop recording
        elif self.path.endswith('stop'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'success')
            changeDetectorInstance.disarm()
            print("Stopped recording.")
            return

        # Camera control request - Delete all photos
        elif self.path.endswith('delete-final'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'success')
            os.system('rm photos/*')
            print("Deleted photos.")
            return

        # Camera info request - Get camera status
        elif self.path.endswith('get-status'):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            sensitivity = "unknown"
            if changeDetectorInstance.minWidth == config["less_sensitivity"]:
                sensitivity = "less"
            elif changeDetectorInstance.minWidth == config["min_width"]:
                sensitivity = "default"
            elif changeDetectorInstance.minWidth == config["more_sensitivity"]:
                sensitivity = "more"
            send_data = {
                "mode": changeDetectorInstance.mode,
                "sensitivity": sensitivity,
                "fix_camera_settings": config["fix_camera_settings"],
                "iso": config["iso"],
                "shutter_speed": config["shutter_speed"],
                "rotate_camera": config["rotate_camera"]
            }
            json_data = json.dumps(send_data)
            self.wfile.write(json_data.encode("utf-8"))
            print("Returned camera status.")
            return

        # Camera control request - Rotate camera 180 degrees
        elif self.path.endswith('rotate-180'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'success')
            new_config = changeDetectorInstance.rotate_camera()
            self.update_config(new_config)
            print("Rotated camera.")
            return

        # Camera control request - Set exposure settings to auto
        elif self.path.endswith('auto-exposure'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'success')
            new_config = changeDetectorInstance.auto_exposure()
            self.update_config(new_config)
            print("Set exposure settings to auto.")
            return

        # 404 page
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Page not found')
            print("Page not found.")
            return

    def _get_start_and_end(self, files):
        args = parse_qs(urlparse(self.path).query)
        page = int(self._get_query_value(args, 'page', '1'))
        size = self._get_query_value(args, 'size', 'all')
        if 'all' == size:
            start = 0
            end = len(files)
        else:
            size = int(size)
            start = (page - 1) * size
            end = start + size
        return start, end

    def do_POST(self):
        print(self.path)

        # POST request - Update time
        if self.path.endswith('set-time'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            data_string = self.rfile.read(int(self.headers['Content-Length']))
            data = json.loads(data_string.decode('utf-8'))

            print("Time: " + data["timeString"])

            global isTimeSet
            if isTimeSet is True:
                print("Time has already been set during this powerup.")
            else:
                os.system('date -s "' + data["timeString"] + '"')
                isTimeSet = True
                print("Time updated.")

            self.wfile.write(b'success')

        # POST request - Set exposure and ISO settings
        elif self.path.endswith('fix-exposure'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            data_string = self.rfile.read(int(self.headers['Content-Length']))
            data = json.loads(data_string.decode('utf-8'))

            print("Exposure: {}".format(data["exposure"]))

            new_config = changeDetectorInstance.fix_exposure(int(data["exposure"]))
            self.update_config(new_config)

            self.wfile.write(b'success')

    @staticmethod
    def update_config(new_config):
        global config
        config = new_config
        with open("../config.json", 'w') as json_file:
            contents = json.dumps(config, sort_keys=True, indent=4, separators=(',', ': '))
            json_file.write(contents)

    def _get_query_value(self, args, key, default):
        values = args.get(key, [])
        if values:
            try:
                value = values.pop()
            except IndexError:
                value = default
            return value


# Threaded server
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads"""


def main():
    if len(sys.argv) != 2:
        print("Error - please provide server port as first argument when calling the script.")
        sys.exit(2)

    server = None
    try:
        changeDetectorInstance.start()
        server = ThreadedHTTPServer(('', int(sys.argv[1])), CamHandler)
        print("server started")
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        changeDetectorInstance.cancel()
        if server is not None:
            server.socket.close()
'''

# Set up loggers
camera_logger = setup_logger('camera_controller_controller', 'camera_controller.log')

if __name__ == '__main__':
    camera_controller.start()
    app.run(debug=True, threaded=True)
