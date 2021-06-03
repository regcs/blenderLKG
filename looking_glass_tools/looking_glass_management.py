# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import io, os
import timeit
from enum import Enum

# modules required by the Holo Play Service
import pynng, cbor, math
from PIL import Image, ImageOps
import numpy as np

# just for debugging
from pprint import pprint
from time import sleep
# from . holoplay_service_api_commands import *

# LIGHTFIELD IMAGE CLASSES
###############################################
# the following classes are used to represent, convert, and manipulate a set of
# views using a defined lightfield format
class LightfieldImage(object):

    # POSSIBLE FORMATS OF THE VIEWS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #   Enum definition for the different formats the lightfield views can be
    #   passed as
    class views_format(Enum):
        numpyarray = 1
        bytesio = 2

        @classmethod
        def to_list(cls):
            return list(map(lambda enum: enum, cls))

    #   Enum definition for the different formats the lightfield image can be
    #   transformed to
    class decoderformat(Enum):
        numpyarray = 1
        bytesio = 2

        @classmethod
        def to_list(cls):
            return list(map(lambda enum: enum, cls))


    # CLASS METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @classmethod
    def new(cls, format, **kwargs):
        ''' create an empty lightfield image object of specified format '''

        # try to find the class for the specified type, if it exists
        LightfieldImageFormat = [subclass for subclass in BaseLightfieldImageFormat.__subclasses__() if (subclass == format)]

        if LightfieldImageFormat:
            lightfield = LightfieldImageFormat[0](**kwargs)
            return lightfield

        raise TypeError("'%s' is no valid lightfield image format." % format)

    @classmethod
    def open(cls, filepath, format, **kwargs):
        ''' open a lightfield image object file of specified format from disk '''

        # try to find the class for the specified format, if it exists
        LightfieldImageFormat = [subclass for subclass in BaseLightfieldImageFormat.__subclasses__() if (subclass == format)]
        if LightfieldImageFormat:

            # create a new lightfield image instance of the specified format
            lightfield = LightfieldImageFormat[0](**kwargs)

            # load the image
            lightfield.load(filepath)

            # return the lightfield image instance of the specified format
            return lightfield

        raise TypeError("'%s' is no valid lightfield image format." % format)

    @classmethod
    def from_buffer(cls, filepath, format):
        ''' creat a lightfield image object of specified format from a byte buffer '''
        pass

    @classmethod
    def convert(self, lightfield, target_format):
        ''' convert a lightfield image object to another type '''
        pass

class BaseLightfieldImageFormat(object):

    # PRIVATE MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __views = []              # list of views the lightfield is created from
    __views_format = None     # format of the views
    __metadata = {}           # metadata of the lightfield format
    __colormode = 'RGBA'      # colormode of the image data
    __colorchannels = 4       # number of color channels in the image data


    # INSTANCE METHODS - IMPLEMENTED BY BASE CLASS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def get_views(self):
        ''' return the list of views in their original format '''
        return {'views': self.views, 'format': self.views_format}


    # INSTANCE METHODS - IMPLEMENTED BY SUBCLASSES
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def __init__(self, **kwargs):
        ''' create a new and empty lightfield image object of specified type '''
        pass

    def load(self, filepath):
        ''' load the lightfield from a file '''
        pass

    def save(self, filepath, format):
        ''' convert the lightfield to a specific file format and save it '''
        pass

    def delete(self, lightfield):
        ''' delete the given lightfield image object '''
        pass

    def set_views(self, views, format):
        ''' store the list of views and their format '''
        self.views = views
        self.views_format = format
        # NOTE: This method might be overriden by subclasses to to perform
        #       specific validity checks (e.g., expected number of views or formats)

    def decode(self, format):
        ''' return the image as the lightfield and return it '''
        pass

    # CLASS PROPERTIES
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @property
    def views(self):
        return self.__views

    @views.setter
    def views(self, value):
        self.__views = value

    @property
    def views_format(self):
        return self.__views_format

    @views_format.setter
    def views_format(self, value):
        self.__views_format = value

    @property
    def metadata(self):
        return self.__metadata

    @metadata.setter
    def metadata(self, value):
        self.__metadata = value

    @property
    def colormode(self):
        return self.__colormode

    @colormode.setter
    def colormode(self, value):
        self.__colormode = value

    @property
    def colorchannels(self):
        return self.__colorchannels

    @colorchannels.setter
    def colorchannels(self, value):
        self.__colorchannels = value

