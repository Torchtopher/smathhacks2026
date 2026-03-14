from roboflow import Roboflow

# rf = Roboflow(api_key="API KEY")
project = rf.workspace("waterqualityprediction").project("floating-trash-detection")
version = project.version(1)
version.download("yolo26")
