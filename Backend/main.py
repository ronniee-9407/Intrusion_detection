import time
import json
import base64
import cv2
import numpy as np
import tensorflow as tf

from flask import Flask, request
from flask_cors import CORS
from flask_sockets import Sockets
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from datetime import date, datetime, timedelta
from threading import Thread
import os
import gevent
import database
import jsw_intrusion_plc
import socket


app = Flask(__name__)
sockets = Sockets(app)
cors = CORS(app, resources={r"/*": {"origins": "*"}})
intrusion_img_path = "D:/Intrusion Images"

mydb = database.datbase_connection()
my_cursor = mydb.cursor()
table_name = "detect_intrusion"

## Connect to the plc.
instrument = jsw_intrusion_plc.connect_plc(com_port="COM3")
class_map = { 1: "Person", 2: "Crane Hook", 3: "Crane Motor" }


## Capture cam using thread
class VideoCaptureThread():
    def __init__(self, device_ip):
        self.device_ip = device_ip
        self.cap = cv2.VideoCapture(self.device_ip)
        self.ret, self.frame = self.cap.read()

    def start_thread(self):
        Thread(target=self.update_frame, args=()).start()
        print("Cam thread starts.")
        return self

    def reconnect_cam(self):
        self.cap = cv2.VideoCapture(self.device_ip)
        time.sleep(0.01)

    def update_frame(self):
        while True:
            self.ret, self.frame = self.cap.read()
            if not self.ret:
                print("Camera is Not  connected. Trying to reconnect...")
                self.reconnect_cam()
                time.sleep(1)
            time.sleep(0.01)

    def get_frame(self):
        return self.frame