class LookingGlassQuilt(BaseLightfieldImageFormat):

    # PUBLIC MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # supported quilt formats
    class formats:

        __dict = {

            # first gen devices
            1: {'description': "2k Quilt, 32 Views", 'quilt_width': 2048, 'quilt_height': 2048, 'view_width': 512, 'view_height': 256, 'columns': 4, 'rows': 8 },
            2: {'description': "4k Quilt, 45 Views", 'quilt_width': 4096, 'quilt_height': 4096, 'view_width': 819, 'view_height': 455, 'columns': 5, 'rows': 9 },
            3: {'description': "8k Quilt, 45 Views", 'quilt_width': 8192, 'quilt_height': 8192, 'view_width': 1638, 'view_height': 910, 'columns': 5, 'rows': 9 },

            #Looking Glass Portrait
            4: {'description': "Portrait, 48 Views", 'quilt_width': 3360, 'quilt_height': 3360, 'view_width': 420, 'view_height': 560, 'columns': 8, 'rows': 6 },
            5: {'description': "Portrait, 91 Views", 'quilt_width': 4095, 'quilt_height': 4225, 'view_width': 585, 'view_height': 325, 'columns': 7, 'rows': 13 },

        }

        @classmethod
        def add(cls, values):
            ''' add a new format by passing a dict '''
            cls.__dict[len(cls.__dict) + 1] = values
            return len(cls.__dict)

        @classmethod
        def remove(cls, id):
            ''' remove an existing format '''
            cls.__dict.pop(id, None)

        @classmethod
        def get(cls, id=None):
            ''' return the complete dictionary or the dictionary of a specific format '''
            if not id: return cls.__dict
            else:      return cls.__dict[id]

        @classmethod
        def set(cls, id, values):
            ''' modify an existing format by passing a dict '''
            if id in cls.__dict.keys(): cls.__dict[id] = values


    # INSTANCE METHODS - IMPLEMENTED BY SUBCLASS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def __init__(self, id=None):
        ''' create a new and empty lightfield image object of type LookingGlassQuilt '''

        # if no quilt format id was passed
        if not id:

            # TODO: Implement this as arguments in a reasonable way
            # store color information
            self.colormode = 'RGBA'
            self.colorchannels = 4

            # store quilt metadata
            self.metadata['quilt_width'] = 0
            self.metadata['quilt_height'] = 0
            self.metadata['view_width'] = 0
            self.metadata['view_height'] = 0
            self.metadata['rows'] = 0
            self.metadata['columns'] = 0
            self.metadata['count'] = 0

        # if a valid id was passed
        elif id in LookingGlassQuilt.formats.get().keys():

            # TODO: Implement this as arguments in a reasonable way
            # store color information
            self.colormode = 'RGBA'
            self.colorchannels = 4

            # store quilt metadata
            self.metadata['quilt_width'] = LookingGlassQuilt.formats.get(id)['quilt_width']
            self.metadata['quilt_height'] = LookingGlassQuilt.formats.get(id)['quilt_height']
            self.metadata['view_width'] = LookingGlassQuilt.formats.get(id)['view_width']
            self.metadata['view_height'] = LookingGlassQuilt.formats.get(id)['view_height']
            self.metadata['rows'] = LookingGlassQuilt.formats.get(id)['rows']
            self.metadata['columns'] = LookingGlassQuilt.formats.get(id)['columns']
            self.metadata['count'] = self.metadata['rows'] * self.metadata['columns']

        else:

            raise TypeError("There is no quilt format with the id '%i'. Please choose one of the following: %s" % (id, LookingGlassQuilt.formats.get()))

    def load(self, filepath):
        ''' load the quilt file from the given path and convert to numpy views '''
        if os.path.exists(filepath):

            start = timeit.default_timer()
            # use PIL to load the image from disk
            # NOTE: This makes nearly all of the execution time of the load() method
            quilt_image = Image.open(filepath)
            if quilt_image:

                # reset state variable
                found = False

                # for each supported quilt format
                for qf in LookingGlassQuilt.formats.get().values():

                    # if the image dimensions matches one of the quilt formats
                    # NOTE: We allow a difference of +/-1 px in width and height
                    #       to accomodate for rounding errors in view width/height
                    if quilt_image.width in range(qf['quilt_width'] - 1, qf['quilt_width'] + 1) and quilt_image.height in range(qf['quilt_height'] - 1, qf['quilt_height'] + 1):

                        # store new row and column number in the metadata
                        self.metadata['rows'] = qf['rows']
                        self.metadata['columns'] = qf['columns']
                        self.metadata['count'] = qf['rows'] * qf['columns']
                        self.metadata['view_width'] = qf['view_width']
                        self.metadata['view_height'] = qf['view_height']

                        # update state variable
                        found = True

                # if no fitting quilt format was found
                if not found: raise TypeError("The loaded image is not in a supported format. Please check the image dimensions.")

                # TODO: This takes 0.5 to 1.5 s ... is there a faster way?
                # convert it to a numpy array
                quilt_np = np.asarray(quilt_image, dtype=np.uint8)
                # crop the image in case, the size is incorrect due to rounding
                # errors
                quilt_np = quilt_np[0:(self.metadata['rows'] * self.metadata['view_height']), 0:(self.metadata['columns'] * self.metadata['view_width']), :]

                # store the colormode
                self.colormode = quilt_image.mode

                # store the size and color depth in the meta data of the instance
                self.metadata['quilt_height'], self.metadata['quilt_width'], self.colorchannels = quilt_np.shape

                # then we reshape the quilt into the array of individual views ...
                views = quilt_np.reshape(self.metadata['rows'], self.metadata['view_height'], self.metadata['columns'], self.metadata['view_width'], self.colorchannels).swapaxes(1, 2).reshape(self.metadata['count'], self.metadata['view_height'], self.metadata['view_width'], self.colorchannels)

                # ... and pass the views and views format to the instance
                self.set_views([view for view in views], LightfieldImage.views_format.numpyarray)

                return True

            raise TypeError("The quilt image was found but could not be opened. The image format is not supported.")

        raise FileNotFoundError("The quilt image was not found.")

    def save(self, filepath, format):
        ''' convert the lightfield to a specific file format and save it '''
        pass

    def delete(self, lightfield):
        ''' delete the given lightfield image object '''
        pass

    def get_views(self):
        ''' return a 2-tubple with the list of views and their format '''
        return super().get_views()

    def set_views(self, views, format):
        ''' store the list of views and their format '''

        # we override the base class function to introduce an additional check
        if len(views) == self.metadata['count']:

            # and then call the base class function
            return super().set_views(views, format)

        raise ValueError("Invalid view set. %i views were passed, but %i were required." % (len(views), self.metadata['count']))

    def decode(self, format, custom_decoder = None):
        ''' return the lightfield image object in a specific format '''

        # get the views
        views = self.get_views()['views']
        views_format = self.get_views()['format']

        # if a custom decoder function is passed
        if custom_decoder:

            # call this function
            quilt = custom_decoder(views, views_format, format)

            # return the bytesio of the quilt
            return quilt


        # TODO: HERE IS THE PLACE TO DEFINE STANDARD CONVERSIONS THAT CAN BE
        #       USED IN MULTIPLE PROGRAMMS

        # if the image shall be returned as
        if format == LightfieldImage.decoderformat.bytesio:

            # if the views are in a numpy array format
            if views_format == LightfieldImage.views_format.numpyarray:

                # create a numpy quilt from numpy views
                quilt_numpy = self.__from_views_to_quilt_numpy(views)

                # convert to bytesio
                quilt_bytesio = self.__from_numpyarray_to_bytesio(quilt_numpy)

                # return the bytesio of the quilt
                return quilt_bytesio

            # otherwise raise exception
            raise TypeError("The given views format '%s' is not supported." % views_format)

        # otherwise raise exception
        raise TypeError("The requested lightfield format '%s' is not supported." % format)


    # PRIVATE INSTANCE METHODS: VIEWS TO QUILTS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: this function is based on https://stackoverflow.com/questions/42040747/more-idiomatic-way-to-display-images-in-a-grid-with-numpy
    def __from_views_to_quilt_numpy(self, dtype = np.uint8):
        ''' convert views given as numpy arrays to a quilt as a numpy array '''

        # get the views
        views = self.get_views()['views']
        views_format = self.get_views()['format']

        # create a numpy array from the list of views
        views = np.asarray(views)

        # then we reshaoe the numpy array to the quilt shape
        quilt_np = views.reshape(self.metadata['rows'], self.metadata['columns'], self.metadata['view_height'], self.metadata['view_width'], self.colorchannels).swapaxes(1, 2).reshape(self.metadata['quilt_height'], self.metadata['quilt_width'], self.colorchannels)

        # TODO: CODE TO CONVERT VIEWS TO QUILT
        return quilt_np


    # PRIVATE INSTANCE METHODS: CONVERT BETWEEN DECODERFORMATS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def __from_numpyarray_to_bytesio(self, data):
        ''' convert pixel data from numpy array to BytesIO object '''

        # create a PIL image from the numpy
        quilt_image = Image.fromarray(data)

        # create a BytesIO object and save the numpy image data therein
        bytesio = io.BytesIO()
        quilt_image.save(bytesio, 'BMP')

        # return the bytesio object
        return bytesio

    # CLASS PROPERTIES
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # @property                   # read-only property
    # def formats(self):
    #     return self.__formats

    # @presets.setter
    # def presets(self, value):
    #     self.__formats = value



