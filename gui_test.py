import sys

from PySide6.QtWidgets import (
    QMainWindow, 
    QApplication, 
    QPushButton,
    QVBoxLayout,
    QWidget
)

from SLDevicePythonWrapper import (
    SLDevice,
    DeviceInterface,
    SLError,
    ExposureModes,
    SLImage,
    SLBufferInfo
)

# from gui_functions import capture_image

deviceInterface = DeviceInterface.USB
imageSaveDirectory = "L:\\SLDevice\\Examples\\Example_Code\\Python\\captured_images\\"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Better XView")
        self.camera_open = False
        self.streaming = False

        # Identify device
        device = SLDevice(deviceInterface)
                
        layout = QVBoxLayout()
        self.camera_on_button = QPushButton('Camera off')
        self.camera_on_button.setCheckable(True)
        self.stream_button = QPushButton('Start stream')
        self.stream_button.setEnabled(False)
        self.stream_button.setCheckable(True)
        self.capture_button = QPushButton("Capture Image")
        self.capture_button.setEnabled(False)

       

        self.camera_on_button.clicked.connect(lambda checked: self.on_button_toggled(checked, device))
        self.stream_button.clicked.connect(lambda checked: self.stream_button_toggled(checked, device))
        self.capture_button.clicked.connect(lambda: self.button_clicked(device))

        layout.addWidget(self.camera_on_button)
        layout.addWidget(self.stream_button)
        layout.addWidget(self.capture_button)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        

    def on_button_toggled(self, checked, device):
        if checked:
            self.camera_on_button.setText('Camera on')
            self.open_camera(device)
            self.stream_button.setEnabled(True)
        else:
            self.camera_on_button.setText('Camera off')
            self.close_camera(device)
            self.stream_button.setEnabled(False)

    def open_camera(self, device):
        # Open camera
        err = device.OpenCamera()
        if err != SLError.SL_ERROR_SUCCESS:
            print('Failed to open camera with error: ', err)
            return -1
        print('Successfuly opened camera')
        self.camera_open = True

        dds = False
        exposureMode = ExposureModes.trig_mode

        print('Intialising Software Trigger')

        # Configure the device
        err = device.SetExposureMode(exposureMode)
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to set exposure mode to {exposureMode} with error: {err}')
            return
    
        err = device.SetDDS(dds)
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to set DDS to {dds} with error: {err}')
            return
        
        print(f'Set DDS to {dds}')
    
    def close_camera(self, device):
        # Close camera
        err = device.CloseCamera()
        if err != SLError.SL_ERROR_SUCCESS:
            print('Failed to CloseCamera with error: ', err)
            return -2

        print('Successfully closed camera')
        self.camera_open = False

        # TODO: should also toggle streaming

    def stream_button_toggled(self, checked, device):
        if checked:
            self.start_stream(device)
            self.stream_button.setText('Stop stream')
            self.streaming = True
            self.capture_button.setEnabled(True)
        else:
            self.stop_stream(device)
            self.stream_button.setText('Start stream')
            self.streaming = False
            self.capture_button.setEnabled(False)

        
    def start_stream(self, device):
        if not self.camera_open:
            print('Open camera before starting stream')
            return

         # Build SLImage object to read frames into
        self.image = SLImage(device.GetImageXDim(), device.GetImageYDim())
        self.bufferInfo: SLBufferInfo = None
        
        # Start Stream
        err = device.StartStream()
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to start stream with error: {err}')
            return

        print('Started stream')
        self.streaming = True

    
    def stop_stream(self, device):
        # Stop stream
        err = device.StopStream()
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to stop stream with error: {err}')
            return
        
        print('Stopped stream')
        self.streaming = False

    def button_clicked(self, device):
        if not self.camera_open:
            print("Camera must be on to capture an image")
            return
        if not self.streaming:
            print("Camera must be streaming to capture an image")
            return
        
        print("Capturing Image")

        err = device.SoftwareTrigger()
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to send software trigger with error: {err}')
            return
        
        print('Sent software trigger')

        if not hasattr(self, "image"):
            print("Image buffer not initialized. Start the stream first.")
            return

        bufferInfo = device.AcquireImage(self.image)
        filename = f"{imageSaveDirectory}SoftwareTriggerCapture{bufferInfo.frameCount}.tif"

        if bufferInfo.error == SLError.SL_ERROR_SUCCESS:
            # Frame acquired successfully
            print(f"Read new frame #{bufferInfo.frameCount} with dims: {bufferInfo.width}x{bufferInfo.height}")
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


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()