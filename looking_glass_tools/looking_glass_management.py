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

# The Socket interface classes are based on freeHPC https://github.com/regcs/freehpc

# import bpy
import timeit
from enum import Enum

# modules required by the Holo Play Service socket
import pynng, cbor, math

# just for debugging
from pprint import pprint
from time import sleep
# from . holoplay_service_api_commands import *

# CLASS FOR LIGHTFIELD DISPLAY SOCKETS
###############################################
# socket factory class to handle opening a socket of specificied type
class Socket(object):

    # CLASS METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @classmethod
    def open(self, socket_type):
        ''' open the socket of the specified type '''

        # try to find the class for the specified type, if it exists
        SocketTypeClass = [subclass for subclass in BaseSocketType.__subclasses__() if subclass.type == socket_type]

        # if a socket of the specified type was found, create and return its instance
        if SocketTypeClass: return SocketTypeClass[0]()

        # otherwise raise an exception
        raise ValueError("There is no socket of type '%s'." % socket_type)

    # NOTE: WE COULD IMPLEMENT A VLASS METHOD FOR CLOSING SOCKETS HERE
    #       INSTEAD OF IMPLEMENTING THE "CLOSE()" METHOD IN EACH SOCKET.
    #       BUT AT THE MOMENT I THINK IT IS BETTER TO DO IT IN EACH TYPE CLASS.


# the base socket type class used for handling lightfield display communication
class BaseSocketType(object):

    # DEFINE CLASS PROPERTIES AS PROTECTED MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    type = None                                         # the unique identifier string of a socket type (required for the factory class)

    # DEFINE CLASS PROPERTIES AS PRIVATE MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __socket = None                                     # NNG socket instance
    __version = ""                                      # version string of the socket service

    # TEMPLATE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # these methods must be implemented by subclasses
    def __init__(self):
        ''' handle initialization of the class instance and the specific socket '''
        pass

    def is_socket(self):
        ''' handle checking if the socket is open '''
        pass

    def is_connected(self):
        ''' handle checking if the socket is connected to the service '''
        pass

    def connect(self):
        ''' handle connection to the socket service '''
        pass

    def disconnect(self):
        ''' handle disconnection from the socket service '''
        pass

    def close(self):
        ''' handle closing of the socket '''
        pass

    # CLASS PROPERTIES
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @property
    def socket(self):
        return self.__socket

    @socket.setter
    def socket(self, value):
        self.__socket = value

    @property
    def version(self):
        return self.__version

    @version.setter
    def version(self, value):
        self.__version = value


