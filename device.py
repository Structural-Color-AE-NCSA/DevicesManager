import traceback
from flask import Flask, Response, render_template, url_for, flash, redirect, Blueprint, request, session, current_app, \
    send_from_directory, abort

import time

from .scripts.replace_placeholders import replace_placeholders_content
from .utilities.messenger import Messenger, gen_fake_message
from .auth import role_required

from flask import jsonify
from .utilities.user_utilities import *
from .utilities.rabbitMQ.cameraFrames import CameraFrames
from .utilities.rabbitMQ.pcpFile import PCPFile
from .utilities.rabbitMQ.printingParams import PrintingParams
from .utilities.grid_plot import *

from flask_paginate import Pagination, get_page_args
from .config import Config
import logging
from time import gmtime

logging.Formatter.converter = gmtime
logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%dT%H:%M:%S',
                    format='%(asctime)-15s.%(msecs)03dZ %(levelname)-7s [%(threadName)-10s] : %(name)s - %(message)s')
__logger = logging.getLogger("device.py")

devicebp = Blueprint('device', __name__, url_prefix=Config.URL_PREFIX + '/device')

pcp_file = PCPFile()
printing_params = PrintingParams()
grid_plot = GridPlot()


shape_x = 0
shape_y = 0
buf = None


@devicebp.route('/device/init_pcp_file', methods=['POST'])
@role_required("user")
def load_pcp_file():
    """
    load pcp file and initialize the grid
    :return:
    """
    is_abs_printing = False
    file_content = json.loads(request.data).get("data")
    x_start_pos = 0
    y_start_pos = 0

    x_min = 0
    x_max = 0
    y_min = 0
    y_max = 0
    x = 0
    y = 0
    file_content = file_content.replace(")\n", ")\r\n")
    pcp_commands = file_content.split("\r\n")
    for cmd in pcp_commands:
        if len(cmd) <= 0:
            continue
        print(cmd)
        cmd = cmd.replace("\\n", "\n")
        if cmd.startswith("#"):
            continue
        tmp = cmd.split("(")
        command = tmp[0].split(".")
        name = command[0]  # device
        sub = cmd[1 + len(name):]
        op = None  # operation
        params = None  # operation params
        pattern = r'^(.*?)\('
        match = re.search(pattern, sub)
        if match:
            op = match.group(1)
        pattern = r'"([^"]*)"'
        match = re.search(pattern, sub)
        if match:
            params = match.group(1)
        else:
            pattern = r'\((.*?)\)'
            match = re.search(pattern, sub)
            if match:
                params = match.group(1)
        if name == "axes":
            if op == "move":
                print("lulzbot.move: " + params)

                x_move_pattern = r"X(-?\d+)"
                match = re.search(x_move_pattern, params)
                if match:
                    x_delta = int(match.group(1))
                    x = x + x_delta
                    x_min = min(x_min, x)
                    x_max = max(x_max, x)

                y_move_pattern = r"Y(-?\d+)"
                match = re.search(y_move_pattern, params)
                if match:
                    y_delta = int(match.group(1))
                    y = y + y_delta
                    y_min = min(y_min, y)
                    y_max = max(y_max, y)
            elif op == "startPoint":
                is_abs_printing = True
                print("lulzbot.startPoint: " + params)
                x_abs_pattern = r"X=(-?\d+)"
                match = re.search(x_abs_pattern, params)
                if match:
                    x_start_pos = int(match.group(1))
                y_abs_pattern = r"Y=(-?\d+)"
                match = re.search(y_abs_pattern, params)
                if match:
                    y_start_pos = int(match.group(1))

    print("pcp shape width: " + str(x_max - x_min))
    print("pcp shape height: " + str(y_max - y_min))
    shape_x = x_max - x_min
    shape_y = y_max - y_min

    data = dict()
    data['shape_x'] = shape_x
    data['shape_y'] = shape_y
    data['nrows'], data['ncols'] = grid_plot.get_dimension(shape_x, shape_y)
    buf = grid_plot.init_plot(282, 582, shape_x, shape_y)

    if is_abs_printing:
        cell_id = grid_plot.calculate_cell_id(x_start_pos, y_start_pos)
        grid_plot.set_starting_cell_id(cell_id)
    # return Response(buf, mimetype='image/png')
    return jsonify(data), 200


