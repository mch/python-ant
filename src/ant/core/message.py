# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################
# pylint: disable=missing-docstring,invalid-name

import struct

from ant.core.exceptions import MessageError
from ant.core.constants import *


class Message(object):
    INCOMPLETE = 'incomplete'
    CORRUPTED = 'corrupted'
    MALFORMED = 'malformed'
    
    def __init__(self, type_=0x00, payload=None):
        self.setType(type_)
        self.setPayload(payload if payload is not None else bytearray())

    def getPayload(self):
        return self.payload

    def setPayload(self, payload):
        if len(payload) > 9:
            raise MessageError('Could not set payload (payload too long).',
                               internal=Message.MALFORMED)
        self.payload = payload

    def getType(self):
        return self.type_

    def setType(self, type_):
        if (type_ > 0xFF) or (type_ < 0x00):
            raise MessageError('Could not set type (type out of range).',
                               internal=Message.CORRUPTED)

        self.type_ = type_

    def getChecksum(self):
        checksum = MESSAGE_TX_SYNC
        checksum ^= len(self.payload)
        checksum ^= self.type_
        for byte in self.payload:
            checksum ^= byte
        return checksum

    def getSize(self):
        return len(self.payload) + 4

    def encode(self):
        raw = bytearray(( MESSAGE_TX_SYNC, len(self.payload), self.type_ ))
        raw += self.payload
        raw.append(self.getChecksum())
        return raw

    def decode(self, raw):
        raw = bytearray(raw)
        if len(raw) < 5:
            raise MessageError('Could not decode (message is incomplete).',
                               internal=Message.INCOMPLETE)

        sync, length, type_ = raw[:3]

        if sync != MESSAGE_TX_SYNC:
            raise MessageError('Could not decode (expected TX sync).',
                               internal=Message.CORRUPTED)
        if length > 9:
            raise MessageError('Could not decode (payload too long).',
                               internal=Message.MALFORMED)
        if len(raw) < (length + 4):
            raise MessageError('Could not decode (message is incomplete).',
                               internal=Message.INCOMPLETE)

        self.setType(type_)
        self.setPayload(raw[3:length + 3])

        if self.getChecksum() != raw[length + 3]:
            raise MessageError('Could not decode (bad checksum).',
                               internal=Message.CORRUPTED)

        return self.getSize()

    def getHandler(self, raw):
        self.decode(raw)
        msg = TYPE_TABLE[self.type_]()
        msg.setPayload(self.payload)
        return msg


class ChannelMessage(Message):
    def __init__(self, type_, payload='', number=0x00):
        Message.__init__(self, type_, bytearray(1) + payload)
        self.setChannelNumber(number)

    def getChannelNumber(self):
        return self.payload[0]

    def setChannelNumber(self, number):
        if (number > 0xFF) or (number < 0x00):
            raise MessageError('Could not set channel number ' \
                                   '(out of range).')

        self.payload[0] = number


# Config messages
class ChannelUnassignMessage(ChannelMessage):
    def __init__(self, number=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_UNASSIGN,
                         number=number)


class ChannelAssignMessage(ChannelMessage):
    def __init__(self, number=0x00, type_=0x00, network=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_ASSIGN,
                                payload=bytearray(2), number=number)
        self.setChannelType(type_)
        self.setNetworkNumber(network)

    def getChannelType(self):
        return self.payload[1]

    def setChannelType(self, type_):
        self.payload[1] = type_

    def getNetworkNumber(self):
        return self.payload[2]

    def setNetworkNumber(self, number):
        self.payload[2] = number


class ChannelIDMessage(ChannelMessage):
    def __init__(self, number=0x00, device_number=0x0000, device_type=0x00,
                 trans_type=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_ID,
                                payload=bytearray(4), number=number)
        self.setDeviceNumber(device_number)
        self.setDeviceType(device_type)
        self.setTransmissionType(trans_type)

    def getDeviceNumber(self):
        return struct.unpack('<H', str(self.payload[1:3]))[0]

    def setDeviceNumber(self, device_number):
        self.payload[1:3] = struct.pack('<H', device_number)

    def getDeviceType(self):
        return self.payload[3]

    def setDeviceType(self, device_type):
        self.payload[3] = device_type

    def getTransmissionType(self):
        return self.payload[4]

    def setTransmissionType(self, trans_type):
        self.payload[4] = trans_type


class ChannelPeriodMessage(ChannelMessage):
    def __init__(self, number=0x00, period=8192):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_PERIOD,
                                payload=bytearray(2), number=number)
        self.setChannelPeriod(period)

    def getChannelPeriod(self):
        return struct.unpack('<H', str(self.payload[1:3]))[0]

    def setChannelPeriod(self, period):
        self.payload[1:3] = struct.pack('<H', period)


