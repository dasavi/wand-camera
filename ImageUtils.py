import cv2
import numpy as np
from GlobalConstants import IMAGE_HEIGHT, IMAGE_WIDTH

THRESHOLD_VALUE = 200
THRESHOLD_DELTA = 20

kernel = np.ones((10,10),np.uint8)

def dilateImage(img):
    return cv2.dilate(img, kernel, iterations = 1)


# Filters everything but the brightest spot in a frame
# Returns a black / white image of the bright spot
def showBrightSpot(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.dilate(img, None, iterations=4)
    # img = cv2.GaussianBlur(img, (5, 5), 0)

    # Adjust threshold to the brightest spot in the frame, so we don't lose track if it flickers
    THRESHOLD_VALUE = cv2.minMaxLoc(img)[1] - THRESHOLD_DELTA
    img = cv2.threshold(img, THRESHOLD_VALUE, 255, cv2.THRESH_BINARY)[1]
    
    return img