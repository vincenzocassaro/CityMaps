import os

import cv2

image_name = "palmanova"

image_folder = "images"
video_name = f"videos/second/{image_name}.mp4"

# images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
frame = cv2.imread(os.path.join(image_folder, f"{image_name}.png"))
height, width, layers = frame.shape

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video = cv2.VideoWriter(video_name, fourcc, 0.3, (width, height))

video.write(frame)

cv2.destroyAllWindows()
video.release()