# SERVICE MANAGER FOR LIGHTFIELD DISPLAYS
###############################################
# the service manager is the factory class for generating service instances of
# the different service types
class ServiceManager(object):

    # PRIVATE MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __active = None                                    # active service
    __service_count = []                               # number of created services
    __service_list = []                                # list of created services


    # CLASS METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @classmethod
    def add(cls, service_type):
        ''' open the service of the specified type '''

        # try to find the class for the specified type, if it exists
        ServiceTypeClass = [subclass for subclass in BaseServiceType.__subclasses__() if (subclass == service_type or subclass.type == service_type)]

        # if a service of the specified type was found
        if ServiceTypeClass:

            # create the service instance
            service = ServiceTypeClass[0]()

            # append registered device to the device list
            cls.__service_list.append(service)

            # make this service the active service if no service is active or this is the first ready service
            if (not cls.get_active() or (cls.get_active() and not cls.get_active().is_ready())):
                cls.set_active(service)

            print("Added service '%s' to the service manager." % service)

            return service

        # otherwise raise an exception
        raise ValueError("There is no service of type '%s'." % service_type)

    @classmethod
    def to_list(cls):
        ''' enumerate the services of this service manager as list '''
        return cls.__service_list

    @classmethod
    def count(cls):
        ''' return number of services '''
        return len(cls.to_list())

    @classmethod
    def get_active(cls):
        ''' return the active service (i.e., the one currently used by the app / user) '''
        return cls.__active

    @classmethod
    def set_active(cls, service):
        ''' set the active service (i.e., the one currently used by the app / user) '''
        if service in cls.__service_list:
            cls.__active = service
            return service

        # else raise exception
        raise ValueError("The given device with id '%i' is not in the list." % id)

    @classmethod
    def reset_active(cls):
        ''' set the active service to None '''
        cls.__service_active = None

    @classmethod
    def remove(cls, service):
        ''' remove the service from the ServiceManager '''
        # NOTE:

        # if the device is in the list
        if service in cls.__service_list:

            # create the device instance
            print("Removing service '%s' ..." % (service))

            # if this device is the active device, set_active
            if cls.get_active() == service: cls.reset_active()

            cls.__service_list.remove(service)

            # then delete the service instance
            del service

            return True

