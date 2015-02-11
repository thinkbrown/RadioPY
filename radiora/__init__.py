import xml.etree.ElementTree as ET
import telnetlib
import threading

class TelnetConnection(threading.Thread):
	def __init__(self, Hostname, Username, Password):
		threading.Thread.__init__(self)
		self.host = Hostname
		self.user = Username
		self.password = Password
		self.connected = False
		self.handler = None
		self.tn = telnetlib.Telnet(self.host)
	def open(self):
		self.tn.open(self.host)
		self.tn.read_until('login: ')
		self.tn.write(self.user + '\r\n')
		self.tn.read_until('password: ')
		self.tn.write(self.password + '\r\n')
		self.tn.read_until("GNET> ")
		self.connected = True
		self.start()
	def close(self):
		self.connected = False
		self.join()
		self.tn.close()
	def isConnected(self):
		return self.connected
	def setHandler(self, handler):
		self.handler = handler 
	def send(self, string):
		if not self.connected:
			self.openConnection()
		self.tn.write(string + '\r\n')
	def run(self):
		while self.connected:
			response = self.tn.read_until('\r\n', 1)
			if response:
				response = response.replace( '\r\n', '' )
				response = response.replace( 'GNET> ', '' )
				if self.handler is not None:
					self.handler(response)

class Controller:
	def __init__(self, Hostname, Username, Password, persistConn = False):
		self.host = Hostname
		self.integID = {}
		self.tn = TelnetConnection(Hostname, Username, Password)
		self.tn.setHandler(self.responseParser)
		
		self.cond = threading.Condition()
		# condition var protects these 2 values
		self.expectedId = None
		self.requestedResp = None
	def close(self):
		self.tn.close()
	def sendCommand(self, commandString, Feedback = True):
		if not self.tn.isConnected():
			self.tn.open()
		#print 'sendCommand', commandString
		self.waitIntegID = None
		self.tn.send(commandString)
		
		# If we are expecting a response, we need to lock
		# and wait for the parser to get the response for us
		if Feedback:
			self.cond.acquire()
			self.requestedResp = None  # Clear any previous
			self.expectedId = commandString.split(',')[1]			
			#print 'Waiting for id', self.expectedId 
			resp = None
			while True:
				if self.requestedResp:
					resp = self.requestedResp
					break;
				self.cond.wait(1)
			self.expectedId = None
			self.cond.release()

			if not resp:  # If we timed out, there is no response
				return False
			else:
				# Otherwise, return the last value, 
				#which should be the state we are looking for
				return resp[-1].rstrip()

	def responseParser(self, resp):
	        if resp.startswith(('~')):
			resparray = resp.strip('~').split(',')
			handled = False
        		
			# Lock, and check if we are waiting for this reponse
			self.cond.acquire()
			if self.expectedId:
				self.requestedResp = resparray
				self.cond.notify()
				handled = True
			self.cond.release()
			
			if not handled:
				if resparray[0] == 'DEVICE':
					self.handleDevice(resparray)
				elif resparray[0] == 'OUTPUT':
					self.handleOutput(resparray)
	        else:
        	        print 'Handler unknown response: \"%s\"' % resp
			return
	 
	def handleOutput(self, resp):
		if resp[2] == '29':   # Skip undocumented output command 
			return 

		id = resp[1]
		if id in self.integID:
			output = self.integID[id]
			if resp[2] == '1':  # zone Set
				print 'ID %d %-20s %-25s now at %3d' % (int(resp[1]), output.getRoom().getName(), output.getName(), int(float(resp[3]))), '%'
			else:
				print 'handleOutput', resp
		else:
			print 'handleOutput', resp
	
	def handleDevice(self, resp):
		id = resp[1]
		if id in self.integID:
			kp = self.integID[id]
			if resp[3] == '3':  # button push
				button = int(resp[2])
				print 'ID %d %-20s %-25s B%d %s pushed' % (int(id), kp.getRoom().getName(), kp.getName(), button, kp.findButton(button-1).getName() )
			elif resp[3] == '9':  # led change
				button = int(resp[2])-80  # subtract 80 for led offset
				print 'ID %d %-20s %-25s B%d %-10s led = %d' % (int(id), kp.getRoom().getName(), kp.getName(), button, kp.findButton(button-1).getName(), int(resp[4]))
			else:
				print 'handleDevice', resp
		else:
			print 'handleDevice', resp
	
	def getXML(self):
		import urllib2
		xmlfile = urllib2.urlopen('http://' + self.host + '/DbXmlInfo.xml')
		self.xmldata = xmlfile.read()
		xmlfile.close()
		return self.xmldata
	def registerIntegId(self, integid, obj):
		self.integID[integid] = obj
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
		self.Controller.registerIntegId(output.getIntegrationID(), output)
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
	def __init__(self, Name, IntegrationID, Controller, Room):
		print 'Output:', Name
		self.Name = Name
		self.IntegrationID = IntegrationID
		self.Controller = Controller
		self.Room = Room
	def Set(self, level):
		self.Controller.sendCommand('\x23' + 'OUTPUT,' + str(self.IntegrationID) + ',1,' + str(level))
	def getName(self):
		return self.Name
	def getRoom(self):
		return self.Room
	def getIntegrationID(self):
		return self.IntegrationID
	def Get(self):
		response = self.Controller.sendCommand('?' + 'OUTPUT,' + str(self.IntegrationID) + ',1')
		if response:
			level = int(float(response))
			return level
		else: return 'No Response'

