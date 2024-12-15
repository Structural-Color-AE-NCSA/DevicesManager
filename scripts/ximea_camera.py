from ximea import xiapi
import PIL.Image
from datetime import datetime

class XimeaCamera(object):
    cam = None
    def __init__(self):
        self.cam = xiapi.Camera()
        print('Opening first camera...')
        # cam.open_device_by_SN('02477751')
        #(open by serial number)
        self.cam.open_device()
        self.cam.set_imgdataformat('XI_RGB24')
        # ------exposure in micro seconds
        self.cam.set_exposure(10000)
        print('Exposure was set to %i us' %self.cam.get_exposure())
        #self.cam.set_gain(int('1'))
        #-------gain in dB
        #print('Gain was set to %i us' %self.cam.set_gain(()))

    def take_frame(self):
        img = xiapi.Image()
        print('Starting data acquisition...')
        self.cam.start_acquisition()
        self.cam.get_image(img)
        data = img.get_image_data_numpy(invert_rgb_order=True)
        print('Stopping acquisition...')
        self.cam.stop_acquisition()
        self.cam.close_device()
        img = PIL.Image.fromarray(data, 'RGB')
        current_datetime = datetime.now()
        filename = 'ximea_print'+current_datetime+'.tif'
        img.save(filename,
                 format = 'TIFF', compression = 'tiff_lzw')
        print('Ximea Camera Done.')
        return filename