# BASE CLASS OF SERVICE TYPES
###############################################
# the service type class used for handling lightfield display communication
# all service type implementations must be a subclass of this base class
class BaseServiceType(object):

    # DEFINE CLASS PROPERTIES AS PROTECTED MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    type = None                                         # the unique identifier string of a service type (required for the factory class)

    # DEFINE CLASS PROPERTIES AS PRIVATE MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __version = ""                                      # version string of the service service

    # INSTANCE METHODS - IMPLEMENTED BY BASE CLASS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: Here is the place to implement functions that should not be overriden
    #       by the subclasses, which represent the specific service types

    def __str__(self):
        ''' the display name of the service when the instance is called '''

        return "%s v%s" % (self.name, self.get_version())

    # TEMPLATE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: These methods must be implemented by the subclasses, which represent
    #       the specific service type
    def __init__(self):
        ''' handle initialization of the class instance and the specific service '''
        pass

    def is_ready(self):
        ''' handles check if the service is ready '''
        pass

    def get_version(self):
        ''' method to obtain the service version '''
        pass

    def get_devices(self):
        ''' method to request the connected devices '''
        ''' this function should return a list of device configurations '''
        pass

    def display(self, device, lightfield, aspect=None, custom_decoder = None):
        ''' display a given lightfield image object on a device '''
        pass

    def clear(self, device):
        ''' clear the display of a given device '''
        pass

    def __del__(self):
        ''' handles closing / deinitializing the service '''
        pass

    # CLASS PROPERTIES
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @property
    def service(self):
        return self.__service

    @service.setter
    def service(self, value):
        self.__service = value

    @property
    def version(self):
        return self.__version

    @version.setter
    def version(self, value):
        self.__version = value