@devicebp.route('/device/send_printing_params', methods=['POST'])
def send_printing_params():
    commands = dict()
    x_relative_pos = request.form.get('x_relative_pos')
    y_relative_pos = request.form.get('y_relative_pos')
    z_relative_pos = request.form.get('z_relative_pos')
    print_speed = request.form.get('single_print_speed')
    pressure = request.form.get('single_pressure')
    bed_temp = request.form.get('single_bed_temp')
    pos = ""
    if x_relative_pos:
        pos = pos + "X" + str(x_relative_pos) + " "
    if y_relative_pos:
        pos = pos + "Y" + str(y_relative_pos) + " "
    if z_relative_pos:
        pos = pos + "Z" + str(z_relative_pos) + " "
    if print_speed:
        pos = pos + "F" + str(print_speed)
    if pos:
        commands['pos'] = "G1 " + pos + "\n"

    if pressure:
        commands['pressure'] = pressure

    if bed_temp:
        commands['bed_temp'] = "M140 S" + bed_temp + "\n"

    printing_params.send_printing_params(commands)

    return jsonify([]), 200


@devicebp.route('/device/run_pcp_file', methods=['POST'])
@role_required("user")
def send_pcp_file():
    filename = request.form.get('pcpFileName')
    starting_cell_id = request.form.get('starting_cell_id')
    campaign_name = request.form.get('campaignName')
    grid_ncols = int(request.form.get('grid_ncols'))
    grid_nrows = int(request.form.get('grid_nrows'))
    max_loops = int(request.form.get('max_loops'))
    number_prints_trigger_prediction = int(request.form.get('number_prints_trigger_prediction'))

    # ranges:
    min_bed_temp = float(request.form.get('min_bed_temp'))
    max_bed_temp = float(request.form.get('max_bed_temp'))
    min_pressure = float(request.form.get('min_pressure'))
    max_pressure = float(request.form.get('max_pressure'))
    min_speed = float(request.form.get('min_speed'))
    max_speed = float(request.form.get('max_speed'))
    min_zheight = float(request.form.get('min_zheight'))
    max_zheight = float(request.form.get('max_zheight'))

    hue = None
    if request.form.get('hue'):
        hue = float(request.form.get('hue'))
    saturation = None
    if request.form.get('saturation'):
        saturation = float(request.form.get('saturation'))
    value = None
    if request.form.get('value'):
        value = float(request.form.get('value'))

    bed_temp = None
    if request.form.get('bed_temp'):
        bed_temp = float(request.form.get('bed_temp'))
    pressure = None
    if request.form.get('pressure'):
        pressure = float(request.form.get('pressure'))
    print_speed = None
    if request.form.get('print_speed'):
        print_speed = float(request.form.get('print_speed'))
    z_abs_height = None
    if request.form.get('z_abs_height'):
        z_abs_height = float(request.form.get('z_abs_height'))
    autoclean_x_abs_pos = None
    if request.form.get('autoclean_x_abs_pos'):
        z_abs_height = float(request.form.get('autoclean_x_abs_pos'))
    autoclean_y_abs_pos = None
    if request.form.get('autoclean_y_abs_pos'):
        z_abs_height = float(request.form.get('autoclean_y_abs_pos'))

    if filename == '' or campaign_name == '':
        return "fail", 400
    print(f'PCP File Name: {filename}')
    path_to_pcp_file = os.path.join(os.getcwd(), 'DevicesManager/pcp', filename)
    file_content = ""
    with open(path_to_pcp_file, 'r') as file:
        file_content = file.read()
    # save campaign to db
    init_settings = {"bed_temp": bed_temp, "pressure": pressure, "print_speed": print_speed, "z_abs_height": z_abs_height}
    nozzle_auto_clean_abs_posistions = {"abs_x": autoclean_x_abs_pos, "abs_y": autoclean_y_abs_pos}
    predict_ranges = {"min_bed_temp": min_bed_temp, "max_bed_temp": max_bed_temp,
                      "min_pressure": min_pressure, "max_pressure": max_pressure,
                      "min_speed": min_speed, "max_speed": max_speed,
                      "min_zheight": min_zheight, "max_zheight": max_zheight}
    new_campaign_doc = {"campaignName": campaign_name, "submitter": session['name'],
                        "grid_ncols": grid_ncols, "grid_nrows": grid_nrows,
                        "init_settings": init_settings,
                        "nozzle_auto_clean_abs_posistions": nozzle_auto_clean_abs_posistions,
                        "predict_ranges": predict_ranges,
                        "bed_temp": bed_temp, "pressure": pressure,
                        "print_speed": print_speed, "z_abs_height": z_abs_height,
                        "max_loops": max_loops, "number_prints_trigger_prediction": number_prints_trigger_prediction,
                        "hue": hue, "saturation": saturation,
                        "value": value,
                        "filename": filename, "starting_cell_id": starting_cell_id, "status": "running", "filepath": path_to_pcp_file}
    insert_result = insert_one(current_app.config['CAMPAIGNS_COLLECTION'], document=new_campaign_doc)

    if insert_result.inserted_id is None:
        __logger.error("Insert new campaign " + campaign_name + " failed")
        # return redirect(url_for('management.home', title='Campaigns'))
        return "fail", 400

    __logger.info("successfully inserted new campaign " + campaign_name)

    campaign_id = str(insert_result.inserted_id)

    if starting_cell_id == '':  # relative postions
        pcp_commands = file_content + "Done\n"
        pcp_file.send_pcp_file(pcp_commands, -1)
    else:
        # cells = [item.strip() for item in cell_ids.split(',')]
        # for cell_id in cells:
        #     abs_x, abs_y = grid_plot.get_top_left_corner_pos_by_cell_id(int(cell_id))
        #     X = "\"X=" + str(abs_x)
        #     Y = "Y=" + str(abs_y)
        #     Z = "Z=21.4" + "\""
        #     if z_abs_height:
        #         Z = "Z="+str(z_abs_height) + "\""
        #     start_point_pos = "axes.startPoint(" + X + " " + Y + " " + Z + ")"
        #     print(start_point_pos)
        #     pcp_commands = start_point_pos + "\r\n" + file_content + "Done\n"
        #     pcp_file.send_pcp_file(campaign_id, pcp_commands, int(cell_id), bed_temp, print_speed, pressure)

        cell_id = int(starting_cell_id)
        abs_x, abs_y = grid_plot.get_top_left_corner_pos_by_cell_id(int(cell_id))
        X = "\"X=" + str(abs_x)
        Y = "Y=" + str(abs_y)
        Z = "Z=21.4" + "\""
        if z_abs_height:
            Z = "Z="+str(z_abs_height) + "\""
        start_point_pos = "axes.startPoint(" + X + " " + Y + " " + Z + ")"
        print(start_point_pos)

        # replace parameters
        file_content = replace_placeholders_content(file_content, bed_temp, pressure, print_speed, z_abs_height)
        pcp_commands = start_point_pos + "\r\n" + file_content + "Done\n"
        pcp_file.send_pcp_file(campaign_id, pcp_commands, int(cell_id), number_prints_trigger_prediction, 0, 0.0, bed_temp, print_speed, pressure,
                               autoclean_x_abs_pos,
                               autoclean_y_abs_pos,
                               predict_ranges)
    # for filename in request.form:
    #     print(f'PCP File Name: {filename}')
    #     path_to_pcp_file = os.path.join(os.getcwd(), 'pcp', filename)
    #     with open(path_to_pcp_file, 'r') as file:
    #         file_content = file.read()
    #     # add end line to notify pcp completion
    #     file_content = file_content + "Done\n"
    #     pcp_file.send_pcp_file(file_content, grid_plot.get_cell_id())
    # fixme, mimic another the 6 runs
    # time.sleep(1)
    # pcp_file.send_pcp_file(file_content, 1+grid_plot.get_cell_id())
    # time.sleep(1)
    # pcp_file.send_pcp_file(file_content, 2+grid_plot.get_cell_id())
    # time.sleep(1)
    # pcp_file.send_pcp_file(file_content, 3+grid_plot.get_cell_id())
    # time.sleep(1)
    # pcp_file.send_pcp_file(file_content, 4+grid_plot.get_cell_id())
    # time.sleep(1)
    # pcp_file.send_pcp_file(file_content, 5+grid_plot.get_cell_id())
    # time.sleep(1)
    # pcp_file.send_pcp_file(file_content, 6+grid_plot.get_cell_id())
    return jsonify({"campaign_name": campaign_name, "campaign_id": campaign_id}), 200

