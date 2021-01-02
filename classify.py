import tensorflow as tf
from tensorflow import keras
from keras.models import Sequential
from keras.layers import Dense, Flatten, Conv2D, MaxPooling2D, Dropout
from tensorflow.keras import layers
from keras.utils import to_categorical
import numpy as np
import matplotlib.pyplot as plt
import sys
import cv2
from cv2 import *
import math
import os
from os import listdir
from os.path import isfile, join, isdir
from config import CLASS_MAPPING
from config import TRAINING_IMAGE_SIZE_X
from config import TRAINING_IMAGE_SIZE_Y
plt.style.use('fivethirtyeight')

TEST_DIRECTORY = "./images/test/"
TEST_FILE = "draw.png"

def processImageData(img):
    from keras.preprocessing.image import load_img
    from keras.preprocessing.image import img_to_array

    # resize image
    img = cv2.resize(img, (TRAINING_IMAGE_SIZE_X, TRAINING_IMAGE_SIZE_Y))

    # # convert to data array
    img_array = img_to_array(img)

    img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)

    print("img_array shape: %s", img_array.shape)
    return img_array 

# def blackWhiteToRGB(img_array):
#     for x in img_array.shape
def classify(predictionArr):
    
    result = "No spell found"
    currentConfidence = 0
    print("\n=========")
    for i, val in enumerate(predictionArr):
        print(str(CLASS_MAPPING[i]) + ": " + str(val))
        if val > currentConfidence:
            currentConfidence = val
            result = CLASS_MAPPING[i]
    print("=========\n")


    print("\n====RESULT=====")
    print(result)
    
    print("===============\n")
    return result

def classifyImage(img):
    # Load trained model
    model = keras.models.load_model('./models/spell_model')

    # Get image array in proper format for prediction
    img = processImageData(img)

    predictions = model.predict(np.array( [img] ), batch_size=128)
    result = classify(predictions[0])
    return result


