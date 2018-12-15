# -*- coding: utf-8 -*-
"""
Created on Sat Feb 13 21:34:27 2016

@author: pi

Test UDP server to print out messages that are sent to the robot
"""

import sys
import argparse

import socket
UDP_Port = 5802

def getArgs():
    """
    Command line arguement decoder 
    """
    print sys.argv
    parser = argparse.ArgumentParser(description='SHS Entropy Team 138 First 2016 Robot Message Display')
    parser.add_argument('-port', action='store',dest='port',help='Listen Port ', default=5804)
    
    args = vars(parser.parse_args())
    return args
    
if __name__ == "__main__":

    # A UDP server
    args = getArgs()
    UDP_Port = int(args['port'])
    
    # Set up a UDP server
    UDPSock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    
    # Listen on port 21567
    # (to all IP addresses on this system)
    listen_addr = ("",UDP_Port)
    UDPSock.bind(listen_addr)
    
    print "Robot Listening on Port= ",UDP_Port
    
    # Report on all data packets received and
    # where they came from in each case (as this is
    # UDP, each may be from a different source and it's
    # up to the server to sort this out!)
    while True:
            data,addr = UDPSock.recvfrom(1024)
            print
            print data.strip(),addr
