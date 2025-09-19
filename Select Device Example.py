import logging
import sys
from SLDevicePythonWrapper import *


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S')

cameras = SLDevice.ScanCameras()

if len(cameras) == 0:
    logging.info("No cameras found")
elif len(cameras) == 1:
    logging.info("Found one camera")
    
    camera = cameras[0]
    logging.info(f"IP: {camera.DetectorIPAddress}")
    logging.info(f"Interface: {camera.Interface}")
    logging.info(f"unit: {camera.unit}")
    
    device = SLDevice(camera)
    
    err = device.OpenCamera()
    if err != SLError.SL_ERROR_SUCCESS: 
        logging.error(f"Failed to Open Camera with error: {err}")
        sys.exit(-1)
    
    logging.info("Successfully opened camera")
    
    # ...
    # ...

    err = device.CloseCamera()
    if err != SLError.SL_ERROR_SUCCESS:
        logging.error(f"Failed to CloseCamera with error: {err}")
        sys.exit(-2)
    
    logging.info("Successfully closed camera")
else:
    logging.info(f"{len(cameras)} cameras found.")
    for count, camera in enumerate(cameras):
        logging.info(f"------------ Camera {count} ------------")
        logging.info(f"IP: {camera.DetectorIPAddress}")
        logging.info(f"Interface: {camera.Interface}")
        logging.info(f"unit: {camera.unit}")
        
    while True:
        userInput = input("Select a camera to connect to: ")
        try:
            number = int(userInput)
            if 0 <= number < len(cameras):
                break
            else:
                logging.error(f"Camera choice must be betweeen 0 and {len(cameras) - 1}")
        except ValueError:
            logging.error("Please enter a valid number")
            
    logging.info(f"Connecting to camera {number}")
    
    device = SLDevice(cameras[number])
    
    err = device.OpenCamera()
    if err != SLError.SL_ERROR_SUCCESS: 
        logging.error(f"Failed to Open Camera with error: {err}")
        sys.exit(-3)
    
    logging.info("Successfully opened camera")
    
    # ...
    # ...
    
    err = device.CloseCamera()
    if err != SLError.SL_ERROR_SUCCESS:
        logging.error(f"Failed to CloseCamera with error: {err}")
        sys.exit(-4)
    
    logging.info("Successfully closed camera")
    
    sys.exit(0)