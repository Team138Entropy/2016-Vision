# -*- coding: utf-8 -*-
"""
Created on Thu Sep 01 13:26:46 2016

@author: jeffrey.f.bryant

TODO: Integrate with RASPBERRY PI Mainline

"""
from multiprocessing import Process, Queue
import time
import sys
import cv2
import FindTarget1 as ft

regions = [
    
    (0.25,0.25,0.5), # Center
    
    (0.0,0.25,0.5),  # Left and right of center
    (0.5,0.25,0.5),

    (0.25,0.0,0.5),  # Top center,left,right
    (0.0,0.0,0.5),
    (0.5,0.0,0.5)

    ]
    
def init():
    global workerLastTasked,lastTarget,tracking,outstandingRequests

    workerLastTasked = 0
    lastTarget = None
    tracking = False
    outstandingRequests = {}

    
class request:
    
    def __init__(self,timestamp,numberAssignments):
        self.timestamp = timestamp
        self.numberAssignments = numberAssignments
        self.results = []
        
    
def worker(index,inqueue,outqueue):
    """
    Main function to process an image; performed in the context
    of a subprocess
    """
    done = False
    print "Worker Started: ",index
    sys.stdout.flush()
    while not done:
        msg = inqueue.get()
        if (msg[0] <= 0.0):
            done = True
            break
        
        #valid request; decode the message
        timestamp = msg[0]
        img = msg[1]
        outline = msg[2]
        threshold = msg[3]
        
        # process the image and queue the results
        targets = ft.processImage(img,0,threshold,outline[0],outline[1])
        retMsg = [timestamp,targets]
        outqueue.put(retMsg)
        sys.stdout.flush()

def makeProcesses(nChildren):
    """
    Create and start all the worker processes
    """
    global taskQueue,resultsQueue,workers
    
    if nChildren < 0:
        print 'makeProcesses: ',nChildren, ' is too small'
        return False
    if nChildren > 3:
        print 'makeProcesses: ',nChildren, ' is too large'
        return False
    
    # Create a task queue for each worker to receive the image segment    
    taskQueue = []
    for k in range(nChildren):
        taskQueue.append(Queue())
    resultsQueue = Queue() # Single results queue
    
    #Create and start the workers
    workers = []
    for k in range(nChildren):
        p = Process(target=worker, args=(k,taskQueue[k],resultsQueue))
        workers.append(p)
    for p in workers:
        p.start()
        
    time.sleep(2)
        
    return True
        

def shutdown():
    """
    Request all the workers to stop and wait for them to finish
    """
    global taskQueue,workers
    
    for k in taskQueue:
        msg = [0.0,'Done']
        k.put(msg)
    for k in workers:
        k.join()
        
        
def taskAcq(timestamp,img):
    """
    Task the workers in acquisition mode by splitting the camera image into
    segments and dealing them out to the workers
    
    TODO: Check for any busy and skip tasking
    """
    
    global workerLastTasked,outstandingRequests
    n = 0
   
    # Keep a place for the results
    task = request(timestamp,len(regions))
    print task.timestamp,task.numberAssignments
    outstandingRequests[timestamp] = task
    
    # Split the image and send it to the workersn
    for r in regions:
        w,h,c = img.shape
        left = int(r[0] * w)
        top = int(r[1] * h)
        width = int(r[2] * w)
        height = int(r[2] * h)
        rect = (left,top,width,height)
        img1 = img[top:top+width,left:left+height] 
        
        msg = [timestamp,img1,rect,ft.detectThreshold]        
        q = taskQueue[n]
        q.put(msg)
        workerLastTasked = n
        
        n = n + 1;
        if n >= len(taskQueue):
            n = 0
            
            
def checkForNewResults():
    
    """
    Check the results queue from the workers and update the outstandingRequests
    data structure. If all workers have finished then return the complete list
    of results. Otherwise return None
    """
    
    global outstandingRequests
    
    allTargets = None
    while not resultsQueue.empty():
        msg = resultsQueue.get()
        timestamp = msg[0]
        task = outstandingRequests[timestamp]
        if task == None:
            print "Task not found for: ",timestamp
        else:
            task.results.append(msg)
            
            # finished all image for the collection;
            if len(task.results) >= task.numberAssignments :
                matchTargets = []
                nomatchTargets = []
                for r in task.results:
                    targets = r[1]
                    
                    for t in targets:
                        if t['match']:
                            matchTargets.append(t)
                        else:
                            nomatchTargets.append(t)

                    allTargets = []       
                    for t in matchTargets:
                        allTargets.append(t)
                    for t in nomatchTargets:
                        allTargets.append(t)
            
        return allTargets        
        