# SERVICE TYPES FOR LOOKING GLASS DEVICES
###############################################
# Holo Play Service for Looking Glass lightfield displays
class HoloPlayService(BaseServiceType):

    # DEFINE CLASS PROPERTIES AS PROTECTED MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    type = 'holoplayservice'                            # the unique identifier string of this service type (required for the factory class)
    name = 'HoloPlay Service'                           # the name this service type

    # DEFINE CLASS PROPERTIES AS PRIVATE MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __socket = None                                             # NNG socket
    __address = 'ipc:///tmp/holoplay-driver.ipc'                # driver url (alternative: "ws://localhost:11222/driver")
    __dialer = None                                             # NNG Dialer of the socket
    __devices = []                                              # list of devices recognized by this service
    __decoder_format = LightfieldImage.decoderformat.bytesio    # the decoder format in which the lightfield data is passed to the backend or display

    # Error
    ###################
    #   Enum definition for errors returned from the HoloPlayCore dynamic library.
    #
    #   This encapsulates potential errors with the connection itself,
    #   as opposed to hpc_service_error, which describes potential error messages
    #   included in a successful reply from HoloPlay Service.
    class client_error(Enum):
        CLIERR_NOERROR = 0
        CLIERR_NOSERVICE = 1
        CLIERR_VERSIONERR = 2
        CLIERR_SERIALIZEERR = 3
        CLIERR_DESERIALIZEERR = 4
        CLIERR_MSGTOOBIG = 5
        CLIERR_SENDTIMEOUT = 6
        CLIERR_RECVTIMEOUT = 7
        CLIERR_PIPEERROR = 8
        CLIERR_APPNOTINITIALIZED = 9

    # INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def __init__(self, timeout = 5000):
        ''' initialize the class instance and create the NNG socket '''

        # open a Req0 socket
        self.__socket = pynng.Req0(recv_timeout = timeout)

        # if the NNG socket is open
        if self.__is_socket():

            print("Created socket: ", self.__socket)

            # connect to HoloPlay Service App
            self.__connect()

    def is_ready(self):
        ''' check if the service is ready: Is NNG socket created and connected to HoloPlay Service App? '''
        if self.__is_connected():
            return True

        return False

    def get_version(self):
        ''' return the holoplay service version '''

        # if the NNG socket is connected to HoloPlay Service App
        if self.__is_connected():

            # request service version
            response = self.__send_message({'cmd': {'info': {}}, 'bin': ''})
            if response != None:

                # if no error was received
                if response[1]['error'] == 0:

                    # version string of the Holo Play Service
                    self.version = response[1]['version']

        return self.version

    def get_devices(self):
        ''' send a request to the service and request the connected devices '''
        ''' this function should return a list object '''

        # if the service is ready
        if self.is_ready():

            # request calibration data
            response = self.__send_message(self.__get_devices())
            if response != None:

                # if no errors were received
                if response[1]['error'] == 0:

                    # get the list of devices with status "ok"
                    devices = [device for device in response[1]['devices'] if device['state'] == "ok"]

                    # iterate through all devices
                    for device in devices:

                        # to flatten the dict, we extract the separate "calibration"
                        # dict and delete it
                        configuration = device['calibration']

                        # parse odd value-object format from calibration json
                        configuration.update({key: value['value'] if isinstance(value, dict) else value for (key,value) in configuration.items()})

                        # calculate the derived values (e.g., tilt, pich, etc.)
                        self.__calculate_derived(configuration)

                        # return the device list
                        return devices

    def display(self, device, lightfield, aspect=None, invert=False, custom_decoder = None):
        ''' display a given lightfield image object on a device '''
        ''' HoloPlay Service expects a lightfield image in LookingGlassQuilt format '''

        # if the service is ready
        if self.is_ready():

            # convert the lightfield into a suitable format for this service
            # NOTE: HoloPlay Service expects a byte stream
            start = timeit.default_timer()
            bytesio = lightfield.decode(self.__decoder_format, custom_decoder)
            print("Decoded lightfield data to BytesIO stream in %.3f s." % (timeit.default_timer() - start))

            if type(bytesio) == io.BytesIO:

                # convert to bytes
                bytes = bytesio.getvalue()

                # free the memory buffer
                bytesio.close()

                # parse the quilt metadata
                settings = {'vx': lightfield.metadata['columns'], 'vy':lightfield.metadata['rows'], 'vtotal': lightfield.metadata['rows'] * lightfield.metadata['columns'], 'aspect': aspect, 'invert': not invert}

                # pass the quilt to the device
                print("The lightfield image '%s' is being sent to '%s' ..." % (lightfield, self))
                self.__send_message(self.__show_quilt(device.configuration['index'], bytes, settings))
                print("Sending message and waiting for response took %.3f s." % (timeit.default_timer() - start))

                return True

            raise TypeError("The '%s' expected lightfield data conversion to %s, but %s was passed." % (self, io.BytesIO, type(bytesio)))

        raise RuntimeError("The '%s' is not ready. Is HoloPlay Service app running?" % (self))

    def clear(self, device):
        ''' clear the display of a given device '''

        # if the service is ready
        if self.is_ready():

            # clear the display
            if self.__send_message(self.__hide(device.configuration['index'])):

                return True

        raise RuntimeError("The '%s' is not ready. Is HoloPlay Service app running?" % (self))

    def __del__(self):
        ''' disconnect from HoloPlay Service App and close NNG socket '''
        if self.__is_connected():

            # disconnect and close socket
            self.__disconnect()
            self.__close()

    # PRIVATE INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: Here is the place to define internal functions required only for this
    #       specific service implementation

    def __is_socket(self):
        ''' check if the socket is open '''
        return (self.__socket != None and self.__socket != 0)

    def __is_connected(self):
        ''' check if a connection to a service is active '''
        return (self.__socket != None and self.__socket != 0 and self.__dialer)

    def __connect(self):
        ''' connect to holoplay service '''

        # set default error value:
        # NOTE: - if communication with HoloPlay Service fails, we use the
        #         direct HID approach to read calibration data
        error = self.client_error.CLIERR_NOERROR.value

        # if there is not already a connection
        if self.__dialer == None:

            # try to connect to the HoloPlay Service
            try:

                self.__dialer = self.__socket.dial(self.__address, block = True)

                # TODO: Set proper error values
                error = self.client_error.CLIERR_NOERROR.value

                print("Connected to HoloPlay Service v%s." % self.get_version())

                return True

            # if the connection was refused
            except pynng.exceptions.ConnectionRefused:

                # Close socket and reset status variable
                self.__close()

                print("Could not connect. Is HoloPlay Service running?")

                return False

        print("Already connected to HoloPlay Service:", self.__dialer)
        return True

    def __disconnect(self):
        ''' disconnect from holoplay service '''

        # if a connection is active
        if self.__is_connected():
            self.__dialer.close()
            self.__dialer = None
            print("Closed connection to %s." % self.name)
            return True

        # otherwise
        print("There is no active connection.")
        return False

    def __close(self):
        ''' close NNG socket '''

        # Close socket and reset status variable
        if self.__is_socket():
            self.__socket.close()

            # reset state variables
            self.__socket = None
            self.__dialer = None
            self.version = ""

    def __send_message(self, input_object):
        ''' send a message to HoloPlay Service '''
        # if a NNG socket is open
        if self.__is_socket():

            # dump a CBOR message
            cbor_dump = cbor.dumps(input_object)

            # send it to the socket
            self.__socket.send(cbor_dump)

            # receive the CBOR-formatted response
            response = self.__socket.recv()

            # return the decoded CBOR response length and its conent
            return [len(response), cbor.loads(response)]

    def __calculate_derived(self, configuration):
        ''' calculate the values derived from the calibration json delivered by HoloPlay Service '''
        configuration['tilt'] = configuration['screenH'] / (configuration['screenW'] * configuration['slope'])
        configuration['pitch'] = - configuration['screenW'] / configuration['DPI']  * configuration['pitch']  * math.sin(math.atan(abs(configuration['slope'])))
        configuration['subp'] = configuration['pitch'] / (3 * configuration['screenW'])
        configuration['ri'], configuration['bi'] = (2,0) if configuration['flipSubp'] else (0,2)
        configuration['fringe'] = 0.0


    # PRIVATE STATIC METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @staticmethod
    def __get_devices():
        ''' tell HoloPlay Service to send the configurations of all devices '''

        command = {
            'cmd': {
                'info': {},
            },
            'bin': '',
        }
        return command

    @staticmethod
    def __show_quilt(dev_index, bindata, settings):
        ''' tell HoloPlay Service to display the incoming quilt '''
        command = {
            'cmd': {
                'show': {
                    'targetDisplay': dev_index,
                    'source': 'bindata',
                    'quilt': {
                        'type': 'image',
                        'settings': settings
                    }
                },
            },
            'bin': bindata,
        }
        return command

    @staticmethod
    def __load_quilt(dev_index, name, settings = None):
        ''' tell HoloPlay Service to load a cached quilt '''
        command = {
            'cmd': {
                'show': {
                    'targetDisplay': dev_index,
                    'source': 'cache',
                    'quilt': {
                        'type': 'image',
                        'name': name
                    },
                },
            },
            'bin': bytes(),
        }

        # if settings were specified
        if settings: command['cmd']['show']['quilt']['settings'] = settings

        return command

    @staticmethod
    def __cache_quilt(dev_index, bindata, name, settings):
        ''' tell HoloPlay Service to cache the incoming quilt '''
        command = {
            'cmd': {
                'cache': {
                    'targetDisplay': dev_index,
                    'quilt': {
                        'type': 'image',
                        'name': name,
                        'settings': settings
                    }
                }
            },
            'bin': bindata,
        }
        return command

    @staticmethod
    def __hide(dev_index):
        ''' tell HoloPlay Service to hide the displayed quilt '''

        command = {
            'cmd': {
                'hide': {
                    'targetDisplay': dev_index,
                },
            },
            'bin': bytes(),
        }
        return command

    @staticmethod
    def __wipe(dev_index):
        ''' tell HoloPlay Service to clear the display (shows the logo quilt) '''
        command = {
            'cmd': {
                'targetDisplay': dev_index,
                'wipe': {},
            },
            'bin': bytes(),
        }
        return command



