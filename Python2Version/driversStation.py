# -*- coding: utf-8 -*-
"""
Created on Mon Feb 15 12:41:12 2016

@author: jeffrey.f.bryant
"""
import numpy as np
import cv2
import socket
import argparse
import time
import subprocess
import traceback
import sys

packetSize = 65536-4 # Max payload size (65K - 4 header bytes)
UDP_IP = '0.0.0.0'
UDP_PORT = 5800
BroadcastData = 'driverstation138'
imageSocket = None
debugPrint = False
displayResolution = (640,480)
messageResolution = (320,240)
#piAddr = '10.01.38.14'
piAddr = '10.1.38.11'
detectThreshold = 0.95

def getArgs():
    """
    Command line arguement decoder 
    """
    parser = argparse.ArgumentParser(description='SHS Entropy Team 138 First 2016 Driver Station Display')
    parser.add_argument('-port', action='store',dest='port',help='Listen Port ', default=UDP_PORT)
    parser.add_argument('-bport', action='store',dest='bport',help='Broadcast Port ', default=5804)    
    parser.add_argument('-res',action='store',dest='resolution',help='Display Resolution (w,h)',default='(640,480)')
    parser.add_argument('-pi',action='store',dest='piAddr',help='PI Vision Processor IP',default=piAddr)
    
    args = vars(parser.parse_args())
    return args

def init(host="localhost",port=5800,resolution=(320,240)):
    
    """ Setup variables"""
    
    global UDP_IP,UDP_PORT,imageSocket,messageResolution
    
    UDP_IP = host
    UDP_PORT = port
    messageResolution = resolution
 
    print "UDP target IP:", UDP_IP
    print "UDP target port:", UDP_PORT

    imageSocket = socket.socket(socket.AF_INET, # Internet
                                socket.SOCK_DGRAM) # UDP
    imageSocket.setsockopt(socket.SOL_SOCKET,
	                       socket.SO_REUSEADDR,1)
    imageSocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
                         
    print "Socket Setup:",imageSocket
    
    
def joinGroup(mcastAddr):
    """
    Configure a socket to listen to a specified multicast address
    """
    ok = True
    try:
        mreq = struct.pack("=4sl", socket.inet_aton(mcastAddr), socket.INADDR_ANY)
        imageSocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except:
        ok = False
    return ok
   
def hostsOnNetwork():
    """
    Windows function to list all the hosts on a LAN
    """
    os.system('net view > conn.tmp')
    f = open('conn.tmp', 'r')
    f.readline();f.readline();f.readline()
    
    conn = []
    host = f.readline()
    while host[0] == '\\':
        conn.append(host[2:host.find(' ')])
        host = f.readline()
    
    f.close()
    return conn
    
    
def pingHost(host):
    """
    Ping a host (windows or linux)
    """
    found = False
    try:
        if (sys.platform == 'win32'):
            ping = subprocess.Popen(
                ["ping", "-n", "1","-w","2500", host],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE)
        else:
           ping = subprocess.Popen(
                ["ping", "-c", "1","-w","2500", host],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE)              
                
        out, error = ping.communicate()
        lines = out.split('\n')
       
        if str.find(lines[2],'Reply') >= 0:
            found = True
    except:
        print 'Ping Exception on ', host
        
    return found
    


def myIP():
    """
    Return the IP for this node
    """
    
    ipsToTry = [piAddr,'192.168.1.1','10.1.38.1']
    localIpAddress = None
    
    # Try using intrinsic calls
    for k in ipsToTry:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((k, 0))  # connecting to a UDP address doesn't send packets
            localIpAddress = s.getsockname()[0]
            break
        except:
            print '------ myIP() except using-----------:  ',k
            traceback.print_exc(file=sys.stdout)
            
    
    # If hat did not work then query the OS
    if (localIpAddress == None):
        try:
            status = subprocess.Popen(
                ["ipconfig"],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE
            )  
            out, error = status.communicate()
            lines = out.split('\n')
            
            starts = []
            n = 0
            for k in lines:
                if k.find('Ethernet adapter Local Area Connection') >= 0:
                    starts.append(n)
                n = n + 1
            for k in starts:
                test = lines[k+3]
                fields = test.split(':')
                if len(fields) > 0 and fields[0].find('IPv4') >= 0:
                    localIpAddress = fields[1].strip()
                    return localIpAddress
        except:
            print '------ myIP() except using ipconfig ----------'
            traceback.print_exc(file=sys.stdout)
        
    
    # If that does not work then set it to local
    if localIpAddress == None:
        localIpAddress = 'localhost'
            
    return localIpAddress   
    
    
