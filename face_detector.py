import cv2
import numpy as np
import os

def get_face_detector():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    
    modelFile = os.path.join(script_dir, "models/res10_300x300_ssd_iter_140000.caffemodel")
    configFile = os.path.join(script_dir, "models/deploy.prototxt")
    
    model = cv2.dnn.readNetFromCaffe(configFile, modelFile)
    return model

def find_faces(img, model):
    h, w = img.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 1.0,
	(300, 300), (104.0, 177.0, 123.0))
    model.setInput(blob)
    res = model.forward()
    faces = []
    for i in range(res.shape[2]):
        confidence = res[0, 0, i, 2]
        if confidence > 0.5:
            box = res[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x, y, x1, y1) = box.astype("int")
            faces.append([x, y, x1, y1])
    return faces