# DEVICE MANAGER FOR LIGHTFIELD DISPLAYS
###############################################
# the device manager is the factory class for generating device instances of
# the different device types
class DeviceManager(object):

    # DEFINE CLASS PROPERTIES AS PRIVATE MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __dev_count = 0             # number of device instances
    __dev_list = []             # list for initialized device instances
    __dev_active = None         # currently active device instance
    __dev_service = None         # the service used by the device manager


    # CLASS METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @classmethod
    def get_service(cls, service):
        ''' return the service used by this device manager '''
        return cls.__dev_service

    @classmethod
    def set_service(cls, service):
        ''' set the service used by this device manager '''
        cls.__dev_service = service

    @classmethod
    def refresh(cls, emulate_remaining = True):
        ''' refresh the device list using a given service '''

        # if the service ready
        if cls.__dev_service and cls.__dev_service.is_ready():

            instances = []

            # set all (not emulated) devices to "disconnected"
            # NOTE: We don't delete the devices, because that would be more
            #       complex to handle when the user already used the specific
            #       device type instance for their settings
            for d in cls.__dev_list:
                if d.emulated == False:
                    d.connected = False

            # request devices
            devices = cls.__dev_service.get_devices()
            if devices:

                # for each device returned create a LookingGlassDevice instance
                # of the corresponding type
                for idx, device in enumerate(devices):

                    # try to find the instance of this device
                    instance = list(filter(lambda d: d.serial == device['calibration']['serial'], cls.__dev_list))

                    # if no instance of this device exists
                    if not instance:

                        # create a device instance of the corresponding type
                        instance = cls.add_device(device['hardwareVersion'], device)

                        # make this device the active device if no device is active or this is the first connected device
                        if (not cls.get_active() or (cls.get_active() and not cls.get_active().connected)):
                            cls.set_active(instance.id)

                    else:

                        # update the configuration
                        instance[0].configuration = device

                        # make sure the state of the device instance is "connected"
                        instance[0].connected = True

            return None

        print("No HoloPlay Service connection. The device list could not be obtained. ")

    @classmethod
    def add_device(cls, device_type, device_configuration = None):
        ''' add a new device '''

        # try to find the class for the specified type, if it exists
        DeviceTypeClass = [subclass for subclass in BaseDeviceType.__subclasses__() if subclass.type == device_type]

        # call the corresponding type
        if DeviceTypeClass:

            # create the device instance
            device = DeviceTypeClass[0](cls.__dev_service, device_configuration)

            # increment device count
            # NOTE: this number is never decreased to prevent ambiguities of the id
            cls.__dev_count += 1

            # append registered device to the device list
            cls.__dev_list.append(device)

            return device

        # otherwise raise an exception
        raise ValueError("There is no Looking Glass of type '%s'." % device_type)


    @classmethod
    def remove_device(cls, device):
        ''' remove a previously added device '''

        # if the device is in the list
        if device in cls.__dev_list:

            # create the device instance
            print("Removing device '%s' ..." % (device))

            # if this device is the active device, set_active
            if cls.get_active() == device.id: cls.reset_active()

            cls.__dev_list.remove(device)

            return True

        # otherwise raise an exception
        raise ValueError("The device '%s' is not in the list." % device)

    @classmethod
    def add_emulated(cls, filter=None):
        ''' add an emulated device for each supported device type '''

        # for each device type which is not in "except" list
        for DeviceType in set(BaseDeviceType.__subclasses__()) - set([DeviceType for DeviceType in cls.__subclasses__() if DeviceType.type in filter ]):

            # if not already emulated
            if not (DeviceType.type in [d.type for d in cls.__dev_list if d.emulated == True]):

                # create an instance without passing a configuration
                # (that will created an emulated device)
                instance = cls.add_device(DeviceType.type)

        return True

    @classmethod
    def to_list(cls, show_connected = None, show_emulated = None, filter_by_type = None):
        ''' enumerate the devices of this device manager as list '''
        return [d for d in cls.__dev_list if ((show_connected == None or d.connected == show_connected) and (show_emulated == None or d.emulated == show_emulated)) and (filter_by_type == None or d.type == filter_by_type)]

    @classmethod
    def count(cls, show_connected = None, show_emulated = None, filter_by_type = None):
        ''' get number of devices '''
        return len(cls.to_list(show_connected, show_emulated, filter_by_type))

    @classmethod
    def get_active(cls):
        ''' return the active device (i.e., the one currently used by the user) '''
        return cls.__dev_active

    @classmethod
    def set_active(cls, id):
        ''' set the active device (i.e., the one currently used by the user) '''
        for device in cls.__dev_list:
            if (device.id == id):
                cls.__dev_active = device
                return device

        # else raise exception
        raise ValueError("The given device with id '%i' is not in the list." % id)

    @classmethod
    def reset_active(cls):
        ''' set the active device to None '''
        cls.__dev_active = None

    @classmethod
    def exists(cls, serial=None, type=None):
        ''' check if the device instance already exists '''
        if serial and serial in [d.serial for d in cls.__dev_list]:
            return True

        return False


