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
plt.style.use('fivethirtyeight')

TEST_DIRECTORY = "./images/test/"
TEST_FILE = "draw.png"

CLASS_MAPPING = {
    0: "Mistake",
    1: "Aguamenti",
    2: "Tarantallegra",
    3: "Incendio"
}

def processImageData(img):
    from keras.preprocessing.image import load_img
    from keras.preprocessing.image import img_to_array

    # resize image
    img = cv2.resize(img, (50, 50))

    # # convert to data array
    img_array = img_to_array(img)

    img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)

    print("img_array shape: %s", img_array.shape)
    return img_array 

# def blackWhiteToRGB(img_array):
#     for x in img_array.shape
def predictionToClassification(predictionArr):
    
    result = "No spell found"
    currentConfidence = predictionArr[0]
    for i, val in enumerate(predictionArr):
        if val > currentConfidence:
            currentConfidence = val
            result = CLASS_MAPPING[i]


    print("\n=========")
    print(result)
    
    print(predictionArr)
    print("=========\n")
    return result

def classifyImage(img):
    # Load trained model
    model = keras.models.load_model('./models/spell_model')

    # Get image array in proper format for prediction
    img = processImageData(img)

    predictions = model.predict(np.array( [img] ))
    result = predictionToClassification(predictions[0])
    return result


