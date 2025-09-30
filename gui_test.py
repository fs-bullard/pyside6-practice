import sys
import time
import os

import numpy as np
import cv2

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
    QDialogButtonBox,
    QCheckBox
)
from PySide6.QtGui import ( 
    QPixmap, 
    QImage, 
    QIntValidator, 
    QIcon, 
    QAction, 
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
imageSaveDirectory = os.path.join(basedir, "Images") 

try:
    from ctypes import windll 
    myappid = 'com.spectrumlogic.westernblot.imager.1'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

class ExposureControl(QWidget):
    exposureChanged = Signal(int)

    def __init__(
            self, min_val=10, max_val=30000, 
            default_val=10, parent=None, enabled=False, set_button=True
        ):
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

    def __init__(self, default_val=10):
        super().__init__()

        self.setWindowTitle("Capture Dark Frame")

        self.exposure_control = ExposureControl(enabled=True, set_button=False, default_val=default_val)

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        self.buttonBox = QDialogButtonBox(QBtn)
        self.capture_button = self.buttonBox.button(QDialogButtonBox.Ok)
        self.capture_button.setText("Capture")
        self.capture_button.setEnabled(True)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.exposure_control.input.textChanged.connect(self.validate_input)
        self.exposure_control.exposureChanged.connect(self.emit_exposure)

        layout = QVBoxLayout()
        
        layout.addWidget(self.exposure_control)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)
    
    def validate_input(self, text):
        if (self.exposure_control.input.validator().validate(text, 0)[0]
             == QIntValidator.Acceptable):
            self.capture_button.setEnabled(True)
        else: 
            self.capture_button.setEnabled(False)

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
        self.current_img = None

        # --------------- Central Widget --------------
                
        layout = QVBoxLayout()

        # Camera on
        self.camera_on_button = QPushButton('Camera off')
        self.camera_on_button.setCheckable(True)
        layout.addWidget(self.camera_on_button)
        self.camera_on_button.clicked.connect(self.on_button_toggled)

        # Exposure control
        self.exposure_control = ExposureControl(
            default_val=self.exposureTime, 
            parent=self, 
            enabled=True
        )
        self.exposure_control.exposureChanged.connect(self.set_exposure_time)
        layout.addWidget(self.exposure_control)

        # Streaming
        self.stream_button = QPushButton('Start stream')
        self.stream_button.setEnabled(False)
        self.stream_button.setCheckable(True)
        self.stream_button.clicked.connect(self.stream_button_toggled)
        layout.addWidget(self.stream_button)

        # Capture
        self.capture_button = QPushButton("Capture Image")
        self.capture_button.setEnabled(False)
        self.capture_button.clicked.connect(self.capture_button_clicked)
        layout.addWidget(self.capture_button)

        # Correction settings
        self.dark_subtraction_box = QCheckBox(text='Dark Subtraction')
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(self.dark_subtraction_box)
        layout.addLayout(settings_layout)

        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )
        self.image_label.setMinimumSize(1, 1)
        layout.addWidget(self.image_label, stretch=1)  

        # ------------------- Image Adjustments -----------------
        adj_layout = QHBoxLayout()

        # Auto-contrast
        self.contrast_button = QPushButton('Auto-Contrast')
        self.contrast_button.setEnabled(False)
        self.contrast_button.clicked.connect(self.auto_contrast)
        adj_layout.addWidget(self.contrast_button)

        # Invert
        self.invert_button = QPushButton('Invert')
        self.invert_button.setEnabled(False)
        self.invert_button.clicked.connect(self.invert)
        adj_layout.addWidget(self.invert_button)

        # Reset corrections
        self.reset_button = QPushButton('Reset Corrections')
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(self.reset_corrections)
        adj_layout.addWidget(self.reset_button)

        layout.addLayout(adj_layout)

        # Set central widget
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # --------------- Menu Bar --------------
        menu = self.menuBar()
        
        # File
        file_menu = menu.addMenu('&File')
        
        save_action = QAction("&Save", self)
        save_action.setStatusTip("Save the image")

        file_menu.addAction(save_action)

        # Edit


        # Corrections
        corrections_menu = menu.addMenu('&Corrections')

        capture_dark_action = QAction('&Capture Dark Image', self)
        capture_dark_action.triggered.connect(self.dark_dialog)

        corrections_menu.addAction(capture_dark_action)


    def dark_dialog(self):
        dialog = DarkDialog(default_val=self.exposureTime)
        dialog.setWindowTitle('Capture Dark Frame')
        dialog.exposureChanged.connect(self.set_exposure_time)
        dialog.accepted.connect(self.capture_dark_image)
        dialog.exec()

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
        self.stream_button.setEnabled(False)
        
        

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
        self.capture_image()
        self.save_image(filename)
        print('-'*50)

    def capture_button_clicked(self):
        if not self.camera_open:
            print("Camera must be on to capture an image")
            return
        if not self.streaming:
            print("Camera must be streaming to capture an image")
            return

        self.frame_count += 1
        filename = f"{imageSaveDirectory}\\captured_images\\capture_{self.frame_count}.tif"
        self.capture_image(offset_correction=self.dark_subtraction_box.isChecked())
        self.display_img()
        self.save_image(filename)
        
    def capture_image(self, offset_correction=False):    
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

            # Apply dark correction if specified
            if offset_correction:
                # Initialise dark image object 
                self.dark_image = SLImage(self.device.GetImageXDim(), self.device.GetImageYDim())

                # If dark image doesn't exist in directory, capture one
                filename_dark = f'{imageSaveDirectory}\\correction_images\\dark_frame_{self.exposureTime}.tif'
                if not os.path.exists(filename_dark):
                    # Try and capture dark image
                    print('No dark image found. Prompting user to capture dark image.')
                    self.dark_dialog()
                    return
                else:
                    print('Dark image already exists')

                # Load dark image
                err = SLImage.ReadTiffImage(filename_dark, self.dark_image)
                if err != True:
                    print(f'Failed to read dark image')
                    return

                # Apply offset correction
                err = SLImage.OffsetCorrection(self.image, self.dark_image, darkOffset=50)
                if err != SLError.SL_ERROR_SUCCESS:
                    print(f'Failed to apply dark correction with error: {err}')
                    return    
                print('Offset correction applied')
            
            # Convert the image to QPixmap and display it
            self.current_img = self.image.Frame2Array(0)
        elif bufferInfo.error == SLError.SL_ERROR_MISSING_PACKETS:
            # Frame aquired with missing packets
            print(f"Read new frame #{bufferInfo.frameCount} with dims: {bufferInfo.width}x{bufferInfo.height}")
        elif bufferInfo.error == SLError.SL_ERROR_TIMEOUT:
                print("Timed out whilst waiting for frame")
        else:
            print(f'Failed to acquire image with error: {bufferInfo.error}')

    def display_img(self):
        pixmap = self.convert_image_to_pixmap(self.current_img)
            
        # Scale pixmap to match window dimensions 
        if pixmap:
            self.original_pixmap = pixmap
            self.update_image_label()
        else:
            print("Failed to convert image to QPixmap")

        self.enable_adjustment_buttons(True)

    def save_image(self, filename):
        if self.image.WriteTiffImage(filename) is False:
            print(f'Failed to save image as {filename}')      

    def convert_image_to_pixmap(self, img_array: np.ndarray):
        img_array = np.around(img_array.astype(np.float32) * (2**8 - 1) / (2**14 - 1)).astype(np.uint8)

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

    def auto_contrast(self):
        print('Applying auto-contrast')
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        cl1 = clahe.apply(self.current_img)

        self.current_img = cl1
        self.display_img()

    def invert(self):
        print('Inverting image')
        self.current_img = 2**14 - self.current_img
        self.display_img()

    def enable_adjustment_buttons(self, enable):    
        self.contrast_button.setEnabled(enable)
        self.invert_button.setEnabled(enable)
        self.reset_button.setEnabled(enable)

    def reset_corrections(self):
        print('Resetting corrections')
        filename = f"{imageSaveDirectory}\\captured_images\\capture_{self.frame_count}.tif"
        image_og = SLImage(self.device.GetImageXDim(), self.device.GetImageYDim())
        SLImage.ReadTiffImage(filename, image_og)
        self.current_img = image_og.Frame2Array(0)
        self.display_img()
        
        


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(basedir, 'favicon.ico')))

    window = MainWindow()
    window.show()

    app.exec()