# BASE CLASS FOR DEVICE TYPES
###############################################
# base class for the implementation of different lightfield display types.
# all device types implemented must be a subclass of this base class
class BaseDeviceType(object):


    # PRIVATE MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __type = None           # the unique identifier string of each device type
    __service = None        # the service the device was registered with
    __emulated = False      # is the device instance emulated?
    __connected = True      # is the device still connected?
    __presets = []          # list for the quilt presets

    __lightfield = None     # the lightfield currently displayed on this device


    # INSTANCE METHODS - IMPLEMENTED BY BASE CLASS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: Here is the place to implement functions that should not be overriden
    #       by the subclasses, which represent the specific device types

    def __init__(self, service, configuration=None):
        ''' initialize the device instance '''

        # set essential properties of the class instance
        self.id = DeviceManager.count()

        # if a configuration was passed
        if configuration:

            # use it
            self.configuration = configuration

            # bind the specified service to the device instance
            self.service = service

            # set the state variables for connected devices
            self.connected = True
            self.emulated = False

            # create the device instance
            print("Created class instance for the connected device '%s' of type '%s'." % (self, self.type))

        else:

            # otherwise apply the device type's dummy configuration
            # and assume the device is emulated
            self.configuration = self.emulated_configuration

            # use it
            self.service = None

            # set the state variables for connected devices
            self.connected = False
            self.emulated = True

            # create the device instance
            print("Emulating device '%s' of type '%s'." % (self, self.type))

    def __str__(self):
        ''' the display name of the device when the instance is called '''

        if self.emulated == False: return self.name + " (id: " + str(self.id) + ")"
        if self.emulated == True: return "[Emulated] " + self.name + " (id: " + str(self.id) + ")"


    # TEMPLATE METHODS - IMPLEMENTED BY SUBCLASS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: These methods must be implemented by the subclasses, which represent
    #       the specific device types.
    def display(self, lightfield, custom_decoder = None, **kwargs):
        ''' do some checks if required and hand it over for displaying '''
        # NOTE: This method should only pre-process the image, if the device
        #       type requires that. Then call service methods to display it.

        pass



    # CLASS PROPERTIES - GENRAL
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        self.__id = value

    @property
    def sevice(self):
        return self.__sevice

    @sevice.setter
    def sevice(self, value):
        self.__sevice = value

    @property
    def emulated(self):
        return self.__emulated

    @emulated.setter
    def emulated(self, value):
        self.__emulated = value

    @property
    def connected(self):
        return self.__connected

    @connected.setter
    def connected(self, value):
        self.__connected = value

    @property
    def presets(self):
        return self.__presets

    @presets.setter
    def presets(self, value):
        self.__presets = value

    # CLASS PROPERTIES - CONFIGURATION
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @property
    def configuration(self):
        return self.__configuration

    @configuration.setter
    def configuration(self, value):
        self.__configuration = value

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = value

    @property
    def serial(self):
        # if this is an emulated device
        if self.emulated:
            return self.configuration['serial']
        else:
            return self.configuration['calibration']['serial']

    @serial.setter
    def serial(self, value):
        # if this is an emulated device
        if self.emulated:
            self.configuration['serial'] = value
        else:
            self.configuration['calibration']['serial'] = value

    @property
    def lightfield(self):
        return self.__lightfield

    @lightfield.setter
    def lightfield(self, value):
        self.__lightfield = value



# LOOKING GLASS DEVICE TYPES
###############################################
# Looking Glass 8.9inch
class LookingGlass_8_9inch(BaseDeviceType):

    # PUBLIC MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    type = "standard"                # the unique identifier string of this device type
    name = "8.9'' Looking Glass"     # name of this device type
    formats = [LookingGlassQuilt]    # list of lightfield image formats that are supported
    emulated_configuration = {       # configuration used for emulated devices of this type
                'buttons': [0, 0, 0, 0],
                'calibration': {
                                    'DPI': 338.0,
                                    'configVersion': '1.0',
                                    'screenH': 1600.0,
                                    'screenW': 2560.0,
                                    'serial': 'LKG-1-DUMMY',
                                    'viewCone': 40.0
                                },
                'defaultQuilt': {
                                    'quiltAspect': 1.6,
                                    'quiltX': 4096,
                                    'quiltY': 4096,
                                    'tileX': 5,
                                    'tileY': 9
                                },
                'hardwareVersion': 'standard',
                'hwid': 'LKG0001DUMMY',
                'index': -1,
                'joystickIndex': -1,
                'state': 'ok',
            }

    # INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: Here is the place to define methods required by the BaseClass for any
    #       device type implementations

    def __init__(self, service, configuration=None):
        ''' initialize this specific values of this device type '''
        # call the initialization procedure of the BaseClass
        super().__init__(service, configuration)

        # calculate aspect ratio
        self.configuration['calibration']['aspect'] = self.configuration['calibration']['screenW'] / self.configuration['calibration']['screenH']

    def display(self, lightfield, aspect = None, custom_decoder = None):
        ''' display a given lightfield image object on the device '''
        # NOTE: This method should only do validity checks.
        #       Then call service methods to display the lightfield on the device.

        # if the given lightfield image format is supported
        if type(lightfield) in self.formats:

            # if a service is bound
            if self.service:

                # if no aspect ratio is given, use the device aspect ratio
                if not aspect: aspect = self.configuration['calibration']['aspect']

                print("Requesting '%s' to display the lightfield on '%s' ..." % (self.service, self))

                # request the service to display the lightfield on the device
                if self.service.display(self, lightfield, aspect, custom_decoder):

                    # if that is successful, remember the lightfield for this device
                    self.lightfield = lightfield

                return True

            raise RuntimeError("No service was specified.")

        raise TypeError("The given lightfield image of type '%s' is not supported by this device." % type(lightfield))

    def clear(self):
        ''' clear the device display '''

        # if a service is bound and a lightfield is displayed
        if self.service:

            # if a lightfield is displayed on this device
            if self.lightfield:

                # clear the display
                if self.service.clear(self):

                    # reset the instance's lightfield state variable
                    self.lightfield = None

            return True

        raise RuntimeError("No service was specified.")

    # PRIVATE INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: Here is the place to define internal methods required for your
    #       specific device type implementation

    # def _template_func(self):
    #     ''' DEFINE YOUR REQUIRED DEVICE-SPECIFIC FUNCTIONS HERE '''
    #     return None



