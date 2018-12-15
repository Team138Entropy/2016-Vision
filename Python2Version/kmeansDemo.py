# -*- coding: utf-8 -*-
"""
Created on Wed Jan 13 16:27:31 2016

@author: jeffrey.f.bryant
"""

import numpy as np
import cv2

#filename = '..\\First2016\\RealFullField\\282.jpg'
#filename = '..\\First2016\\animationSnap.JPG'
#filename = '..\\First2016\\find_target_2.jpg'
filename = '..\\First2016\\field1.JPG'

img = cv2.imread(filename)
Z = img.reshape((-1,3))

# convert to np.float32
Z = np.float32(Z)

# define criteria, number of clusters(K) and apply kmeans()
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
K = 6
ret,label,center=cv2.kmeans(Z,K,None,criteria,10,cv2.KMEANS_RANDOM_CENTERS)

# Now convert back into uint8, and make original image
center = np.uint8(center)
res = center[label.flatten()]
res2 = res.reshape((img.shape))

cv2.imshow('Orig',img)
cv2.imshow('res%d' % K,res2)

cv2.waitKey(0)
cv2.destroyAllWindows()