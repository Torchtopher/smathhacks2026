from ultralytics import YOLO

model = YOLO("../runs/detect/trash/train/weights/best.pt")

results = model.predict(
    source="test.png",
    conf=0.25,
    save=True
)

for result in results:
    result.show()
    print(result.boxes)