# Looking Glass Portrait
class LookingGlass_portrait(BaseDeviceType):

    # PUBLIC MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    type = "portrait"                # the unique identifier string of this device type
    name = "Looking Glass Portrait"  # name of this device type
    formats = [LookingGlassQuilt]    # list of lightfield image formats that are supported
    emulated_configuration = {       # configuration used for emulated devices of this type
                'buttons': [0, 0, 0, 0],
                'calibration': {
                                    'DPI': 324.0,
                                    'configVersion': '1.0',
                                    'screenH': 2048.0,
                                    'screenW': 1536.0,
                                    'serial': 'LKG-5-DUMMY',
                                    'viewCone': 58.0
                                },
                'defaultQuilt': {
                                    'quiltAspect': 0.75,
                                    'quiltX': 3840,
                                    'quiltY': 3840,
                                    'tileX': 8,
                                    'tileY': 6
                                },
                'hardwareVersion': 'portrait',
                'hwid': 'LKG0005DUMMY',
                'index': -1,
                'joystickIndex': -1,
                'state': 'ok',
            }


    # INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: Here is the place to define methods required by the BaseClass for any
    #       device type implementations

    def __init__(self, service, configuration=None):
        ''' initialize this specific values of this device type '''
        # call the initialization procedure of the BaseClass
        super().__init__(service, configuration)

        # calculate aspect ratio
        self.configuration['calibration']['aspect'] = self.configuration['calibration']['screenW'] / self.configuration['calibration']['screenH']

    def display(self, lightfield, aspect = None, invert = None, custom_decoder = None):
        ''' display a given lightfield image object on the device '''
        # NOTE: This method should only do validity checks.
        #       Then call service methods to display the lightfield on the device.

        # if the given lightfield image format is supported
        if type(lightfield) in self.formats:

            # if a service is bound
            if self.service:

                # if no aspect ratio is given, use the device aspect ratio
                if not aspect: aspect = self.configuration['calibration']['aspect']
                if invert == None: invert = self.configuration['calibration']['invView']

                print("Requesting '%s' to display the lightfield on '%s' ..." % (self.service, self))

                # request the service to display the lightfield on the device
                if self.service.display(self, lightfield, aspect, invert, custom_decoder):

                    # if that is successful, remember the lightfield for this device
                    self.lightfield = lightfield

                return True

            raise RuntimeError("No service was specified.")

        raise TypeError("The given lightfield image of type '%s' is not supported by this device." % type(lightfield))

    def clear(self):
        ''' clear the device display '''

        # if a service is bound and a lightfield is displayed
        if self.service and self.lightfield:

            # clear the display
            if self.service.clear(self):

                # reset the instance's lightfield state variable
                self.lightfield = None

                return True

        RuntimeError("TEST")

    # PRIVATE INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: Here is the place to define internal functions required for the
    #       specific device type implementation

    # def __template_func(self):
    #     ''' DEFINE YOUR REQUIRED DEVICE-SPECIFIC FUNCTIONS HERE '''
    #     return None




# TEST CODE
################################################################################
print("")

# create a service using "HoloPlay Service" backend
service = ServiceManager.add(HoloPlayService)

# make the device manager use the created service
DeviceManager.set_service(service)

# refresh the list of connected devices using the active service
DeviceManager.refresh()

# create a set of emulated devices
DeviceManager.add_emulated()

print('[STATS] Found %i devices in the list:' % DeviceManager.count())
for idx, device in enumerate(DeviceManager.to_list()):
    print(" [%i] %s" % (idx, device,) )

print('[STATS] Found %i connected devices:' % DeviceManager.count(show_connected = True, show_emulated = False))
for idx, device in enumerate(DeviceManager.to_list(show_connected = True, show_emulated = False)):
    print(" [%i] %s" % (idx, device,) )

print('[STATS] Found %i emulated devices:' % DeviceManager.count(show_connected = False, show_emulated = True))
for idx, device in enumerate(DeviceManager.to_list(show_connected = False, show_emulated = True)):
    print(" [%i] %s" % (idx, device,) )

# get the active Looking Glass
myLookingGlass = DeviceManager.get_active()
if myLookingGlass:

    # if the connected device is a LKG Portrait
    if myLookingGlass.type == 'standard':

        # load a suitable example lightfield image in LookingGlassQuilt format
        TestQuilt = LightfieldImage.open('looking_glass_tools/quilt.png', LookingGlassQuilt)

    # if the connected device is a LKG Portrait
    elif myLookingGlass.type == 'portrait':

        # add the preset for the quilt
        LookingGlassQuilt.formats.add({'description': 'Portrait, 91 Views', 'quilt_width': 4096, 'quilt_height': 4226, 'view_width': 585, 'view_height': 325, 'rows': 13, 'columns': 7})

        # load a suitable example lightfield image in LookingGlassQuilt format
        TestQuilt = LightfieldImage.open('looking_glass_tools/t_giovanni_1_quilt_resize4_qs7x13.png', LookingGlassQuilt)

    # display the quilt
    myLookingGlass.display(TestQuilt)

    sleep(5)

    # clear the quilt
    myLookingGlass.clear()

    sleep(2)

else:

    print("No device is connected!")

# remove the service
ServiceManager.remove(service)




# TODOs:
# +++++++++++++++++++++++++++++++++++++++++++++++
#
# DEVICES
# - add a "device is busy" flag in the DeviceManager (important for planned asynchronous methods)
#
# LIGHTFIELDS
# - add method to get/set the metadata of a lighgtfield manually
#