def splashScreen():
    """
    Display a statup screen that shows what is going on until
    packets are received.
    """
    
    # Create a black image
    img = np.zeros((displayResolution[1],displayResolution[0],3), np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    robotUp = pingHost(piAddr)
    if (robotUp):
        cv2.putText(img,'Sucessfull ping to PI at: ' + piAddr,(10,35), font, 1,(255,255,0),1,cv2.LINE_AA)
    else:
        cv2.putText(img,'PI Ping Error: ' + piAddr,(10,35), font, 1,(255,255,0),1,cv2.LINE_AA)
        
    addr = myIP() + ':' + str(UDP_PORT)
   
    cv2.putText(img,'Listening on: ' + addr,(10,75), font, 1,(255,255,255),1,cv2.LINE_AA)
    
    tstring = time.asctime()[11:19]
    cv2.putText(img,tstring,(10,120), font, 1,(255,255,255),1,cv2.LINE_AA)
     
    cv2.imshow('DriverStation',img)
    
def sendImage(img):
    """ 
    Encode an image into jpeg and send it to
    the UDP socket setup during init
    """

    global UDP_IP,UDP_PORT,imageSocket
    
    newImage = cv2.resize(img,messageResolution)       
    ret, data = cv2.imencode('.jpg', newImage)
    if (debugPrint):
        print "OrigSize=",img.size,"EncodedSize = ", data.size
    
    nPackets = ((data.size-1) / packetSize) + 1
    for k in range(nPackets):
 
        start = k*packetSize
        end =   (k+1)*packetSize
        if (end > data.size):
            end = data.size
            
        blockSize = end-start
        block  = np.zeros((blockSize+4,1),dtype=np.uint8)
        block[0] = np.uint(nPackets)
        block[1] = np.uint(k+1)
        block[2] = blockSize/256
        block[3] = blockSize%256
        block[4:] = data[start:end]
        
        if (imageSocket != None):
            imageSocket.sendto(block.tobytes(), (UDP_IP, UDP_PORT))

        
def rcvImage():
    """
    Receive an image as a series of encoded mjpeg packets
    place them back togather and decode the image into a
    cv2 image
    """
    global UDP_IP,UDP_PORT,imageSocket
    
    imageSocket.settimeout(0.5)
    done = False
    rtn = None
    decoded = None
    while not done:
        try:
            block, addr = imageSocket.recvfrom(65536) # buffer size is 1024 bytes
            imageSocket.settimeout(0.01)
        except:
            break
        block = np.fromstring(block, dtype=np.uint8)
        npackets = block[0]
        packetNum = block[1]
        nBytes = block[2] * 256 + block[3]
        if (rtn == None):
            if (packetNum != 1):
                break
            rtn = block[4:]
        else:
            rtn = np.append(rtn,block[4:])
        if (debugPrint):
            print "Rcv: ",npackets,packetNum,nBytes
        if (npackets == packetNum):
            done = True
            
    csize = 0
    if rtn is not None:
        csize = len(rtn)
        decoded = cv2.imdecode(rtn,1)
    return decoded,csize
        
def sendThreshold(newThr):
    """
    Send the detection threshold to the video processor
    """
    s = 'detectThreshold=' + str(newThr)
    print s
    broadcastSocket.sendto(s,('255.255.255.255',broadcastPort))
    broadcastSocket.sendto(s,(piAddr,broadcastPort))
    broadcastSocket.sendto('showThreshold=5',('255.255.255.255',broadcastPort))
    broadcastSocket.sendto('showThreshold=5',(piAddr,broadcastPort))
        
if __name__ == '__main__':
    """
    Mainline program to receive image packets
    and display them.
    """
    alpha = .9
    beta = (1.0-alpha)
    
    args = getArgs()
    port = int(args['port'])
    broadcastPort = int(args['bport'])
    piAddr = args['piAddr']
    init('0.0.0.0',port)
    imageSocket.bind((UDP_IP, port))
    
    broadcastSocket = socket.socket(socket.AF_INET, # Internet
                                socket.SOCK_DGRAM) # UDP
    broadcastSocket.setsockopt(socket.SOL_SOCKET,
	                       socket.SO_REUSEADDR,1)
    broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                        
    lastBroadcast = time.clock()
    
    fps = 0.0
    bps = 0.0
    lastPacketTime = time.clock()
 
    displayResolution = args['resolution'].split(',') # Convert from string in the format '(w,h)'
    displayResolution = int(displayResolution[0][1:]),int(displayResolution[1][:-1])
    
    print "listening on = ",myIP(),':',port
    print "Image size = ",displayResolution
    splashScreen()
    firstPacket = False
    
    while True:
        
        try:
            deltaBroadcast = time.clock() - lastBroadcast
            if (deltaBroadcast > 1.0):
                lastBroadcast = time.clock()
                broadcastSocket.sendto(BroadcastData,('255.255.255.255',broadcastPort))
                broadcastSocket.sendto(BroadcastData,(piAddr,broadcastPort))
                
                # DEBUG ONLY 
                #broadcastSocket.sendto('robot138',('255.255.255.255',broadcastPort))
                #broadcastSocket.sendto('robot138',(piAddr,broadcastPort))
                
            decoded,compressedSize = rcvImage()
            if decoded is not None:
                resized = cv2.resize(decoded,displayResolution)
                now = time.clock()
                delta = now-lastPacketTime
                lastPacketTime = now
                if (delta > 0.0):
                    fps = alpha * fps + beta/delta
                    bps = alpha * bps + beta * compressedSize/delta
                    fpsString ='FPS: %5.2f BPS: %5.2f M' % (fps,bps*8.0/1000000.0)
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    cv2.putText(resized,fpsString,(10,25), font, 1,(255,255,255),1,cv2.LINE_AA)
                firstPacket = True
                cv2.imshow('DriverStation',resized)
            else:
                if not firstPacket:
                    splashScreen()
            
            ch = 0xFF & cv2.waitKey(1) # Allow the display to refresh
            
            if ch == 27: #ESC exits
                break
            
            if (ch != 255):
                print int(ch)
            
            if (ch == ord('o')):
                print "Targeting On"
                broadcastSocket.sendto('targetOn',('255.255.255.255',broadcastPort))
                broadcastSocket.sendto('targetOn',(piAddr,broadcastPort))
                                
            elif (ch == ord('f')):
                print "Targeting Off"
                broadcastSocket.sendto('targetOff',('255.255.255.255',broadcastPort))
                broadcastSocket.sendto('targetOff',(piAddr,broadcastPort))
                
            elif (ch == ord('t')):
                print "Threshold Display"
                broadcastSocket.sendto('showThreshold=08',('255.255.255.255',broadcastPort))
                broadcastSocket.sendto('showThreshold=08',(piAddr,broadcastPort))

            elif (ch == ord('u')):
                detectThreshold = detectThreshold + .01
                if (detectThreshold > .99):
                    detectThreshold = .99
                sendThreshold(detectThreshold)
 
            elif (ch == ord('d')):
                detectThreshold = detectThreshold - .01
                if (detectThreshold < 0.8):
                    detectThreshold = 0.8
                sendThreshold(detectThreshold)
 
        except:
            print "Exception in Main:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60
            ch = 0xFF & cv2.waitKey(500)
            if ch == 27:
                break            
               
    cv2.destroyAllWindows()    
        
    