class ChannelSearchTimeoutMessage(ChannelMessage):
    def __init__(self, number=0x00, timeout=0xFF):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_SEARCH_TIMEOUT,
                                payload=bytearray(1), number=number)
        self.setTimeout(timeout)

    def getTimeout(self):
        return self.payload[1]

    def setTimeout(self, timeout):
        self.payload[1] = timeout


class ChannelFrequencyMessage(ChannelMessage):
    def __init__(self, number=0x00, frequency=66):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_FREQUENCY,
                                payload=bytearray(1), number=number)
        self.setFrequency(frequency)

    def getFrequency(self):
        return self.payload[1]

    def setFrequency(self, frequency):
        self.payload[1] = frequency


class ChannelTXPowerMessage(ChannelMessage):
    def __init__(self, number=0x00, power=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_TX_POWER,
                                payload=bytearray(1), number=number)
        self.setPower(power)

    def getPower(self):
        return self.payload[1]

    def setPower(self, power):
        self.payload[1] = power


class NetworkKeyMessage(Message):
    def __init__(self, number=0x00, key='\x00' * 8):
        Message.__init__(self, type_=MESSAGE_NETWORK_KEY, payload=bytearray(9))
        self.setNumber(number)
        self.setKey(key)

    def getNumber(self):
        return self.payload[0]

    def setNumber(self, number):
        self.payload[0] = number

    def getKey(self):
        return self.payload[1:]

    def setKey(self, key):
        self.payload[1:] = key


class TXPowerMessage(Message):
    def __init__(self, power=0x00):
        Message.__init__(self, type_=MESSAGE_TX_POWER, payload=bytearray(2))
        self.setPower(power)

    def getPower(self):
        return self.payload[1]

    def setPower(self, power):
        self.payload[1] = power


# Control messages
class SystemResetMessage(Message):
    def __init__(self):
        Message.__init__(self, type_=MESSAGE_SYSTEM_RESET, payload=bytearray(1))


class ChannelOpenMessage(ChannelMessage):
    def __init__(self, number=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_OPEN,
                                number=number)


class ChannelCloseMessage(ChannelMessage):
    def __init__(self, number=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_CLOSE,
                                number=number)


class ChannelRequestMessage(ChannelMessage):
    def __init__(self, number=0x00, message_id=MESSAGE_CHANNEL_STATUS):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_REQUEST,
                                payload=bytearray(1), number=number)
        self.setMessageID(message_id)

    def getMessageID(self):
        return self.payload[1]

    def setMessageID(self, message_id):
        if (message_id > 0xFF) or (message_id < 0x00):
            raise MessageError('Could not set message ID ' \
                                   '(out of range).')

        self.payload[1] = message_id


class RequestMessage(ChannelRequestMessage):
    pass


# Data messages
class ChannelBroadcastDataMessage(ChannelMessage):
    def __init__(self, number=0x00, data='\x00' * 7):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_BROADCAST_DATA,
                                payload=data, number=number)


class ChannelAcknowledgedDataMessage(ChannelMessage):
    def __init__(self, number=0x00, data='\x00' * 7):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_ACKNOWLEDGED_DATA,
                                payload=data, number=number)


class ChannelBurstDataMessage(ChannelMessage):
    def __init__(self, number=0x00, data='\x00' * 7):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_BURST_DATA,
                                payload=data, number=number)


# Channel event messages
class ChannelEventMessage(ChannelMessage):
    def __init__(self, number=0x00, message_id=0x00, message_code=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_EVENT,
                                payload=bytearray(2), number=number)
        self.setMessageID(message_id)
        self.setMessageCode(message_code)

    def getMessageID(self):
        return self.payload[1]

    def setMessageID(self, message_id):
        if (message_id > 0xFF) or (message_id < 0x00):
            raise MessageError('Could not set message ID ' \
                                   '(out of range).')

        self.payload[1] = message_id

    def getMessageCode(self):
        return self.payload[2]

    def setMessageCode(self, message_code):
        if (message_code > 0xFF) or (message_code < 0x00):
            raise MessageError('Could not set message code ' \
                                   '(out of range).')

        self.payload[2] = message_code


# Requested response messages
class ChannelStatusMessage(ChannelMessage):
    def __init__(self, number=0x00, status=0x00):
        ChannelMessage.__init__(self, type_=MESSAGE_CHANNEL_STATUS,
                                payload=bytearray(1), number=number)
        self.setStatus(status)

    def getStatus(self):
        return self.payload[1]

    def setStatus(self, status):
        if (status > 0xFF) or (status < 0x00):
            raise MessageError('Could not set channel status ' \
                                   '(out of range).')

        self.payload[1] = status

#class ChannelIDMessage(ChannelMessage):


