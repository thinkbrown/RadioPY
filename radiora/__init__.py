import xml.etree.ElementTree as ET
import telnetlib

class Controller:
	def __init__(self, Hostname, Username, Password):
		self.host = Hostname
		self.user = Username
		self.password = Password
	def sendCommand(self, commandString, Feedback = True):
		#print 'sendCommand', commandString
		tn = telnetlib.Telnet(self.host)
		tn.read_until('login: ')
		tn.write(self.user + '\r\n')
		tn.read_until('password: ')
		tn.write(self.password + '\r\n')
		tn.read_until("GNET> ")
		tn.write(commandString + '\r\n')
		if Feedback:
			response =  tn.read_until("\n", 1)
			tn.write('\x1d' + '\r\n')
			tn.close()
			if response == 'GNET> ':
				return False
			else:
				return response
		else:
			tn.read_until("GNET> ")
			tn.write('\x1d' + '\r\n')
			tn.close()
	def responseParser(self, response):
		resparray = response.split(',')
		val = resparray[-1].rstrip()
		return val
	def getXML(self):
		import urllib2
		xmlfile = urllib2.urlopen('http://' + self.host + '/DbXmlInfo.xml')
		self.xmldata = xmlfile.read()
		xmlfile.close()
		return self.xmldata
class Room:
	def __init__(self, Name, IntegrationID, Controller):
		print 'Adding Room:', Name
		self.Name = Name
		self.IntegrationID = IntegrationID
		self.Controller = Controller
		self.Outputs = []
		self.Keypads = []
	def addOutput(self, output):
		self.Outputs.append(output)
	def getOutputs(self):
		return self.Outputs
	def findOutput(self, Name):
		for output in self.Outputs:
			if output.getName() == Name:
				return output
		return "ONF"
	def listOutputs(self):
		outputs = []
		for output in self.Outputs:
			outputs.append(output.getName())
		return outputs
	def addKeypad(self, keypad):
		self.Keypads.append(keypad)
	def getKeypads(self):
		return self.Keypads
	def getName(self):
		return self.Name
	def getIntegrationID(self):
		return self.IntegrationID
	def Set(self, level):
		for output in self.Outputs:
			output.Set(level)


class Output:
	def __init__(self, Name, IntegrationID, Controller):
		print 'Output:', Name
		self.Name = Name
		self.IntegrationID = IntegrationID
		self.Controller = Controller
	def Set(self, level):
		self.Controller.sendCommand('\x23' + 'OUTPUT,' + str(self.IntegrationID) + ',1,' + str(level))
	def getName(self):
		return self.Name
	def getIntegrationID(self):
		return self.IntegrationID
	def Get(self):
		response = self.Controller.sendCommand('?' + 'OUTPUT,' + str(self.IntegrationID) + ',1')
		if response:
			level = int(float(self.Controller.responseParser(response)))
			return level
		else: return 'No Response'

class Keypad:
	def __init__(self, Name, IntegrationID, Controller):
		print 'Keypad:', Name
		self.Name = Name
		self.IntegrationID = IntegrationID
		self.Buttons = []
		self.Controller = Controller
	def addButton(self, button):
		self.Buttons.append(button)
	def getButtons(self):
		return self.Buttons
	def getName(self):
		return self.Name
	def getIntegrationID(self):
		return self.IntegrationID
        def getStatus(self):
                for button in self.Buttons:
                	print button.getState(), button.getName()

	

class Button:
	def __init__(self, Engraving, Number, IntegrationID, Controller):
		print 'Button:', Number, Engraving
		self.Engraving = Engraving
		self.Number = Number
		self.IntegrationID = IntegrationID
		self.Controller = Controller
	def push(self):
		self.Controller.sendCommand('\x23' + 'DEVICE,' + self.IntegrationID + ',' + self.Number + ',3', False)
		self.Controller.sendCommand('\x23' + 'DEVICE,' + self.IntegrationID + ',' + self.Number + ',4', False)
	def getName(self):
		return self.Engraving
	def getState(self):
		rval = False
		# Getting the button State would be useless, instead look at the state of the led
		response = self.Controller.sendCommand('?' + 'DEVICE,' + self.IntegrationID + ',' + str(80 + self.Number) + ',9')
		if response:
			rval = self.Controller.responseParser(response)
		return rval


class House:
	def __init__(self, Controller, Name = 'House'):
		self.Rooms = []
		self.Name = Name
		self.Controller = Controller
	def load(self):
		import xml.etree.ElementTree as ET
		root = ET.fromstring(self.Controller.getXML())
		areas = root.find('Areas')[0].find('Areas')
		for loads in areas:
			print '\n'
			newroom = Room(loads.attrib['Name'], loads.attrib['IntegrationID'], self.Controller)
			for output in loads.find('Outputs'):
				newroom.addOutput(Output(output.attrib['Name'], output.attrib['IntegrationID'], self.Controller))
			for dg in loads.find('DeviceGroups'):
				for device in dg.iter('Device'):
					if device.attrib['DeviceType'] == 'SEETOUCH_KEYPAD':
						newroom.addKeypad(self.parseKeypad(device))
					if device.attrib['DeviceType'] == 'HYBRID_SEETOUCH_KEYPAD':
						newroom.addKeypad(self.parseKeypad(device))
					if device.attrib['DeviceType'] == 'SEETOUCH_TABLETOP_KEYPAD':
						newroom.addKeypad(self.parseKeypad(device))
			self.Rooms.append(newroom)

	def parseKeypad(self, device):
		newkeypad = Keypad(device.attrib['Name'], device.attrib['IntegrationID'], self.Controller)
		for comp in device.iter('Component'):
			if comp.attrib['ComponentType'] == 'BUTTON':
				button = comp[0]
				number = int(comp.attrib['ComponentNumber'])
				if 'ButtonType' in button.attrib and button.attrib['ButtonType'] != 'MasterRaiseLower':
					name = 'Unnamed Button'		
					if 'Engraving' in button.attrib:
						name = button.attrib['Engraving']
					newkeypad.addButton(Button(name, number, newkeypad.getIntegrationID(), self.Controller))
		return newkeypad

	def addRoom(self,room):
		self.Rooms.append(room)
	def getRooms(self):
		return self.Rooms
	def findRoom(self, Name):
		for room in self.Rooms:
			if room.getName() == Name:
				return room
		return "RNF"
	def dictRooms(self):
		roomlist = {}
		for room in self.Rooms:
			roomlist[room.getIntegrationID()] = room.getName()
		return roomlist
	def listRooms(self):
		roomlist = []
		for room in self.Rooms:
			roomlist.append(room.getName())
		return roomlist
	def getStatus(self):
		for room in self.Rooms:
			for output in room.getOutputs():
				print output.getName(),': ', output.Get(), '%'
	def Shutdown(self):
		for room in self.Rooms:
			for output in room.getOutputs():
				output.Set(0)
	def Showtime(self):
		for room in self.Rooms:
			for output in room.getOutputs():
				output.Set(100)
	def getController(self):
		return self.Controller


'''
radiora = Controller('10.0.1.44', 'lutron', 'integration')
house = House(radiora)
house.load()


- module -

main = radiora.Controller('10.0.1.44', 'lutron', 'integration')
house = radiora.House(main)
house.load('DbXmlInfo.xml')

'''
