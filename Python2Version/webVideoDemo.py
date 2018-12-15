#!/usr/bin/env python
#
# Project: Video Streaming with Flask
# Author: Log0 <im [dot] ckieric [at] gmail [dot] com>
# Date: 2014/12/21
# Website: http://www.chioka.in/
# Description:
# Modified to support streaming out with webcams, and not just raw JPEGs
# Modified by Jeff Bryant to support finding faces usin the OpenCV demo.
# Most of the code credits to Miguel Grinberg, except that I made a small tweak. Thanks!
# Credits: http://blog.miguelgrinberg.com/post/video-streaming-with-flask
#
# Usage:
# 1. Install Python dependencies: cv2, flask. (wish that pip install works like a charm)
# 2. Run "python main.py".
# 3. Navigate the browser to the local webpage.

import os
import cv2
from flask import Flask, render_template, Response


class VideoCamera(object):
    
    def __init__(self):
        # Using OpenCV to capture from device 0. If you have trouble capturing
        # from a webcam, comment the line below out and use a video file
        # instead.
        self.video = cv2.VideoCapture(0)
        # If you decide to use video.mp4, you must have this file in the folder
        # as the main.py.
        # self.video = cv2.VideoCapture('video.mp4')
        pdir = 'C:/Users/jeffrey.f.bryant/Desktop/FirstRobotics/haarcascades/'
        self.face_cascade = cv2.CascadeClassifier(pdir + 'haarcascade_frontalface_alt.xml')
        self.eye_cascade = cv2.CascadeClassifier(pdir + 'haarcascade_eye.xml')
        
    def __del__(self):
        self.video.release()
    
    def get_frame(self):
        success, image = self.video.read()
        # We are using Motion JPEG, but OpenCV defaults to capture raw images,
        # so we must encode it into JPEG in order to correctly display the
        # video stream.
        image = cv2.resize(image,(640,480))
        image = self.findFaces(image)
        newImage = cv2.resize(image,(320,240))       
        ret, jpeg = cv2.imencode('.jpg', newImage)
        return jpeg.tobytes()

    def findFaces(self,frame) :
    
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
               
        for (x,y,w,h) in faces:
            cv2.rectangle(frame,(x,y),(x+w,y+h),(255,0,0),2)
            roi_gray = gray[y:y+h, x:x+w]
            roi_color = frame[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray)
            for (ex,ey,ew,eh) in eyes:
                cv2.rectangle(roi_color,(ex,ey),(ex+ew,ey+eh),(0,255,0),2)
    
        return frame


app = Flask(__name__)


@app.route('/')
def index():
    loc = 'index.html'
    return render_template(loc)

 
def gen(camera):
    counter = 0
    while True:
        frame = camera.get_frame()
        counter = counter+1
        if (counter > 3):
            counter = 0;
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print os.curdir
    app.run(host='0.0.0.0', debug=True)
