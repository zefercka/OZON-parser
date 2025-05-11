import cv2
import numpy as np
import requests
from io import BytesIO
from PIL import Image

def fetch_image(path):
    try:
        img = Image.open(path).convert("L")  # в градации серого
        return np.array(img)
    except:
        return None

def image_blur_score(image_array):
    # Laplacian variance: чем ниже, тем более размытое изображение
    return cv2.Laplacian(image_array, cv2.CV_64F).var()

# Пример:
path = "images/fe2f9abc-27ec-4a19-92b0-22839f8c856b_0.jpg"
img = fetch_image(path)
if img is not None:
    score = image_blur_score(img)
    print(f"Blur score: {score}")
else:
    print("Не удалось загрузить изображение.")
