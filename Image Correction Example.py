import logging
import sys
from SLDevicePythonWrapper import *



logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S')

installDir      = "L:\\SLDevice\\" # Default directory, will need changing if install directory is not default
imageSaveDir    = installDir + "Examples\\captured_images\\"
darkPath        = installDir + "Examples\\Example_Code\\Demo Images\\AVG_Dark_2802_2400.tif"
fldPath         = installDir + "Examples\\Example_Code\\Demo Images\\AVG_Gain_2802_2400.tif"
sourcePath      = installDir + "Examples\\Example_Code\\Demo Images\\AVG_PCB_2802_2400.tif"
defectPath      = installDir + "Examples\\Example_Code\\Demo Images\\DefectMap.tif"


def main() -> int:
    try:
        FullCorrection()
    except Exception as e:
        logging.error(f"Caught exception during correction {e}")
        return -1
    
    return 0

def FullCorrection() -> None:
    # Additional offset to prevent negative values
    # 300 is the recommended value
    darkOffset = 300 

    imageToCorrect = SLImage(sourcePath)
    darkMap = SLImage(darkPath)
    gainMap = SLImage(fldPath)
    defectMap = SLImage(defectPath)
    
    # Corrections should be done in the order Offset correction --> Gain correction --> Defect correction
    
    err = imageToCorrect.OffsetCorrection(darkMap, darkOffset)
    if err != SLError.SL_ERROR_SUCCESS:
        logging.error(f"Failed to apply offset correction with error: {err}")
    
    logging.info("Offset correction applied.")
    
    err = imageToCorrect.GainCorrection(gainMap, darkOffset)
    if err != SLError.SL_ERROR_SUCCESS:
        logging.error(f"Failed to apply gain correction with error: {err}")
        
    logging.info("Gain correction applied.")
    
    err = imageToCorrect.KernelDefectCorrection(defectMap)
    if err != SLError.SL_ERROR_SUCCESS:
        logging.error(f"Failed to apply defect correction with error: {err}")
        
    logging.info("Defect correction applied.")
    
    filename = f"{imageSaveDir}Corrected_Image_2802_2400.tif"
    if imageToCorrect.WriteTiffImage(filename, 16):
        logging.info(f"Saved image as {filename}")
    else:
        logging.error("Failed to save image")

if __name__ == "__main__":
    sys.exit(main())
