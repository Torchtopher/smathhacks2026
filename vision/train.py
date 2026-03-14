from ultralytics import YOLO

model = YOLO("yolov8n.pt")

results = model.train(
    data="Floating-Trash-Detection-1/data.yaml",
    epochs=10,
    imgsz=640,
    batch=16,
    project="trash",
)

print("Training complete!")
print(results)