# Holo Play Service Socket for Looking Glass lightfield displays
class HoloPlayServiceSocket(BaseSocketType):

    # DEFINE CLASS PROPERTIES AS PROTECTED MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    type = 'holoplayservice'                            # the unique identifier string of this socket type (required for the factory class)

    # DEFINE CLASS PROPERTIES AS PRIVATE MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __address = 'ipc:///tmp/holoplay-driver.ipc'        # driver url (alternative: "ws://localhost:11222/driver")
    __dialer = None                                     # NNG Dialer of the socket

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
        self.socket = pynng.Req0(recv_timeout = timeout)

        # if the NNG socket is open
        if self.is_socket():

            print("Created socket: ", self.socket)

    def is_socket(self):
        ''' check if the socket is open '''
        return (self.socket != None and self.socket != 0)

    def is_connected(self):
        ''' check if a connection to a service is active '''
        return (self.socket != None and self.socket != 0 and self.__dialer)

    def connect(self):
        ''' connect to holoplay service '''

        # set default error value:
        # NOTE: - if communication with HoloPlay Service fails, we use the
        #         direct HID approach to read calibration data
        error = self.client_error.CLIERR_NOERROR.value

        # if there is not already a connection
        if self.__dialer == None:

            # try to connect to the HoloPlay Service
            try:

                self.__dialer = self.socket.dial(self.__address, block = True)

                # TODO: Set proper error values
                error = self.client_error.CLIERR_NOERROR.value

                print("Connected to HoloPlay Service v%s." % self.get_version())

                return True

            # if the connection was refused
            except pynng.exceptions.ConnectionRefused:

                # Close socket and reset status variable
                self.close()

                print("Could not connect. Is HoloPlay Service running?")

                return False

        print("Already connected to HoloPlay Service:", self.__dialer)
        return True


    def disconnect(self):
        ''' disconnect from holoplay service '''

        # if a connection is active
        if self.is_connected():
            self.__dialer.close()
            self.__dialer = None
            print("Closed connection to HoloPlay Service.")
            return True

        # otherwise
        print("There is no active connection.")
        return False

    def close(self):
        ''' close NNG socket '''

        # Close socket and reset status variable
        if self.is_socket():
            self.socket.close()

            # reset state variables
            self.socket = None
            self.version = ""
            self.__dialer = None


    def get_version(self):
        ''' get the holoplay service version '''

        # if the socket is connected
        if self.is_connected():

            # request service version
            response = self.__nng_send_message({'cmd': {'info': {}}, 'bin': ''})
            if response != None:

                # if no error was received
                if response[1]['error'] == 0:

                    # version string of the Holo Play Service
                    self.version = response[1]['version']

        return self.version


    def get_devices(self):
        ''' send a request to the service and request the connected devices '''
        ''' this function should return a list object '''

        # if the NNG socket is open
        if self.is_connected():

            # request calibration data
            response = self.__nng_send_message({'cmd': {'info': {}}, 'bin': ''})
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


    # PRIVATE INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # send a NNG message to the HoloPlay Service
    def __nng_send_message(self, input_object):
        ''' send a message to HoloPlay Service '''

        # if a NNG socket is open
        if self.is_socket():

            # dump a CBOR message
            cbor_dump = cbor.dumps(input_object)

            # send it to the socket
            self.socket.send(cbor_dump)
            # print("---------------")
            # print("Command (" + str(len(cbor_dump)) + " bytes, "+str(len(input_object['bin']))+" binary): ")
            # print(input_object['cmd'])
            # print("---------------")

            # receive the CBOR-formatted response
            response = self.socket.recv()

            # print("Response (" + str(len(response)) + " bytes): ")
            cbor_load = cbor.loads(response)
            # print(cbor_load)
            # print("---------------")

            # return the response length and its conent
            return [len(response), cbor_load]

    # calculate the values derived from the calibration json delivered by HoloPlay Service
    def __calculate_derived(self, configuration):

        # calculate any values derived values from the cfg values
        configuration['tilt'] = configuration['screenH'] / (configuration['screenW'] * configuration['slope'])
        configuration['pitch'] = - configuration['screenW'] / configuration['DPI']  * configuration['pitch']  * math.sin(math.atan(abs(configuration['slope'])))
        configuration['subp'] = configuration['pitch'] / (3 * configuration['screenW'])
        configuration['ri'], configuration['bi'] = (2,0) if configuration['flipSubp'] else (0,2)
        configuration['fringe'] = 0.0