class Keypad:
	def __init__(self, Name, IntegrationID, Controller, Room):
		print 'Keypad:', Name
		self.Name = Name
		self.IntegrationID = IntegrationID
		self.Buttons = []
		self.Controller = Controller
		self.Controller.registerIntegId(self.IntegrationID, self)
		self.Room = Room
	def addButton(self, button):
		self.Buttons.append(button)
	def getButtons(self):
		return self.Buttons
	def getName(self):
		return self.Name
	def getRoom(self):
		return self.Room
	def getIntegrationID(self):
		return self.IntegrationID
        def getStatus(self):
                for button in self.Buttons:
                	print button.getState(), button.getName()
	def findButton(self,num):
		return self.Buttons[num]
	

class Button:
	def __init__(self, Engraving, Number, IntegrationID, Controller):
		print 'Button:', Number, Engraving
		self.Engraving = Engraving
		self.Number = Number
		self.IntegrationID = IntegrationID
		self.Controller = Controller
	def push(self):
		self.Controller.sendCommand('\x23' + 'DEVICE,' + self.IntegrationID + ',' + str(self.Number) + ',3', False)
		self.Controller.sendCommand('\x23' + 'DEVICE,' + self.IntegrationID + ',' + str(self.Number) + ',4', False)
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
				newroom.addOutput(Output(output.attrib['Name'], output.attrib['IntegrationID'], self.Controller, newroom))
			for dg in loads.find('DeviceGroups'):
				for device in dg.iter('Device'):
					if device.attrib['DeviceType'] == 'SEETOUCH_KEYPAD':
						newroom.addKeypad(self.parseKeypad(device, newroom))
					if device.attrib['DeviceType'] == 'HYBRID_SEETOUCH_KEYPAD':
						newroom.addKeypad(self.parseKeypad(device, newroom))
					if device.attrib['DeviceType'] == 'SEETOUCH_TABLETOP_KEYPAD':
						newroom.addKeypad(self.parseKeypad(device, newroom))
			self.Rooms.append(newroom)

	def parseKeypad(self, device, newroom):
		newkeypad = Keypad(device.attrib['Name'], device.attrib['IntegrationID'], self.Controller, newroom)
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
				#print output.getName(),': ', output.Get(), '%'
				print '%25s : %3d' % (output.getName(), output.Get()), '%'
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
