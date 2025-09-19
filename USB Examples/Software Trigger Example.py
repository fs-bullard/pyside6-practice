from SLDevicePythonWrapper import *
import logging
import sys

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S')

imageSaveDirectory = "L:\\SLDevice\\Examples\\captured_images\\"
deviceInterface = DeviceInterface.USB

def main() -> int:
    # Open a connection to a device with a specified interface
    device = SLDevice(deviceInterface)
    
    err = device.OpenCamera()
    if err != SLError.SL_ERROR_SUCCESS: 
        logging.error(f"Failed to Open Camera with error: {err}")
        return -1
    
    logging.info("Successfully opened camera")
    
    SoftwareTriggerExample(device)
    
    err = device.CloseCamera()
    if err != SLError.SL_ERROR_SUCCESS:
        logging.error(f"Failed to CloseCamera with error: {err}")
        return -2
    
    logging.info("Successfully closed camera")

    return 0

def SoftwareTriggerExample(device: SLDevice) -> None:
    numFrames = 20
    dds = False
    exposureMode = ExposureModes.trig_mode
    
    logging.info("Initialising Software Trigger")

    # Configure the device
    err = device.SetExposureMode(exposureMode)
    if err != SLError.SL_ERROR_SUCCESS: 
        logging.error(f"Failed to set exposure mode to {exposureMode} with error: {err}")
        return
    
    logging.info(f"Set exposure mode to {exposureMode}")
    
    err = device.SetDDS(dds)
    if err != SLError.SL_ERROR_SUCCESS: 
        logging.error(f"Failed to set DDS to {dds} with error: {err}")
        return
    
    logging.info(f"Set DDS to {dds}")

    # Build SLImage object to read frames into
    image = SLImage(device.GetImageXDim(), device.GetImageYDim())
    bufferInfo: SLBufferInfo = None

    # Start Stream
    err = device.StartStream()
    if err != SLError.SL_ERROR_SUCCESS:
        logging.error(f"Failed to start stream with error: {err}")
        return
    
    logging.info("Started stream") 

	# Captures up to numFrames frames
	# After sending a software trigger, AcquireImage blocks the thread until a frame arrives or it times out
	# Frame rate (as well as exposure time) will depend on trigger frequency
	# For high frame rates, images should not be saved in loop as this can slow AcquisitionExample
    for _ in range(numFrames):
        logging.info("Press enter to send software trigger or 'Q' to quit")
        grabFrame = input()
        if grabFrame == "q" or grabFrame == "Q":
            logging.info("Exiting...")
            break
        
        err = device.SoftwareTrigger()
        if err != SLError.SL_ERROR_SUCCESS:
            logging.error(f"Failed to send software trigger with error: {err}")
            break
        
        logging.info("Sent software trigger")

        bufferInfo = device.AcquireImage(image)
        filename = f"{imageSaveDirectory}SoftwareTriggerCapture{bufferInfo.frameCount}.tif"
        
        if bufferInfo.error == SLError.SL_ERROR_SUCCESS:                # Frame acquired successfully
            logging.info(f"Read new frame #{bufferInfo.frameCount} with dims: {bufferInfo.width}x{bufferInfo.height}")
            if image.WriteTiffImage(filename) is False:
                logging.error("Failed to save image")
        elif bufferInfo.error == SLError.SL_ERROR_MISSING_PACKETS:      # Frame acquired with missing packets
            logging.info(f"Read new frame #{bufferInfo.frameCount} with dims: {bufferInfo.width}x{bufferInfo.height}, missing packets: {bufferInfo.missingPackets}")
            if image.WriteTiffImage(filename) is False:
                logging.error("Failed to save image")
        elif bufferInfo.error == SLError.SL_ERROR_TIMEOUT:
            logging.warning("Timed out whilst waiting for frame")
        else:
            logging.error(f"Failed to acquire image with error: {bufferInfo.error}")
        
    # Stop Stream
    err = device.StopStream()
    if err != SLError.SL_ERROR_SUCCESS:
        logging.error(f"Failed to stop stream with error: {err}")
        return
    
    logging.info("Stopped stream")
    
if __name__ == "__main__":
    sys.exit(main())