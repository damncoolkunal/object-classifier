
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.applications import imagenet_utils
from imutils.object_detection import non_max_suppression
from search.detection_helpers import sliding_window
from search.detection_helpers import image_pyramid
import numpy as np
import argparse
import imutils
import time
import cv2


ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True,
	help="path to the input image")
ap.add_argument("-s", "--size", type=str, default="(200, 150)",
	help="ROI size (in pixels)")
ap.add_argument("-c", "--min-conf", type=float, default=0.9,
	help="minimum probability to filter weak detections")
ap.add_argument("-v", "--visualize", type=int, default=-1,
	help="whether or not to show extra visualizations for debugging")
args = vars(ap.parse_args())


WIDTH = 600
PYR_SCALE = 1.5
WIN_STEP = 16
ROI_SIZE = eval(args["size"])
INPUT_SIZE = (224, 224)


print("[INFO] loading network...")
model = ResNet50(weights="imagenet", include_top=True)


orig = cv2.imread(args["image"])
orig = imutils.resize(orig, width=WIDTH)
(H, W) = orig.shape[:2]

pyramid = image_pyramid(orig, scale=PYR_SCALE, minSize=ROI_SIZE)


rois = []
locs = []


start = time.time()

# loop over the image pyramid
for image in pyramid:
	
	scale = W / float(image.shape[1])

	
	for (x, y, roiOrig) in sliding_window(image, WIN_STEP, ROI_SIZE):
		
		x = int(x * scale)
		y = int(y * scale)
		w = int(ROI_SIZE[0] * scale)
		h = int(ROI_SIZE[1] * scale)

		
		roi = cv2.resize(roiOrig, INPUT_SIZE)
		roi = img_to_array(roi)
		roi = preprocess_input(roi)

		
		rois.append(roi)
		locs.append((x, y, x + w, y + h))

		
		if args["visualize"] > 0:
			
			clone = orig.copy()
			cv2.rectangle(clone, (x, y), (x + w, y + h),
				(0, 255, 0), 2)

			
			cv2.imshow("Visualization", clone)
			cv2.imshow("ROI", roiOrig)
			cv2.waitKey(0)


end = time.time()
print("[INFO] looping over pyramid/windows took {:.5f} seconds".format(
	end - start))


rois = np.array(rois, dtype="float32")

# classify each of the proposal ROIs using ResNet and then show how
# long the classifications took
print("[INFO] classifying ROIs...")
start = time.time()
preds = model.predict(rois)
end = time.time()
print("[INFO] classifying ROIs took {:.5f} seconds".format(
	end - start))


preds = imagenet_utils.decode_predictions(preds, top=1)
labels = {}

# loop over the predictions
for (i, p) in enumerate(preds):
	
	(imagenetID, label, prob) = p[0]


	if prob >= args["min_conf"]:
		
		box = locs[i]

		L = labels.get(label, [])
		L.append((box, prob))
		labels[label] = L


for label in labels.keys():
	
	print("[INFO] showing results for '{}'".format(label))
	clone = orig.copy()

	
	for (box, prob) in labels[label]:
		
		(startX, startY, endX, endY) = box
		cv2.rectangle(clone, (startX, startY), (endX, endY),
			(0, 255, 0), 2)

	
	cv2.imshow("Before", clone)
	clone = orig.copy()

	
	boxes = np.array([p[0] for p in labels[label]])
	proba = np.array([p[1] for p in labels[label]])
	boxes = non_max_suppression(boxes, proba)

	
	for (startX, startY, endX, endY) in boxes:
		
		cv2.rectangle(clone, (startX, startY), (endX, endY),
			(0, 255, 0), 2)
		y = startY - 10 if startY - 10 > 10 else startY + 10
		cv2.putText(clone, label, (startX, y),
			cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)

	cv2.imshow("After", clone)
	cv2.waitKey(0)
