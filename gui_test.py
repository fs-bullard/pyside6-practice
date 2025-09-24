import sys
import time
import os

import numpy as np

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QMainWindow, 
    QApplication, 
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel, 
    QSizePolicy,
    QLineEdit,
    QHBoxLayout, 
    QDialog,
    QDialogButtonBox
)
from PySide6.QtGui import ( 
    QPixmap, 
    QImage, 
    QIntValidator, 
    QIcon, 
    QAction, 
    QKeySequence
)

from SLDevicePythonWrapper import (
    SLDevice,
    DeviceInterface,
    SLError,
    ExposureModes,
    SLImage,
    SLBufferInfo,
)

deviceInterface = DeviceInterface.USB
basedir = os.path.dirname(__file__)
imageSaveDirectory = os.path.join(basedir, "\\SLDevice\\Examples\\Example_Code\\Python\\") 

try:
    from ctypes import windll 
    myappid = 'com.spectrumlogic.westernblot.imager.1'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

class ExposureControl(QWidget):
    exposureChanged = Signal(int)

    def __init__(self, min_val=10, max_val=30000, default_val=10, parent=None, enabled=False, set_button=True):
        super().__init__(parent)
        self.parent = parent

        # Layout
        layout = QHBoxLayout()

        # Label
        self.label = QLabel('Exposure Time (ms):')
        layout.addWidget(self.label)

        # Input
        self.input = QLineEdit(self, text=str(default_val))
        
        validator = QIntValidator(min_val, max_val, self)
        self.input.setValidator(validator)

        layout.addWidget(self.input)

        self.input.textChanged.connect(self.emit_exposure)
        self.input.returnPressed.connect(self.emit_exposure) 

        self.input.setEnabled(enabled)
       
        
        # Set button
        if set_button:
            self.button = QPushButton('Set')
            layout.addWidget(self.button)
            self.button.clicked.connect(self.emit_exposure)
            self.button.setEnabled(enabled)

        # Set layout
        self.setLayout(layout)        

    def emit_exposure(self):
        if self.input.hasAcceptableInput():
            value = int(self.input.text())
            self.exposureChanged.emit(value)

class DarkDialog(QDialog):
    exposureChanged = Signal(int)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Capture Dark Frame")

        self.exposure_control = ExposureControl(enabled=True, set_button=False)

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.button(QDialogButtonBox.Ok).setText("Capture")
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.exposure_control.exposureChanged.connect(self.emit_exposure)

        layout = QVBoxLayout()

        
        layout.addWidget(self.exposure_control)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def get_exposure(self):
        print('Get exposure from main window')

    def emit_exposure(self):
        if self.exposure_control.input.hasAcceptableInput():
            value = int(self.exposure_control.input.text())
            self.exposureChanged.emit(value)


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
        self.frame_count = 0
                
        layout = QVBoxLayout()

        self.camera_on_button = QPushButton('Camera off')
        self.camera_on_button.setCheckable(True)

        self.exposure_control = ExposureControl(default_val=self.exposureTime, parent=self, enabled=True)

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

        self.stream_button.clicked.connect(self.stream_button_toggled)
        self.capture_button.clicked.connect(self.button_clicked)
        self.exposure_control.exposureChanged.connect(self.set_exposure_time)

        layout.addWidget(self.camera_on_button)

        layout.addWidget(self.exposure_control)

        layout.addWidget(self.stream_button)

        layout.addWidget(self.capture_button)

        layout.addWidget(self.image_label, stretch=1)  
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Menu
        menu = self.menuBar()
        
        # File
        file_menu = menu.addMenu('&File')
        
        save_action = QAction("&Save", self)
        save_action.setStatusTip("Save the image")
        save_action.triggered.connect(self.save_image)

        file_menu.addAction(save_action)

        # Edit


        # Corrections
        corrections_menu = menu.addMenu('&Corrections')

        capture_dark_action = QAction('&Capture Dark Image', self)
        capture_dark_action.triggered.connect(self.dark_dialog)

        corrections_menu.addAction(capture_dark_action)

    def dark_dialog(self):
        dialog = DarkDialog()
        dialog.setWindowTitle('Capture Dark Frame')
        dialog.exposureChanged.connect(self.set_exposure_time)
        dialog.accepted.connect(self.capture_dark_image)
        dialog.exec()
    
    def save_image(self):
        print('Image saved')

    def set_exposure_time(self, value: int):
        self.exposureTime = value
        print(f'Exposure time set to {value}ms')
        if self.camera_open and not self.streaming:
            # Set Exposure time
            err = self.device.SetExposureTime(value)
            print('Device exposure time updated')
            if err != SLError.SL_ERROR_SUCCESS:
                print(f'Failed to set exposure time to {value} with error: {err}')


    def on_button_toggled(self, checked):
        if checked:
            self.open_camera()
        else:
            # Turn off stream first
            if self.streaming:
                self.stop_stream()

            # Turn off camera
            self.close_camera()
            
    def open_camera(self):
        # Open camera
        err = self.device.OpenCamera()
        if err != SLError.SL_ERROR_SUCCESS:
            print('Failed to open camera with error: ', err)
            return -1
        print('Successfuly opened camera')
        self.camera_open = True

        self.camera_on_button.setText('Camera on')
        self.stream_button.setEnabled(True)
        self.camera_on_button.setChecked(True)

        print('Intialising Software Trigger')

        # Configure the device
        err = self.device.SetExposureMode(self.exposureMode)
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to set exposure mode to {self.exposureMode} with error: {err}')
            return  
        
        # Set Exposure time
        self.set_exposure_time(self.exposureTime)
    
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
        self.camera_on_button.setText('Camera off')
        self.camera_on_button.setChecked(False)

    def stream_button_toggled(self, checked):
        if checked:
            self.start_stream()
        else:
            self.stop_stream()
        
    def start_stream(self):
        if not self.camera_open:
            print('Open camera before starting stream')
            return
        
        self.stream_button.setText('Stop stream')
        self.stream_button.setChecked(True)
        self.streaming = True
        self.capture_button.setEnabled(True)
        self.exposure_control.input.setEnabled(False)
        self.exposure_control.button.setEnabled(False)

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
        
        self.stream_button.setText('Start stream')
        self.stream_button.setChecked(False)
        self.streaming = False
        self.capture_button.setEnabled(False)
        self.exposure_control.input.setEnabled(True)
        self.exposure_control.button.setEnabled(True)
        
        print('Stopped stream')
        self.streaming = False

    def capture_dark_image(self):
        print('-'*50)
        print('Capturing dark image')

        # Set exposure time input to new exposure time
        self.exposure_control.input.setText(str(self.exposureTime))

        if self.streaming:
            # Stop streaming
            self.stop_stream()
        if self.camera_open:
            # Close camera
            self.close_camera()

        self.open_camera()
        self.start_stream()

        # Capture image
        filename = f"{imageSaveDirectory}\\correction_images\\dark_frame_{self.exposureTime}.tif"
        self.capture_image(filename)
        print('-'*50)

    def button_clicked(self):
        if not self.camera_open:
            print("Camera must be on to capture an image")
            return
        if not self.streaming:
            print("Camera must be streaming to capture an image")
            return

        self.frame_count += 1
        filename = f"{imageSaveDirectory}\\captured_images\\SoftwareTriggerCapture{self.frame_count}.tif"
        self.capture_image(filename)
        
    def capture_image(self, filename):    
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