# FACTORY CLASS FOR LOOKING GLASS DEVICES
###############################################
# Factory class for generating looking glass device instances of the different
# device types (connected devices + emulated deviced)
class LookingGlassDevice(object):

    # DEFINE CLASS PROPERTIES AS PRIVATE MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __dev_count = 0             # number of device instances
    __dev_list = []             # list for initialized device instances
    __dev_active = None         # currently active device instance


    # CLASS METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @classmethod
    def from_socket(cls, socket, emulate_remaining = True):
        ''' obtain the complete device list from a socket service '''

        # if the socket is open and connected
        if socket and socket.is_connected():

            instances = []

            # TODO: HANDLE DELETION OF DISCONNECTED


            # request devices
            devices = socket.get_devices()
            if devices:

                print("Number of connected devices:", len(devices))

                # for each device returned create a LookingGlassDevice instance
                # of the corresponding type
                for idx, device in enumerate(devices):

                    # create a LookingGlassDevice instance
                    # of the corresponding type
                    instance = cls.add_device(device['hardwareVersion'], device)

                    # make the first device the active device if no device is active
                    if idx == 0 and not cls.get_active(): cls.set_active(instance.id)

            return None

        print("No HoloPlay Service connection. The device list could not be obtained. ")

    @classmethod
    def add_device(cls, device_type, device_configuration = None):
        ''' add a new device '''

        # try to find the class for the specified type, if it exists
        DeviceTypeClass = [subclass for subclass in LookingGlassDeviceType.__subclasses__() if subclass.type == device_type]

        # call the corresponding type
        if DeviceTypeClass:

            device = DeviceTypeClass[0](device_configuration)

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
            if cls.get_active() == device.id: LookingGlassDevice.reset_active()

            cls.__dev_list.remove(device)

            return True

        # otherwise raise an exception
        raise ValueError("The device '%s' is not in the list." % device)

    @classmethod
    def add_emulated(cls, filter=None):
        ''' add an emulated device for each supported device type '''

        # for each evice type which is not in "except" list
        for DeviceType in set(LookingGlassDeviceType.__subclasses__()) - set([DeviceType for DeviceType in cls.__subclasses__() if DeviceType.type in filter ]):

            # create an instance without passing a configuration
            # (that will created an emulated device)
            instance = cls.add_device(DeviceType.type)

        return True


    @classmethod
    def to_list(cls, show_connected = True, show_emulated = True, filter_by_type = None):
        ''' enumerate the devices of this factory class '''

        # list all
        if show_connected == True and show_emulated == True:
            return [d for d in cls.__dev_list if (filter_by_type == None or d.type in filter_by_type)]

        # only connected devices
        elif show_connected == True and show_emulated == False:
            return [d for d in cls.__dev_list if d.emulated == False and (filter_by_type == None or d.type == filter_by_type)]

        # only emulated devices
        elif show_connected == False and show_emulated == True:
            return [d for d in cls.__dev_list if d.emulated == True and (filter_by_type == None or d.type == filter_by_type)]

    @classmethod
    def count(cls, show_connected = True, show_emulated = True, filter_by_type = None):
        ''' get number of devices '''

        return len(cls.to_list(show_connected, show_emulated, filter_by_type))

    @classmethod
    def get_active(cls):
        ''' get the active device (i.e., the one currently used by the user) '''

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

    # STATIC METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # CLASS PROPERTIES
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# BASE CLASS FOR DEVICE TYPES
###############################################
class LookingGlassDeviceType(object):

    # PUBLIC MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __type = None           # the unique identifier string of each device type
    __emulated = False      # the unique identifier string of each device type

    # PRIVATE MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    __presets = []  # list for the quilt presets


    # INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def __init__(self, configuration=None):
        ''' Initialize the device type instance '''

        # set essential properties of the class instance
        self.id = LookingGlassDevice.count()

        # initialize the device type specific values
        self.init()

        # if a configuration was passed
        if configuration:

            # use it
            self.configuration = configuration

            # create the device instance
            print("Successfully registered connected device '%s' of type '%s'." % (self, self.type))

        else:

            # otherwise apply the device type's dummy configuration
            # and assume the device is emulated
            self.configuration = self._dummy_configuration()
            self.emulated = True

            # create the device instance
            print("Successfully emulated device '%s' of type '%s'." % (self, self.type))

    # the display name of the device when the instance is called
    def __str__(self):
        ''' Output name of the device type instance '''

        if self.emulated == False: return self.name + " (id: " + str(self.id) + ")"
        if self.emulated == True: return "[Emulated] " + self.name + " (id: " + str(self.id) + ")"

    # add a quilt preset
    def add_preset(self, description, quilt_width, quilt_height, columns, rows):
        ''' Add a quilt preset to the device type instance '''

        # append the preset to the list
        self.presets.append({
                                "id": len(self.presets),
                                "description": description,
                				"width": quilt_width,
                				"height": quilt_height,
                				"columns": columns,
                				"rows": rows,
                				"totalViews": columns * rows,
                				"quiltOffscreen": None,
                				"viewOffscreens": []
                            })

        # return the added dict as result
        return self.presets[-1]

    # remove a preset
    def remove_preset(self, id):
        ''' Remove a quilt preset from the device type instance '''

        for preset in self.presets:
            if (preset.id == id):

                # create the device instance
                print("Removing preset '%i' ..." % (id))

                self.presets.remove(preset)

            return True

        # otherwise raise an exception
        raise ValueError("The preset with id '%i' is not in the list." % id)



    # CLASS PROPERTIES
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        self.__id = value

    @property
    def emulated(self):
        return self.__emulated

    @emulated.setter
    def emulated(self, value):
        self.__emulated = value

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = value

    @property
    def configuration(self):
        return self.__configuration

    @configuration.setter
    def configuration(self, value):
        self.__configuration = value

    @property
    def presets(self):
        return self.__presets

    @presets.setter
    def presets(self, value):
        self.__presets = value