@devicebp.route('/pcp_plot')
def pcp_plot():
    buf = grid_plot.load_plot()
    return Response(buf, mimetype='image/png')


@devicebp.route('/update_pcp_plot', methods=['POST'])
# @role_required("user")
def update_pcp_plot():
    # fake x, y
    # x = [random.randint(1, 282)/10 for _ in range(10)]
    # y = [random.randint(1, 582)/10 for _ in range(10)]
    params = json.loads(request.data.decode('unicode_escape'))
    cell_id = params.get('cell_id', None)
    if cell_id < 0:
        return jsonify(["cell id not found, not abs position"]), 500
    try:
        grid_plot.update_plot(cell_id)
        print(f"{cell_id} has been updated")
        return jsonify(["success update cell done"]), 200
    except:
        traceback.print_exc()
        return jsonify(["cell id not found"]), 500


@devicebp.route('/campaign/new', methods=['GET'])
@role_required("user")
def start_campaign():
    running_campaign = find_all(current_app.config['CAMPAIGNS_COLLECTION'], filter={"status": "running"})
    if (len(running_campaign) > 0):
        title = 'Campaigns'
        allsources = current_app.config['SIDEBAR_MENU']
        calendars = current_app.config['SIDEBAR_MENU'][title][1]
        flash("Another campaign has been running!")
        # return redirect('management.html',
        #                        allsources=allsources, sourceId=0,
        #                        title=title, calendars=calendars, total=0,
        #                        eventTypeValues=eventTypeValues, isUser=False)
        return redirect(url_for('management.home', title='Campaigns'))

    post = None
    if os.path.exists('pcpfig.png'):
        os.remove('pcpfig.png')
    return render_template("events/device.html", post=post, eventTypeMap=eventTypeMap,
                           isUser=True, apiKey=current_app.config['GOOGLE_MAP_VIEW_KEY'],
                           timestamp=datetime.now().timestamp(),
                           timezones=Config.TIMEZONES,
                           extensions=",".join("." + extension for extension in Config.ALLOWED_PCP_FILE_EXTENSIONS),
                           # groupName=groupName
                           )


@devicebp.route('/stream')
@role_required("user")
def stream():
    campaign_id = request.args.get('campaign_id')
    stream_id = campaign_id
    print("stream " + str(stream_id) + " open")
    def generate():
        messenger = Messenger(campaign_id)
        # gen_fake_message(messenger)
        generator = None
        try:
            while True:
                generator = messenger.get_message()
                for data in generator:
                    print(f"data:" + data)
                    yield f"data:" + data + "\n\n"  # Format for SSE
        except GeneratorExit:
            traceback.print_exc()
            print("Client disconnected, cleaning up resources.")
        finally:
            generator.close()
            print("stream " + str(stream_id) +" CLOSED!")

    return Response(generate(), content_type='text/event-stream')
