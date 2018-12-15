#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
Created on Sat Feb 13 13:14:38 2016

@author: pi

This is the main PI collection package that captures images from the camera,
locates targets, reports them to the robot and forwards images to the drivers
station. This is only a main program and should not be imported.
"""

# import the necessary packages
import time
import sys
import argparse
import cv2
import socket
from picamera.array import PiRGBArray
from picamera import PiCamera
import FindTarget1 as ft
import driversStation as ds

def getArgs():
    """
    Command line arguement decoder 
    """
    print sys.argv
    parser = argparse.ArgumentParser(description='SHS Entropy Team 138 First 2016 Video Sensor')
    parser.add_argument('-ds', action='store',dest='ds',help='Driver Station host:port', default='10.1.38.6:5800')
    parser.add_argument('-r',action='store',dest='robot',help='Robot host:port',default='10.1.38.2:5802')
    parser.add_argument('-dp',action='store_true',dest='debugPrint',help='Enable debug print',default=False)
    parser.add_argument('-v',action='store_true',dest='showVideo',help='Enable local display of driver station video',default=False)
    parser.add_argument('-dv',action='store_true',dest='showDebugVideo',help='Enable local display of Debug video',default=False)
    parser.add_argument('-res',action='store',dest='resolution',help='Camera resolution (w,h)',default='(640,480)')
    parser.add_argument('-gain',action='store',dest='gain',type=float,help='Not Used Yet',default=1.0)
    parser.add_argument('-fr',action='store',dest='frameRate',type=int,help='Camera Frame Rate (FPS)',default=18)
    parser.add_argument('-bport',action='store',dest='bport',type=int,help='Discovery Broadcast Port',default=5804)
    
    args = vars(parser.parse_args())
    return args

def main():
    """
    Main program that loops forever
    """

    time.sleep(0.1)
    args = getArgs()
    sendReports = True
    ft.debugPrint = args['debugPrint']
    ft.showImages = args['showVideo']
    ft.showDebugImages = args['showDebugVideo']
    resolution = args['resolution'].split(',') # Convert from string in the format '(w,h)'
    resolution = int(resolution[0][1:]),int(resolution[1][:-1])
    
    cameraInit = False
    networkInit = False
    
    while not cameraInit or not networkInit:
    
        if not cameraInit:
            try:
        
                camera = PiCamera()
                
                # initialize the camera and grab a reference to the raw camera capture
                camera.resolution = resolution
                camera.framerate = int(args['frameRate'])
                rawCapture = PiRGBArray(camera, size=resolution)
                cameraInit = True
            except:
                print "Camera Exception"
                
        if not networkInit:
            try:
            
                hostPort = args['ds'].split(':')
                ds.init(hostPort[0],int(hostPort[1]))
                
                hostPort = args['robot'].split(':')
                ft.reportSetup(hostPort[0],int(hostPort[1]))
               
                broadcastSocket = socket.socket(socket.AF_INET, # Internet
                                socket.SOCK_DGRAM) # UDP
                broadcastSocket.setsockopt(socket.SOL_SOCKET,
	                       socket.SO_REUSEADDR,1)
                broadcastPort = args['bport']
                listen_addr = ("",broadcastPort)
                broadcastSocket.bind(listen_addr)
                broadcastSocket.setblocking(False)
                print "brodcast Port: ",broadcastPort
                print "Socket Setup: ",broadcastSocket
                
                networkInit = True
            except:
                print "Network Exception"
                
                 
        # allow the camera to warmup
        time.sleep(0.1)
     
    # capture frames from the camera
    for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
        # grab the raw NumPy array representing the image, then initialize the timestamp
        # and occupied/unoccupied text
        image = frame.array 
        collectTime = ft.currentTimeMs()
     
        # Simplest color processing
        # TODO: add tracking, adaptive processing that includes light control
        if ft.targetOn:
            targets = ft.processImage(image,[],-ft.detectThreshold,0,0)
        else:
            targets = []
        
        if sendReports:
            ft.sendReport(collectTime,targets)
            
        # show the frame (and forward to drivers station)
        ft.drawAnnotatedImage(image,targets)
        key = cv2.waitKey(1) & 0xFF
        
        # Perform message processing
        try:
            
            msg, addr = broadcastSocket.recvfrom(512)
            
            if (msg == ds.BroadcastData): # 'driverstation138'
                newIP = addr[0]
                if newIP != ds.UDP_IP:
                    print "Changing Video address= ",newIP
                    ds.init(newIP,ds.UDP_PORT,ds.messageResolution)
                    
            if (msg == 'robot138'):
                newIP = addr[0]
                if newIP != ft.UDP_IP:
                    print "Changing Report address= ",newIP
                    ft.reportSetup(newIP,ft.UDP_PORT)
                    
            if (msg == 'targetOn'):
                ft.targetOn = True
            
            if (msg == 'targetOff'):
                ft.targetOn = False
                
            if msg.find('detectThreshold') >= 0:
                fields = msg.split('=')
                thr = float(fields[1])
                if (thr >= 0.80) and (thr <= 0.99):
                    ft.detectThreshold = thr
                    
            if msg.find('showThreshold') >= 0:
                fields = msg.split('=')
                if (fields[1] == None):
                    timeout = 15
                else:
                    timeout = int(fields[1])
                if (timeout >= 0) and (timeout <= 30):
                    ft.displayThresholdMode(timeout*1000)
                    
        except:
            pass
     
        # clear the stream in preparation for the next frame
        rawCapture.truncate(0)
         
        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break
    
if __name__ == "__main__":
    main()

