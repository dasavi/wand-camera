# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import cv2
from cv2 import *
import numpy as np
import math
import os
from os import listdir
from os.path import isfile, join, isdir
import time
import datetime
import threading
from threading import Thread
from statistics import mean 
from CountsPerSec import CountsPerSec
from HassApi import HassApi
from classify import classifyImage
from ImageUtils import dilateImage, showBrightSpot, saveImage
from config import CAPTURE_MODE

# Check for required number of arguments
if (len(sys.argv) < 4):
    print("Incorrect number of arguments. Required Arguments: [video source url] [home assistant URL] [API token]")
    sys.exit(0)

# Parse Required Arguments
videoSource = "http://192.168.86.167:8080/?action=stream" #0 #default video source
hassUrl = sys.argv[2]
hassRestToken = sys.argv[3]

# Parse Optional Arguments
IsRemoveBackground = True
IsShowOutputWindows = True
IsTraining = False
IsDebugFps = False

if (len(sys.argv) >= 5):
    IsRemoveBackground = sys.argv[4] == "True"

if (len(sys.argv) >= 6):
    IsShowOutputWindows = sys.argv[5] == "True"

if (len(sys.argv) >= 7):
    IsTraining = sys.argv[6] == "True"

if (len(sys.argv) >= 8):
    IsDebugFps = sys.argv[7] == "True"

# Initialize Home Assistant Rest API Wrapper
hass = HassApi(hassUrl, hassRestToken)

# Constants
DesiredFps = 42
DefaultFps = 42 # Original constants trained for 42 FPS
MicroSecondsBetweenFrames = (1 / DesiredFps) * 1000000
frameSkipThreshold = 5 # Number of frames we can skip without seeing wand and still continue

TrainingResolution = 50
TrainingNumPixels = TrainingResolution * TrainingResolution
TrainingFolderName = "Training"
SpellEndMovement = 0.5 * (DefaultFps / DesiredFps )
MinSpellLength = 15 * (DesiredFps / DefaultFps)
MinSpellDistance = 100
NumDistancesToAverage = int(round( 20 * (DesiredFps / DefaultFps)))

# Booleans to turn on or off output windows
IsShowOriginal = False
IsShowBackgroundRemoved = False
IsShowThreshold = False
IsShowOutput = False

if IsShowOutputWindows:
    IsShowOriginal = True
    IsShowBackgroundRemoved = True
    IsShowThreshold = True
    IsShowOutput = True

# Create Windows
if (IsShowOriginal):
    cv2.namedWindow("Original")
    cv2.moveWindow("Original", 0, 0)

if (IsShowBackgroundRemoved):
    cv2.namedWindow("BackgroundRemoved")
    cv2.moveWindow("BackgroundRemoved", 640, 0)

if (IsShowThreshold):
    cv2.namedWindow("Threshold")
    cv2.moveWindow("Threshold", 0, 480+30)

if (IsShowOutput):
    cv2.namedWindow("Output")
    cv2.moveWindow("Output", 640, 480+30)

# Init Global Variables
IsNewFrame = False
nameLookup = {}
LastSpell = "None"

originalCps = CountsPerSec()
noBackgroundCps = CountsPerSec()
thresholdCps = CountsPerSec()
outputCps = CountsPerSec()