class VersionMessage(Message):
    def __init__(self, version='\x00' * 9):
        Message.__init__(self, type_=MESSAGE_VERSION, payload=bytearray(9))
        self.setVersion(version)

    def getVersion(self):
        return self.getPayload()

    def setVersion(self, version):
        if len(version) != 9:
            raise MessageError('Could not set ANT version ' \
                               '(expected 9 bytes).')

        self.setPayload(bytearray(version))


class StartupMessage(Message):
    def __init__(self, startupMessage=0x00):
        Message.__init__(self, type_=MESSAGE_STARTUP, payload=bytearray(1))
        self.setStartupMessage(startupMessage)
        
    def getStartupMessage(self):
        return self.payload[0]
        
    def setStartupMessage(self, startupMessage):
        if (startupMessage > 0xFF) or (startupMessage < 0x00):
            raise MessageError('Could not set start-up message ' \
                                   '(out of range).')
        self.payload[0] = startupMessage


class CapabilitiesMessage(Message):
    def __init__(self, max_channels=0x00, max_nets=0x00, std_opts=0x00,
                 adv_opts=0x00, adv_opts2=0x00):
        Message.__init__(self, type_=MESSAGE_CAPABILITIES, payload=bytearray(4))
        self.setMaxChannels(max_channels)
        self.setMaxNetworks(max_nets)
        self.setStdOptions(std_opts)
        self.setAdvOptions(adv_opts)
        if adv_opts2 is not None:
            self.setAdvOptions2(adv_opts2)

    def getMaxChannels(self):
        return self.payload[0]

    def getMaxNetworks(self):
        return self.payload[1]

    def getStdOptions(self):
        return self.payload[2]

    def getAdvOptions(self):
        return self.payload[3]

    def getAdvOptions2(self):
        return self.payload[4] if len(self.payload) == 5 else 0x00

    def setMaxChannels(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set max channels ' \
                                   '(out of range).')
        self.payload[0] = num

    def setMaxNetworks(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set max networks ' \
                                   '(out of range).')
        self.payload[1] = num

    def setStdOptions(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set std options ' \
                                   '(out of range).')
        self.payload[2] = num

    def setAdvOptions(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set adv options ' \
                                   '(out of range).')
        self.payload[3] = num

    def setAdvOptions2(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set adv options 2 ' \
                                   '(out of range).')
        if len(self.payload) == 4:
            self.payload.append('\x00')
        self.payload[4] = num


class SerialNumberMessage(Message):
    def __init__(self, serial='\x00' * 4):
        Message.__init__(self, type_=MESSAGE_SERIAL_NUMBER)
        self.setSerialNumber(serial)

    def getSerialNumber(self):
        return self.getPayload()

    def setSerialNumber(self, serial):
        if len(serial) != 4:
            raise MessageError('Could not set serial number ' \
                               '(expected 4 bytes).')

        self.setPayload(bytearray(serial))


TYPE_TABLE = {
    MESSAGE_CHANNEL_UNASSIGN: ChannelUnassignMessage,
    MESSAGE_CHANNEL_ASSIGN: ChannelAssignMessage,
    MESSAGE_CHANNEL_ID: ChannelIDMessage,
    MESSAGE_CHANNEL_PERIOD: ChannelPeriodMessage,
    MESSAGE_CHANNEL_SEARCH_TIMEOUT: ChannelSearchTimeoutMessage,
    MESSAGE_CHANNEL_FREQUENCY: ChannelFrequencyMessage,
    MESSAGE_CHANNEL_TX_POWER: ChannelTXPowerMessage,
    MESSAGE_NETWORK_KEY: NetworkKeyMessage,
    MESSAGE_TX_POWER: TXPowerMessage,
    MESSAGE_SYSTEM_RESET: SystemResetMessage,
    MESSAGE_CHANNEL_OPEN: ChannelOpenMessage,
    MESSAGE_CHANNEL_CLOSE: ChannelCloseMessage,
    MESSAGE_CHANNEL_REQUEST: ChannelRequestMessage,
    MESSAGE_CHANNEL_BROADCAST_DATA: ChannelBroadcastDataMessage,
    MESSAGE_CHANNEL_ACKNOWLEDGED_DATA: ChannelAcknowledgedDataMessage,
    MESSAGE_CHANNEL_BURST_DATA: ChannelBurstDataMessage,
    MESSAGE_CHANNEL_EVENT: ChannelEventMessage,
    MESSAGE_CHANNEL_STATUS: ChannelStatusMessage,
    MESSAGE_VERSION: VersionMessage,
    MESSAGE_CAPABILITIES: CapabilitiesMessage,
    MESSAGE_SERIAL_NUMBER: SerialNumberMessage,
    MESSAGE_STARTUP: StartupMessage,
}