# DEVICE TYPE CLASSES
###############################################
# Looking Glass 8.9inch
class LookingGlass_8_9inch(LookingGlassDeviceType):

    # PROTECTED MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    type = "standard"         # the unique identifier string of this device type


    # INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def init(self):
        ''' Initialize the type specific values '''

        # set the display name of the device type
        self.name = "8.9'' Looking Glass"

        # define the quilt presets supported by this Looking Glass type
        self.add_preset("2k Quilt, 32 Views", 2048, 2048, 4, 8)
        self.add_preset("4k Quilt, 45 Views", 4095, 4095, 5, 9)
        self.add_preset("8k Quilt, 45 Views", 4096 * 2, 4096 * 2, 5, 9)



    # PRIVATE INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # the dummy configuration for this Looking Glass type
    def _dummy_configuration(self):
        dummy = {

				# device information
				'index': -1,
				'hdmi': "LKG0001DUMMY",
				'name': self.name,
				'serial': "LKG-1-DUMMY",
				'type': "portrait",

				# window & screen properties
				'x': -1536,
				'y': 0,
				'width': 1536,
				'height': 2048,
				'aspectRatio': 0.75,

				# calibration data
				'pitch': 354.70953369140625,
				'tilt': -0.11324916034936905,
				'center': -0.11902174353599548,
				'subp': 0.0001302083401242271,
				'fringe': 0.0,
				'ri': 0,
				'bi': 2,
				'invView': 1,

				# viewcone
				'viewCone': 58

                }

        return dummy


# Looking Glass Portrait
class LookingGlass_portrait(LookingGlassDeviceType):

    # PROTECTED MEMBERS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    type = "portrait"         # the unique identifier string of this device type


    # INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def init(self):

        # set the display name of the device type
        self.name = "Looking Glass Portrait"

        # define the quilt presets supported by this Looking Glass type
        self.add_preset("Portrait, 48 Views", 3360, 3360, 8, 6)



    # PRIVATE INSTANCE METHODS
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # the dummy configuration for this Looking Glass type
    def _dummy_configuration(self):
        dummy = {

				# device information
				'index': -1,
				'hdmi': "LKG0001DUMMY",
				'name': self.name,
				'serial': "LKG-1-DUMMY",
				'type': "portrait",

				# window & screen properties
				'x': -1536,
				'y': 0,
				'width': 1536,
				'height': 2048,
				'aspectRatio': 0.75,

				# calibration data
				'pitch': 354.70953369140625,
				'tilt': -0.11324916034936905,
				'center': -0.11902174353599548,
				'subp': 0.0001302083401242271,
				'fringe': 0.0,
				'ri': 0,
				'bi': 2,
				'invView': 1,

				# viewcone
				'viewCone': 58

                }

        return dummy


# TEST CODE
################################################################################
print("")

# open a HoloPlay Service socket
socket = Socket.open('holoplayservice')

# connect the app to the socket service
socket.connect()

# request the connected Looking Glasses from the given socket
LookingGlassDevice.from_socket(socket)

# get set of emulated devices
LookingGlassDevice.add_emulated()

print('[STATS] Found %i connected devices:' % LookingGlassDevice.count(show_connected = True, show_emulated = False))
for idx, device in enumerate(LookingGlassDevice.to_list(show_connected = True, show_emulated = False)):
    print(" [%i] %s" % (idx, device,) )

print('[STATS] Found %i emulated devices:' % LookingGlassDevice.count(show_connected = False, show_emulated = True))
for idx, device in enumerate(LookingGlassDevice.to_list(show_connected = False, show_emulated = True)):
    print(" [%i] %s" % (idx, device,) )

# disconnect from socket Service
socket.disconnect()

# close the socket
socket.close()

# dev_1 = LookingGlassDevice.add_device("standard")
# dev_2 = LookingGlassDevice.add_device("portrait")
# print('[STATS] Enumerate registered devices:')
# print(LookingGlassDevice.enumerate())
# LookingGlassDevice.set_active(0)
# active = LookingGlassDevice.get_active()
# print(active.emulated)
# LookingGlassDevice.remove_device(dev_1)
