import xml.etree.ElementTree as ET
import telnetlib

class Controller:
	def __init__(self, Hostname, Username, Password):
		self.host = Hostname
		self.user = Username
		self.password = Password
	def sendCommand(self, commandString, Feedback = True):
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
	

class Button:
	def __init__(self, Engraving, Number, IntegrationID, Controller):
		self.Engraving = Engraving
		self.Number = Number
		self.IntegrationID = IntegrationID
		self.Controller = Controller
	def push(self):
		self.Controller.sendCommand('\x23' + 'DEVICE,' + self.IntegrationID + ',' + self.Number + ',3', False)
		self.Controller.sendCommand('\x23' + 'DEVICE,' + self.IntegrationID + ',' + self.Number + ',4', False)
	def getName(self):
		return self.Engraving


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
			newroom = Room(loads.attrib['Name'], loads.attrib['IntegrationID'], self.Controller)
			for newoutput in loads[3]:
				newroom.addOutput(Output(newoutput.attrib['Name'], newoutput.attrib['IntegrationID'], self.Controller))
			for newkeypad in loads[0]:
				for devicegroup in newkeypad[0]:
					if devicegroup.tag == 'Device' and devicegroup.attrib['DeviceType'] == 'SEETOUCH_KEYPAD':
						newkeypad = Keypad(devicegroup.attrib['Name'], devicegroup.attrib['IntegrationID'], self.Controller)
						for buttons in devicegroup[0]:
							if buttons.tag == 'Component' and buttons.attrib['ComponentType'] == 'BUTTON':
								if 'Engraving' in buttons[0].attrib:
									newkeypad.addButton(Button(buttons[0].attrib['Engraving'], buttons[0].attrib['Name'].split(' ')[-1], newkeypad.getIntegrationID(), self.Controller))
								else:
									newkeypad.addButton(Button('Unnamed Button', buttons[0].attrib['Name'].split(' ')[-1], newkeypad.getIntegrationID(), self.Controller))
						newroom.addKeypad(newkeypad)
			self.Rooms.append(newroom)


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
