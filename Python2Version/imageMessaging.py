# -*- coding: utf-8 -*-
"""
Created on Mon Feb 15 12:41:12 2016

@author: jeffrey.f.bryant
"""
import numpy as np
import cv2
import socket

packetSize = 65536-4 # Max payload size (65K - 4 header bytes)
UDP_IP = '0.0.0.0'
UDP_PORT = 5004
imageSocket = None
debugPrint = False

def init(host,port):
    
    """ Setup variables"""
    
    global UDP_IP,UDP_PORT,imageSocket

    UDP_IP = host
    UDP_PORT = port

    print "UDP target IP:", UDP_IP
    print "UDP target port:", UDP_PORT

    imageSocket = socket.socket(socket.AF_INET, # Internet
                                socket.SOCK_DGRAM) # UDP
                         
    print "Socket Setup:",imageSocket
    
    global blockPtr,blockList
    
def sendImage(img):
    """ 
    Encode an image into jpeg and send it to
    the UDP socket setup during init
    """

    global UDP_IP,UDP_PORT,imageSocket
    
    newImage = cv2.resize(img,(320,240))       
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
            
    if (rtn != None):
        decoded = cv2.imdecode(rtn,1)
    return decoded
        


if __name__ == '__main__':
    init('0.0.0.0',5004)
    imageSocket.bind((UDP_IP, UDP_PORT))
    while True:
        
        decoded = rcvImage()
        if (decoded != None):
            resized = cv2.resize(decoded,(640,480))
            cv2.imshow('DriverStation',resized)
        
        ch = 0xFF & cv2.waitKey(1)
        if ch == 27:
            break
        
    cv2.destroyAllWindows()    
        
    