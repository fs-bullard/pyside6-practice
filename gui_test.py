import sys
import time
import os

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, 
    QApplication, 
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel, 
    QSizePolicy,
    QLineEdit,
    QHBoxLayout
)
from PySide6.QtGui import QPixmap, QImage, QIntValidator, QIcon

from SLDevicePythonWrapper import (
    SLDevice,
    DeviceInterface,
    SLError,
    ExposureModes,
    SLImage,
    SLBufferInfo
)

deviceInterface = DeviceInterface.USB
basedir = os.path.dirname(__file__)
imageSaveDirectory = os.path.join(basedir, "\\SLDevice\\Examples\\Example_Code\\Python\\captured_images\\") 

try:
    from ctypes import windll  # Only exists on Windows.
    myappid = 'com.spectrumlogic.westernblot.imager.1'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Better XView")
        self.resize(700, 800)       

        self.camera_open = False
        self.streaming = False

        # Identify device
        self.device = SLDevice(deviceInterface)
        self.exposureTime = 10
        self.exposureMode = ExposureModes.seq_mode
        self.dds = False
                
        layout = QVBoxLayout()

        self.camera_on_button = QPushButton('Camera off')
        self.camera_on_button.setCheckable(True)

        self.exposure_time_label = QLabel('Exposure Time (ms):')
        self.exposure_time_input = QLineEdit(self, text=str(self.exposureTime))
        et_validator = QIntValidator(10, 30000, self)
        self.exposure_time_input.setValidator(et_validator)
        self.exposure_time_input.setEnabled(False)
        self.exposure_time_button = QPushButton('Set')
        self.exposure_time_button.setEnabled(False)

        self.stream_button = QPushButton('Start stream')
        self.stream_button.setEnabled(False)
        self.stream_button.setCheckable(True)

        self.capture_button = QPushButton("Capture Image")
        self.capture_button.setEnabled(False)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )
        self.image_label.setMinimumSize(1, 1)

        self.camera_on_button.clicked.connect(self.on_button_toggled)
        self.exposure_time_input.returnPressed.connect(self.exposure_set)
        self.exposure_time_button.clicked.connect(self.exposure_set)
        self.stream_button.clicked.connect(self.stream_button_toggled)
        self.capture_button.clicked.connect(self.button_clicked)

        layout.addWidget(self.camera_on_button)

        exposure_controls = QHBoxLayout()
        exposure_controls.addWidget(self.exposure_time_label)
        exposure_controls.addWidget(self.exposure_time_input)
        exposure_controls.addWidget(self.exposure_time_button)
        layout.addLayout(exposure_controls)

        layout.addWidget(self.stream_button)

        layout.addWidget(self.capture_button)

        layout.addWidget(self.image_label, stretch=1)  
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
    
    def exposure_set(self):
        if self.camera_open and not self.streaming:
            # Set Exposure time
            self.exposureTime = int(self.exposure_time_input.text())
            err = self.device.SetExposureTime(self.exposureTime)
            print(f'Exposure time set to {self.exposureTime}ms')
            if err != SLError.SL_ERROR_SUCCESS:
                print(f'Failed to set exposure time to {self.exposureTime} with error: {err}')


    def on_button_toggled(self, checked):
        if checked:
            self.camera_on_button.setText('Camera on')
            self.open_camera()
            self.stream_button.setEnabled(True)
            self.exposure_time_input.setEnabled(True)
            self.exposure_time_button.setEnabled(True)
        else:
            # Turn off stream first
            self.stream_button.setText('Start stream')
            if self.streaming:
                self.stop_stream()
            self.streaming = False
            self.capture_button.setEnabled(False)
            self.stream_button.setChecked(False)
            self.stream_button.setEnabled(False)

            # Turn off camera
            self.close_camera()
            self.camera_on_button.setText('Camera off')

            self.exposure_time_input.setEnabled(False)
            self.exposure_time_button.setEnabled(False)

            

    def open_camera(self):
        # Open camera
        err = self.device.OpenCamera()
        if err != SLError.SL_ERROR_SUCCESS:
            print('Failed to open camera with error: ', err)
            return -1
        print('Successfuly opened camera')
        self.camera_open = True

        print('Intialising Software Trigger')

        # Configure the device
        err = self.device.SetExposureMode(self.exposureMode)
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to set exposure mode to {self.exposureMode} with error: {err}')
            return  
        
        # Set Exposure time
        err = self.device.SetExposureTime(self.exposureTime)
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to set exposure time to {self.exposureTime} with error: {err}')

        print(f'Set exposure time to {self.exposureTime}ms')
    
        err = self.device.SetDDS(self.dds)
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to set DDS to {self.dds} with error: {err}')
            return
        
        print(f'Set DDS to {self.dds}')
    
    def close_camera(self):
        # Close camera
        err = self.device.CloseCamera()
        if err != SLError.SL_ERROR_SUCCESS:
            print('Failed to CloseCamera with error: ', err)
            return -2

        print('Successfully closed camera')
        self.camera_open = False

    def stream_button_toggled(self, checked):
        if checked:
            self.start_stream()
            self.stream_button.setText('Stop stream')
            self.streaming = True
            self.capture_button.setEnabled(True)
            self.exposure_time_input.setEnabled(False)
            self.exposure_time_button.setEnabled(False)
        else:
            self.stop_stream()
            self.stream_button.setText('Start stream')
            self.streaming = False
            self.capture_button.setEnabled(False)
            self.exposure_time_input.setEnabled(True)
            self.exposure_time_button.setEnabled(True)
        
    def start_stream(self):
        if not self.camera_open:
            print('Open camera before starting stream')
            return

         # Build SLImage object to read frames into
        self.image = SLImage(self.device.GetImageXDim(), self.device.GetImageYDim())
        self.bufferInfo: SLBufferInfo = None
        
        # Start Stream
        err = self.device.StartStream()
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to start stream with error: {err}')
            return

        print('Started stream')
        self.streaming = True

    
    def stop_stream(self):
        # Stop stream
        err = self.device.StopStream()
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to stop stream with error: {err}')
            return
        
        print('Stopped stream')
        self.streaming = False

    def button_clicked(self):
        if not self.camera_open:
            print("Camera must be on to capture an image")
            return
        if not self.streaming:
            print("Camera must be streaming to capture an image")
            return
        
        print("Capturing Image")

        err = self.device.SoftwareTrigger()
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to send software trigger with error: {err}')
            return
        
        print('Sent software trigger')

        if not hasattr(self, "image"):
            print("Image buffer not initialized. Start the stream first.")
            return
        
        time.sleep(self.exposureTime / 1000)

        bufferInfo = self.device.AcquireImage(self.image)
        filename = f"{imageSaveDirectory}SoftwareTriggerCapture{bufferInfo.frameCount}.tif"

        if bufferInfo.error == SLError.SL_ERROR_SUCCESS:
            # Frame acquired successfully
            print(f"Read new frame #{bufferInfo.frameCount} with dims: {bufferInfo.width}x{bufferInfo.height}")

            # Convert the image to QPixmap and display it
            pixmap = self.convert_image_to_pixmap(self.image)
            # Scale pixmap to match window dimensions 
            if pixmap:
                self.original_pixmap = pixmap
                self.update_image_label()
            else:
                print("Failed to convert image to QPixmap")

            if self.image.WriteTiffImage(filename) is False:
                print("Failed to save image")

        elif bufferInfo.error == SLError.SL_ERROR_MISSING_PACKETS:
            # Frame aquired with missing packets
            print(f"Read new frame #{bufferInfo.frameCount} with dims: {bufferInfo.width}x{bufferInfo.height}")

            if self.image.WriteTiffImage(filename) is False:
                print('Failed to save image')

        elif bufferInfo.error == SLError.SL_ERROR_TIMEOUT:
            print("Timed out whilst waiting for frame")
        else:
            print(f'Failed to acquire image with error: {bufferInfo.error}')


    def convert_image_to_pixmap(self, sl_image: SLImage):
        img_array_16bit = sl_image.Frame2Array(0)

        img_array = np.around(img_array_16bit.astype(np.float32) * (2**8 - 1) / (2**14 - 1)).astype(np.uint8)

        height, width = img_array.shape[:2]
        q_image = QImage(img_array.data, width, height, width, QImage.Format_Grayscale8).copy()

        return QPixmap.fromImage(q_image)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image_label()        
    
    def update_image_label(self):
        if hasattr(self, "original_pixmap"):
            scaled_pixmap = self.original_pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def closeEvent(self, event):
        if self.streaming:
            self.stop_stream()
        if self.camera_open:
            self.close_camera()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(basedir, 'favicon.ico')))

    window = MainWindow()
    window.show()

    app.exec()