class IntrusionDetection():
    def __init__(self, model_path):
        self.plc_input = 0
        self.prev_time = datetime(2022, 10, 20, 11, 54, 10, 62506)  
        self.model_path = model_path
        self.detect_fn = tf.saved_model.load(self.model_path)
        print("[!] Model loaded successfully")
        try:
            with open('latest_roi.json', 'rb') as fp: self.roi_pts = json.load(fp)
        except:
            print("No roi points found...")
            self.roi_pts = [[219, 114], [418, 165], [466, 270], [531, 243], [579, 239], [605, 216], [549, 133], [343, 87], [298, 92], [240, 97]]
            # [[1, 2], [2, 2], [2, 3], [1, 3], [1, 2]]


    ## Detect Objects for Single frame/image 
    def detect_intrusion(self, frame, min_score=0.4, max_boxes=20, image_resize=(640, 480), is_demo=True):
        filename = "" 
        snap_time = 0 
        intrusion_per_frame = 0

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_batch = np.expand_dims(frame_rgb, 0)
        
        detections = self.detect_fn(frame_batch)
        boxes = detections['detection_boxes'][0].numpy()
        scores = detections['detection_scores'][0].numpy()
        class_ids = detections['detection_classes'][0].numpy().astype(int)
        
        ##################################################################################
        try:
            person_index = tf.where(tf.equal(class_ids, 1)) 
            person_boxes = tf.squeeze(tf.gather(boxes, person_index))
            person_scores = tf.squeeze(tf.gather(scores, person_index))
            person_class_id = tf.squeeze(tf.gather(class_ids, person_index))

            selected_indices = tf.image.non_max_suppression(person_boxes, person_scores, max_output_size=max_boxes, iou_threshold=0.5)
            person_boxes = tf.gather(person_boxes, selected_indices).numpy()
            person_scores = tf.gather(person_scores, selected_indices).numpy()
            person_class_id = tf.gather(person_class_id, selected_indices).numpy().astype(np.int16)

            crane_index = tf.where(tf.greater(class_ids, 1)) 
            crane_boxes = tf.squeeze(tf.gather(boxes, crane_index))
            crane_scores = tf.squeeze(tf.gather(scores, crane_index))
            crane_class_id = tf.squeeze(tf.gather(class_ids, crane_index)).numpy().astype(np.int16)

            crane_selected_idxs = tf.image.non_max_suppression(crane_boxes, crane_scores, max_output_size=max_boxes, iou_threshold=0.1)
            crane_boxes = tf.gather(crane_boxes, crane_selected_idxs).numpy()
            crane_scores = tf.gather(crane_scores, crane_selected_idxs).numpy()
            crane_class_id = tf.gather(crane_class_id, crane_selected_idxs)

            boxes = np.append(person_boxes, crane_boxes, 0)
            scores = np.append(person_scores, crane_scores, 0)
            class_ids = np.append(person_class_id, crane_class_id, 0)
        except:
            print("Not using Non Max Suppression")
        #################################################################################

        ## Define Restricted area 
        frame_rgb = cv2.resize(frame_rgb, image_resize)
        frame_rgb = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        img_overlay = frame_rgb.copy()
        out_frame = frame_rgb.copy()
        img_with_poly = cv2.fillPoly(img_overlay, pts=[np.array(self.roi_pts)], color=(0, 0, 255))
        frame_rgb = cv2.addWeighted(out_frame, 0.5, img_with_poly, 0.5, 1.0)
        
        ## Draw BBox on frames
        num_intrusion = []
        im_height, im_width, channels = frame_rgb.shape
        for i in range(min(boxes.shape[0], max_boxes)):
            if scores[i] >= min_score:
                ymin, xmin, ymax, xmax = tuple(boxes[i])
                (left, right, top, bottom) = (int(xmin * im_width), int(xmax * im_width), int(ymin * im_height), int(ymax * im_height))

                ## Draw crane bbox
                if class_ids[i] != 1:
                    cv2.rectangle(frame_rgb, (left, top), (right, bottom), (255, 0, 0), 4)
                    display_str = f"{class_map[class_ids[i]]}"#: {int(scores[i] * 100)}%"
                    frame_rgb = cv2.putText(frame_rgb, display_str, (left, bottom + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

                ## Draw person bbox
                if class_ids[i] == 1:
                    all_roi_pts = self.roi_pts
                    all_roi_pts.append((all_roi_pts[0]))
                    rl1 = cv2.pointPolygonTest(np.array(all_roi_pts), (left, bottom), False)
                    rl2 = cv2.pointPolygonTest(np.array(all_roi_pts), (right, bottom), False)
                    if rl1 == 1 or rl2 == 1 :
                        rl = 1
                        color = (0, 0, 255)
                        num_intrusion.append(rl)
                        
                        # ## Send ON signal to PLC.
                        # self.plc_input = 1
                        # try:
                        #     instrument.write_bit(1281, self.plc_input)
                        # except:
                            
                        #     print("[!] Failed to send ON single to the PLC.")
                        # # print(instrument.read_bit(1281))
                    else:   
                        rl = 0
                        color = (0, 255, 0)

                        # self.plc_input = 0
                        # try:
                        #     instrument.write_bit(1281, self.plc_input)
                        # except:
                        #    print("[!] Failed to send OFF single to the PLC.")
                        

                    cv2.rectangle(frame_rgb, (int(left), int(top)), (int(right), int(bottom)), color, 4)
                    display_str = f"{class_map[class_ids[i]]}"#: {int(scores[i] * 100)}%"
                    frame_rgb = cv2.putText(frame_rgb, display_str, (left, bottom + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                    
        if not is_demo:
            intrusion_per_frame = int(np.sum(np.array(num_intrusion)))
            if intrusion_per_frame > 0:

                # Send ON signal to PLC.
                self.plc_input = 1
                try:
                    instrument.write_bit(1281, self.plc_input)
                except:
                    pass
                    # print("[!] Failed to send ON single to the PLC.")

                datetimestamp = datetime.now()
                datetime_now = datetimestamp.strftime('%Y-%m-%d %H:%M:%S')
                skip_time = self.prev_time + timedelta(seconds=5)
                if datetimestamp >= skip_time:
                    self.prev_time = datetimestamp
                    date_today = datetimestamp.strftime("%Y-%m-%d")       
                    folder_path = f"{intrusion_img_path}/{date_today}"
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                    filename = datetimestamp.strftime("%Y%m%d%H%M%f")[:-4]
                    cv2.imwrite(f"{folder_path}/{filename}.jpg", frame_rgb)

                    ## write data to mysql
                    sql = "insert into detect_intrusion (date_time, cam_name, img_id, num_intrusion) values (%s, %s, %s, %s)" 
                    val = (datetime_now, str("Cam 1"), str(filename), intrusion_per_frame)
                    my_cursor.execute(sql, val)
                    mydb.commit()
                    snap_time = datetime_now
                else:
                    intrusion_per_frame = 0

            else:
                self.plc_input = 0
                try:
                    instrument.write_bit(1281, self.plc_input)
                except:
                    pass
                    # print("[!] Failed to send OFF single to the PLC.")

        return frame_rgb, intrusion_per_frame, snap_time, filename
        
    
    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(('10.254.254.254', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = None
        finally:
            s.close()
            return IP
                

#######################################################################################################################################
########################################################## Flask Api call #############################################################

device_ip = "rtsp://service:Jswhsm2_280310@192.168.0.108:554/?h26x=4"
video_path = r"D:\\JSW Intrusion Detection\\Backend\\Sample Data\\1667723115.mp4" 
model_path = r"D:\JSW Intrusion Detection\Backend\DL Model\efficientdet_d1_45000"

## Initialize the class
intrusion = IntrusionDetection(model_path)
## Initialize the camera
intrusion_cap = VideoCaptureThread(device_ip)
intrusion_cap.start_thread()

fps = 120/1
frame_width = 640 #1920
frame_height = 480 #1080
gst_out = "appsrc ! video/x-raw ! queue ! videoconvert ! x264enc ! video/x-h264, stream-format=avc, alignment=au, profile=constrained-baseline !" \
        "h264parse ! rtspclientsink location=rtsp://192.168.2.99:8554/test"
out = cv2.VideoWriter(gst_out,  cv2.CAP_GSTREAMER, 0,  fps, (frame_width, frame_height), True)

# fourcc = cv2.VideoWriter_fourcc(*'XVID')
# video_name = f'Output Video/{int(time.time())}.avi'
# out = cv2.VideoWriter(video_name, fourcc, 20, (frame_width, frame_height))

if not out.isOpened():
    raise Exception("can't open video writer!")


## Live Video Page
@sockets.route('/intrusionVideo')
def detection_video(ws): 
    while True:
        frame = intrusion_cap.get_frame()
        if frame is not None:
            frame_rgb, num_intrusion, snap_time, image_id = intrusion.detect_intrusion(frame, is_demo=False)
            base64_img = base64.b64encode(cv2.imencode('.bmp', frame_rgb)[1].tobytes())
            encoded_img = base64_img.decode('ascii') 
            cam_status = 1  ## Camera is connected."
            data = {
                "encoded_img": encoded_img,
                "cam_status": cam_status,
                "num_intrusion": num_intrusion,
                "snap_time": snap_time, 
                "image_id": image_id
                }
            ws.send(json.dumps(data))
            # frame_rgb = cv2.resize(frame_rgb, (1920, 1080))
            out.write(frame_rgb)
            gevent.sleep(0.01)
        else:
            data = {
                "encoded_img": [],
                "cam_status": 0,  ## Camera is not connected!!!
                "num_intrusion": 0,
                "snap_time": 0,
                "image_id": 0
            }
            ws.send(json.dumps(data))
            gevent.sleep(0.01)


@sockets.route('/dbStatus')
def database_status(ws):
    while True:
        s = mydb.is_connected()
        if s == True:
            db_status = 1  ## Database is connected."
        else:
            db_status = 0  ## Database is not connected."
        data = {
                "db_status": db_status
                }
        ws.send(json.dumps(data))
        gevent.sleep(300)


@app.route('/saveROI', methods=["POST"])
def send_roi_page():
    intrusion.roi_pts = request.json['spotArray']
    with open("latest_roi.json", "w") as fp: json.dump(intrusion.roi_pts, fp)
    print(f"User selected ROI points: {intrusion.roi_pts}")
    response = app.response_class(
        status=200,
        mimetype='application/json'
    )
    return response


@app.route('/defaultROI', methods=["GET"])
def default_roi_page():
    intrusion.roi_pts = [[219, 114], [418, 165], [466, 270], [531, 243], [579, 239], [605, 216], [549, 133], [343, 87], [298, 92], [240, 97]]
    print(f"Default ROI called: {intrusion.roi_pts}")
    response = app.response_class(
        status=200,
        mimetype='application/json'
    )
    return response


@sockets.route('/roiDemoVideo')
def detection_video(ws):
    cap= cv2.VideoCapture(r"D:\JSW Intrusion Detection\Backend\Demo ROI\demo_video.mp4")
    while True:
        ret, frame = cap.read()
        if ret == True:
            frame, _, _, _ = intrusion.detect_intrusion(frame)
            base64_img = base64.b64encode(cv2.imencode('.bmp', frame)[1].tobytes())
            encoded_img = base64_img.decode('ascii') 
            data = {"encoded_imgg": encoded_img}
            ws.send(json.dumps(data))
            gevent.sleep(0.01)
            
        else:
            ws.close()
            print("Websocket closed!")
            break
        time.sleep(0.01)

    
## Data Analysis Page
@app.route('/searchDateTime', methods=["GET", "POST"])
def search_dateTime_page():
    query = request.json['query']
    print(f"Date-Time query received: {query}")
    start_date = query[0] +" "+query[2]+":00"
    end_date =  query[1] +" "+query[3]+":00"
    DBtimedata = database.getQuery(my_cursor, start_date, end_date)
    response = app.response_class(
        json.dumps(DBtimedata),
        status=200,
        mimetype='application/json'
    )
    return response


@app.route('/showImg', methods=["GET", "POST"])
def show_image():
    datetime = request.json['dateTime']
    image_id = request.json['imageID']
    date_folder = datetime.split(" ")[0]
    img_file = f"{intrusion_img_path}/{date_folder}/{image_id}.jpg"
    bgr_img = cv2.imread(img_file)
    encoded_image = base64.b64encode(cv2.imencode('.jpg', bgr_img)[1].tobytes()).decode('ascii') 
    response = app.response_class(
        json.dumps(encoded_image),
        status=200,
        mimetype='application/json'
    )
    return response


####################################################################################################
################################################ Server Starts #####################################

if __name__ == "__main__":
    # Thread(target=write_to_plc, args=(intrusion.plc_input,)).start()
    server = pywsgi.WSGIServer(('0.0.0.0', 4000), app, handler_class=WebSocketHandler)
    print(f"[!] Server Started at: {intrusion.get_ip_address()}:4000")
    server.serve_forever()