lk_params = dict( winSize  = (25,25),
                  maxLevel = 7,
                  criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

IsNewFrame = False
frame = None

IsNewFrameNoBackground = False
frame_no_background = None

IsNewFrameThreshold = False
frameThresh = None

findNewWands = True
trackedPoints = None
wandTracks = []

def PerformSpell(spell):
    """
    Make the desired Home Assistant REST API call based on the spell
    """
    if(spell == "circle"):
        print("ACTIVATE SPELL")
    return # Temporarily disable

    if (spell=="incendio"):
        hass.TriggerAutomation("automation.wand_incendio")
    elif (spell=="aguamenti"):
        hass.TriggerAutomation("automation.wand_aguamenti")
    elif (spell=="alohomora"):
        hass.TriggerAutomation("automation.wand_alohomora")
    elif (spell=="silencio"):
        hass.TriggerAutomation("automation.wand_silencio")
    elif (spell=="specialis_revelio"):
        hass.TriggerAutomation("automation.wand_specialis_revelio")
    elif (spell=="revelio"):
        hass.TriggerAutomation("automation.wand_revelio")
    elif (spell == "tarantallegra"):
        hass.TriggerAutomation("automation.wand_tarantallegra")
    elif(spell == "circle"):
        print("ACTIVATE SPELL")

def CheckForPattern(wandTracks, exampleFrame):
    """
    Check the given wandTracks to see if is is complete, and if it matches a trained spell
    """
    global find_new_wands, LastSpell

    #Debug
    # print("example frame: %s", exampleFrame.shape)

    if (wandTracks == None or len(wandTracks) == 0):
        return

    thickness = 10
    croppedMax =  TrainingResolution - thickness

    distances = []
    wand_path_frame = np.zeros_like(exampleFrame)
    prevTrack = wandTracks[0]

    for track in wandTracks:
        x1 = prevTrack[0]
        x2 = track[0]
        y1 = prevTrack[1]
        y2 = track[1]

        # Calculate the distance
        distance = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
        distances.append(distance)

        cv2.line(wand_path_frame, (x1, y1),(x2, y2), (255,255,255), thickness)
        prevTrack = track

    mostRecentDistances = distances[-NumDistancesToAverage:]
    avgMostRecentDistances = mean(mostRecentDistances)
    sumDistances = sum(distances)
    if cv2.__version__ >= "4.0":
        contours, hierarchy = cv2.findContours(wand_path_frame,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    else:
        contours, hierarchy, unusedVar = cv2.findContours(wand_path_frame,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    # Determine if wand stopped moving by looking at recent movement (avgMostRecentDistances), and check the length of distances to make sure the spell is reasonably long
    if (avgMostRecentDistances < SpellEndMovement and len(distances) > MinSpellLength):
        # Make sure wand path is valid and is over the defined minimum distance
        if (len(contours) > 0) and sumDistances > MinSpellDistance:
            cnt = contours[0]
            x,y,w,h = cv2.boundingRect(cnt)
            crop = wand_path_frame[y-10:y+h+10,x-30:x+w+30]
            result = classifyImage(wand_path_frame)
            if CAPTURE_MODE:
                saveImage(wand_path_frame)

            cv2.putText(wand_path_frame, result, (0,50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255))
            print("Result: ", result, " Most Recent avg: ", avgMostRecentDistances, " Length Distances: ", len(distances), " Sum Distances: ", sumDistances)
            print("")

      

            PerformSpell(result)
            LastSpell = result
        find_new_wands = True
        wandTracks.clear()

    if wand_path_frame is not None:
        if (IsShowOutput):
            wandPathFrameWithText = AddIterationsPerSecText(wand_path_frame, outputCps.countsPerSec())
            cv2.putText(wandPathFrameWithText, "Last Spell: " + LastSpell, (10, 400), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255))
            cv2.imshow("Output", wandPathFrameWithText)

    return wandTracks

def RemoveBackground():
    """
    Thread for removing background
    """
    global frame, frame_no_background, IsNewFrame, IsNewFrameNoBackground

    fgbg = cv2.createBackgroundSubtractorMOG2()
    t = threading.currentThread()
    while getattr(t, "do_run", True):
        if (IsNewFrame):
            IsNewFrame = False

            frameCopy = frame.copy()
            
            # Subtract Background
            fgmask = fgbg.apply(frameCopy, learningRate=0.001)
            frame_no_background = cv2.bitwise_and(frameCopy, frameCopy, mask = fgmask)
            IsNewFrameNoBackground = True

            if (IsShowBackgroundRemoved):
                    frameNoBackgroundWithCounts = AddIterationsPerSecText(frame_no_background.copy(), noBackgroundCps.countsPerSec())
                    cv2.imshow("BackgroundRemoved", frameNoBackgroundWithCounts)
        else:
            time.sleep(0.001)

def CalculateThreshold():
    """
    Thread for calculating frame threshold
    """
    global frame, frame_no_background, frameThresh, IsNewFrame, IsNewFrameNoBackground, IsNewFrameThreshold

    t = threading.currentThread()
    
    while getattr(t, "do_run", True):
        if (IsRemoveBackground and IsNewFrameNoBackground) or (not IsRemoveBackground and IsNewFrame):
            if IsRemoveBackground:
                IsNewFrameNoBackground = False
                process_frame = frame_no_background

            if not IsRemoveBackground:
                IsNewFrame = False
                process_frame = frame

            frameThresh = showBrightSpot(process_frame)

            IsNewFrameThreshold = True
            if (IsShowThreshold):
                    frameThreshWithCounts = AddIterationsPerSecText(frameThresh.copy(), thresholdCps.countsPerSec())
                    cv2.imshow("Threshold", frameThreshWithCounts)
        else:
            time.sleep(0.001)

def ProcessData():
    """
    Thread for processing final frame
    """
    global frameThresh, IsNewFrameThreshold, findNewWands, wandTracks, outputFrameCount, frameSkipCounter

    oldFrameThresh = None
    trackedPoints = None
    frameSkipCounter = 0
    t = threading.currentThread()

    while getattr(t, "do_run", True):
        if (IsNewFrameThreshold):
            if (IsDebugFps):
                outputFrameCount = outputFrameCount + 1

            IsNewFrameThreshold = False
            localFrameThresh = frameThresh.copy()

            if (findNewWands):
                # Identify Potential Wand Tips using GoodFeaturesToTrack
                trackedPoints = cv2.goodFeaturesToTrack(localFrameThresh, 5, .01, 30)
                if trackedPoints is not None:
                    findNewWands = False
            else:
                # calculate optical flow
                nextPoints, statusArray, err = cv2.calcOpticalFlowPyrLK(oldFrameThresh, localFrameThresh, trackedPoints, None, **lk_params)
           
                # Select good points
                good_new = nextPoints[statusArray==1]
                good_old = trackedPoints[statusArray==1]

                if (len(good_new) > 0):
                    # draw the tracks
                    for i,(new,old) in enumerate(zip(good_new,good_old)):
                        a,b = new.ravel()
                        c,d = old.ravel()
           
                        wandTracks.append([a, b])
           
                    # Update which points are tracked
                    trackedPoints = good_new.copy().reshape(-1,1,2)
           
                    wandTracks = CheckForPattern(wandTracks, localFrameThresh)
                elif frameSkipCounter < frameSkipThreshold:
                    frameSkipCounter = frameSkipCounter + 1
                    continue
                else:
                    # No Points were tracked, check for a pattern and start searching for wands again
                    #wandTracks = CheckForPattern(wandTracks, localFrameThresh)
                    wandTracks = []
                    findNewWands = True
                    frameSkipCounter = 0
            
            # Store Previous Threshold Frame
            oldFrameThresh = localFrameThresh

            
        else:
            time.sleep(0.001)

def AddIterationsPerSecText(frame, iterations_per_sec):
    """
    Add iterations per second text to lower-left corner of a frame.
    """
    cv2.putText(frame, "{:.0f} iterations/sec".format(iterations_per_sec),
        (10, 450), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255))
    return frame

timeLastPrintedFps = datetime.datetime.now()

inputFrameCount = 0
outputFrameCount = 0

# Start thread to remove frame background
if IsRemoveBackground:
    RemoveBackgroundThread = Thread(target=RemoveBackground)
    RemoveBackgroundThread.do_run = True
    RemoveBackgroundThread.daemon = True
    RemoveBackgroundThread.start()

# Start thread to calculate threshold
CalculateThresholdThread = Thread(target=CalculateThreshold)
CalculateThresholdThread.do_run = True
CalculateThresholdThread.daemon = True
CalculateThresholdThread.start()

# Start thread to process final frame
ProcessDataThread = Thread(target=ProcessData)
ProcessDataThread.do_run = True
ProcessDataThread.daemon = True
ProcessDataThread.start()

# Set OpenCV video capture source
videoCapture = cv2.VideoCapture(videoSource)

# Main Loop
while True:
    # Get most recent frame
    ret, localFrame = videoCapture.read()

    if (ret):
        frame = localFrame.copy()

        # If successful, flip the frame and set the Flag for the next process to take over
        cv2.flip(frame, 1, frame) # Flipping the frame is done so the spells look like what we expect, instead of the mirror image
        IsNewFrame = True

        if (IsDebugFps):
            inputFrameCount = inputFrameCount + 1
            
            # Print FPS Debug info every second
            if ((datetime.datetime.now() - timeLastPrintedFps).seconds >= 1 ):
                timeLastPrintedFps = datetime.datetime.now()
                print("FPS: %d/%d" %(inputFrameCount, outputFrameCount))
                inputFrameCount = 0
                outputFrameCount = 0
                    

        # Update Windows
        if (IsShowOriginal):
            frameWithCounts = AddIterationsPerSecText(frame.copy(), originalCps.countsPerSec())
            cv2.imshow("Original", frameWithCounts)
        
    elif not ret:
        # If an error occurred, try initializing the video capture again
        videoCapture = cv2.VideoCapture(videoSource)

    # Check for ESC key, if pressed shut everything down
    if (cv2.waitKey(1) is 27):
        break

# Shutdown PyPotter
if IsRemoveBackground:
    RemoveBackgroundThread.do_run = False
    RemoveBackgroundThread.join()

CalculateThresholdThread.do_run = False
ProcessDataThread.do_run = False

CalculateThresholdThread.join()
ProcessDataThread.join()

cv2.destroyAllWindows()