def completeImage(timestamp,img):
    
    """
    Test function to process a complete image
    """
    
    # Flush the queue to start
    while not resultsQueue.empty():
        resultsQueue.get()
        
    #Start the processing
    taskAcq(timestamp,img)
    
    for k in range(10):
        time.sleep(0.1)
        allTargets = checkForNewResults()
        if (allTargets != None):
            break
    return allTargets
    

def taskTrack(timestamp,target,img):
    """
    Task the next worker to process an image segmet around the last detected
    target. The workers are tasked as a round robin sequence
    
    TODO: Check for all busy and skip tasking
    
    """
    
    global workerLastTasked,outstandingRequests
        
    nextTotask = workerLastTasked + 1
    if nextTotask >= len(taskQueue):
        nextTotask = 0
        
    # Compute the region of interest (+- 50 %)
    region = target['bounds']
    extraw = int(0.5 * region[2])
    extrah = int(0.5 * region[3])
    left= int(region[0] - extraw)
    top = int(region[1] - extrah)
    width = int(region[2] + extraw*2)
    height = int(region[3] + extrah*2)
   
    
    # Clip the search area to the inside of the image
    if (left < 0): left = 0
    if (top < 0): top = 0
    right = left+width
    bottom = top+height
    (maxh,maxw,ncolors) = img.shape
    if (right > maxw):
        width = width - (right-maxw)
    if (bottom > maxh):
        height = height - (bottom-maxh)        
        
    rect = (left,top,width,height)
    img1 = img[top:top+height,left:left+width]
    msg = [timestamp,img1,rect,ft.detectThreshold]

    # Keep a place for the results
    task = request(timestamp,1)    
    outstandingRequests[timestamp] = task
     
    q = taskQueue[nextTotask]
    q.put(msg)
    workerLastTasked = nextTotask  
        
def track(timestamp,target,img):
    """
    Test the track function.
    """
    # Flush the queue to start
    while not resultsQueue.empty():
        resultsQueue.get()
                
    #Start the processing
    taskTrack(timestamp,target,img)
    for k in range(50):
        time.sleep(0.1)
        allTargets = checkForNewResults()
        if (allTargets != None):
            break
       
    return allTargets
    
    
def displayResults(targets,img):
    """ 
    Debug display of the results
    """
    
 
    if (targets != None) :
        dispTargets = targets
    else:
        dispTargets = []
        
    if len(dispTargets) > 0:
        for t in targets:
            ft.printTgt(t)

    ft.displayThresholdTimeout = 0;
    ft.showImages = True
    ft.drawAnnotatedImage(img,dispTargets)
             
    done = False
    startTime = ft.currentTimeMs()
    while not done:
        
        ch = 0xFF & cv2.waitKey(1)
        
        if ch == 27:
            done = True  
            
        curTime = ft.currentTimeMs()
        if (curTime - startTime) > 1000:
            done = True
            
def bestTarget(targets):
    """
    Return the best target is a list where best is defined as the widest with
    the match indicator set
    """
    maxw = 0
    found = False
    if (targets == None)  or len(targets) == 0 :
        return False,None
        
    best = targets[0]
    for t in targets:
           width = t['bounds'][2]
           if t['match'] and width > maxw:
               maxw = width
               best = t
               found = True
    return found,best
    

if __name__ == '__main__':
    """
    Test program
    """
    init()
    makeProcesses(3)
    print "Workers Ready"
  
    imgDir = 'C:\\Users\\jeffrey.f.bryant\\Desktop\\FirstRobotics\\vision\\Images\\'
    imgInput = cv2.imread(imgDir + '5.JPG')
    imgCopy = imgInput.copy()
    collectTime = ft.currentTimeMs()
    
    targets = completeImage(collectTime,imgInput)
    displayResults(targets,imgInput)
    
    print
    print '-----------------------Track --------------------'
    print
    
    found, best = bestTarget(targets)
    if (found):
        
        for k in range(4):
            imgInput = imgCopy.copy()
            collectTime = ft.currentTimeMs()
            targets = track(collectTime,best,imgInput)
            displayResults(targets,imgInput)
  

    print "Shutdown: ",len(outstandingRequests)
    shutdown()
    print 'Finished'