#! /usr/bin/python
 
import os
from gps import *
from time import *
from haversine import haversine
import time
import threading
import zipfile
import subprocess
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

#setting the constants
DEBUGPORT=8080  # Debug http server port
MAINREFRESH=1   # Refresh rate of proximity radars analysis in seconds
PROXYREFRESH=60 # Refresh rate of the proximity list of POI is seconds
ALERTREFRESH=2  # Refresh rate of alerting in seconds
DBFILE  = '/home/chip/tools-car/database.zip' # Renamed from rad_txt-iGO-EUR.zip'
POIFILE = 'SpeedCam.txt'
STARTMP3 = '/home/chip/tools-car/Start.mp3'
ENDMP3   = '/home/chip/tools-car/End.mp3'
LIGHTMP3 = '/home/chip/tools-car/Lightbell.mp3'
STRONGMP3= '/home/chip/tools-car/Strongbell.mp3'
WARNINGDISTANCEREF = 0.4 # Ref warning distance in km for low speed (under 60km/h)
WARNINGDISTANCEMULTIPLICATORMEDIUM = 2 # Multiplicator of warning distance for medium speed (under 90km/h)
WARNINGDISTANCEMULTIPLICATORHIGH   = 3 # Multiplicator of warning distance for high  speed (under 130km/h)
WARNINGDISTANCEMULTIPLICATOROVER   = 5 # Multiplicator of warning distance for over  speed (above 130km/h)
POSIMPRECISION = 0.05 # Imprecision in real precise position

#setting the global variables
currentDebugBody = ""
averageSpeedValue = 0
gpsd = None 
poi  = []
proxyPoi = []
proxyPoiInvalidate = False
PROXYDISTANCE=3*PROXYREFRESH/60 # Max distance covered at 180km/h between 2 refreshes
currentMode = 0 # 0 = no GPS, 1 = GPS, 2 = light warning, 3 = heavy warning, 4 = in limited section
htmlPageReady = False

class httpHandler(BaseHTTPRequestHandler):
	global htmlPageReady	
	HEAD="<head><META HTTP-EQUIV='refresh' CONTENT='"+str(MAINREFRESH)+"'><title>gpsData debug page</title></head>"

	def do_GET(self):
		global currentDebugBody
		self.send_response(200)
		self.send_header('Content-type','text/html')
		self.end_headers()
		# Send the html message
		if htmlPageReady:
			self.wfile.write("<html>"+self.HEAD+"<body>"+currentDebugBody+"</body></html>")
		return

	def log_message(self, format, *args):
        	return

class httpServer(threading.Thread):
  webServer=None
  
  def __init__(self):
    threading.Thread.__init__(self)
    self.current_value = None
    self.running = True #setting the thread running to true

  def kill(self):
	print 'Stop webserver'
	self.webServer.shutdown()	

  def run(self):
	#Create a web server and define the handler to manage the
	print 'Start webserver'
	#incoming request
	self.webServer = HTTPServer(('', DEBUGPORT), httpHandler)
	
	#Wait forever for incoming htto requests
	self.webServer.serve_forever()

class Alerting(threading.Thread):
  @staticmethod
  def play_mp3(path):
    FNULL = open(os.devnull, 'w')
    subprocess.Popen(['aplay', '-d', '1', '-r', '48000', '-f', 'S16_LE', '/dev/zero'], stderr=FNULL).wait()
    subprocess.Popen(['mpg123', '-q', path]).wait()

  @staticmethod
  def play_speach(message):
    FNULL = open(os.devnull, 'w')
    tmpFile = '/tmp/gpsData.wav'
    subprocess.Popen(['pico2wave', '-l', 'fr-FR', '-w', tmpFile, message]).wait()
    subprocess.Popen(['aplay', '-d', '1', '-r', '48000', '-f', 'S16_LE', '/dev/zero'], stderr=FNULL).wait()
    subprocess.Popen(['aplay', tmpFile], stderr=FNULL).wait()
    os.remove(tmpFile)

  def __init__(self):
    global poi
    threading.Thread.__init__(self)
    self.current_value = None
    self.play_mp3(STARTMP3)
    self.play_speach('Chargement de '+str(len(poi))+' radars')
    self.running = True #setting the thread running to true
 
  def run(self):
    global currentMode, averageSpeedValue
    while self.running:
	if currentMode == 2:
		self.play_mp3(LIGHTMP3)
		time.sleep(ALERTREFRESH)
	elif currentMode == 3:	
		self.play_mp3(STRONGMP3)
		time.sleep(ALERTREFRESH)
	elif currentMode == 4:
		play.speach('Vitesse moyenne '+str(averageSpeedValue))
		time.sleep(ALERTREFRESH*5)
	else:	
		time.sleep(ALERTREFRESH)
    self.play_mp3(ENDMP3) # Only reached when the thread is terminated

class GpsPoller(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    global gpsd #bring it in scope
    gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
    self.current_value = None
    self.running = True #setting the thread running to true
 
  def run(self):
    global gpsd
    while self.running:
      gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
 
class ProxyPOISelector(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self.running = True #setting the thread running to true
 
  def run(self):
    global gpsd, poi, proxyPoi, proxyPoiInvalidate, PROXYREFRESH, PROXYDISTANCE, currentMode
    while self.running:
		if not currentMode == 0:
			if len(poi) > 0:
				print 'Start proximity radar selection'
				localPos = (gpsd.fix.latitude, gpsd.fix.longitude)
				proxyPoi = []
				proxyPoiInvalidate=True
				for counter, radar in enumerate(poi):
					radarPos = (float(radar[1]), float(radar[0]))
					radarDis = haversine(localPos,radarPos)
					if radarDis <= PROXYDISTANCE:
						proxyPoi.insert(0,(radar[0], radar[1], radar[2], radar[3], radar[4], radar[5], radarDis))
				print 'End proximity radar selection'
				for i in range(PROXYREFRESH): # Used to wait but not blocking for Thread termination
					if self.running:
						time.sleep(1)
					else:
						break
			else:
				time.sleep(1)
		else:
			time.sleep(1)

if __name__ == '__main__':
  # Read radars list from archive
  zipFile = zipfile.ZipFile(DBFILE, 'r')
  with zipFile.open(POIFILE) as f:
      for line in f:
           radar = line.strip('\n').strip('\r').split(",")
	   # Format is X,Y,TYPE,SPEED,DIRTYPE,DIRECTION
	   if not radar[0]=='X': # discard header of file
	   	 poi.insert(0,(radar[0], radar[1], radar[2], radar[3], radar[4], radar[5]))
  # Create helper's threads
  gpsp = GpsPoller()
  poip = ProxyPOISelector()
  alert = Alerting()
  http = httpServer()
  # Start everything
  averageControlProxy = False
  averageMeasureNbr = 0
  try:
    gpsp.start()
    poip.start()
    alert.start()
    http.start()

    while True:
      htmlPageReady = False
      currentDebugBody=' GPS reading<br/>'
      currentDebugBody+='----------------------------------------<br/>'      
      currentDebugBody+='latitude     '+str(gpsd.fix.latitude)+'<br/>'
      currentDebugBody+='longitude    '+str(gpsd.fix.longitude)+'<br/>'
      currentDebugBody+='speed (km/h) '+str(gpsd.fix.speed*3.6)+'<br/>'
      currentDebugBody+='track        '+str(gpsd.fix.track)+'<br/>'
      currentDebugBody+='----------------------------------------<br/>'      
      currentDebugBody+='Records in DB: '+str(len(poi))+'<br/>'
      currentDebugBody+='Current mode : '+str(currentMode)+'<br/>'
      currentDebugBody+='----------------------------------------<br/>'      

      if not (gpsd.fix.latitude == 0 and gpsd.fix.longitude == 0):
	currentMode=1
        localPos = (gpsd.fix.latitude, gpsd.fix.longitude)
        # Set warning distance according to current speed
        if gpsd.fix.speed*3.6 <= 60:
		WARNINGDISTANCE=WARNINGDISTANCEREF
        elif gpsd.fix.speed*3.6 <= 90:
		WARNINGDISTANCE=WARNINGDISTANCEREF*WARNINGDISTANCEMULTIPLICATORMEDIUM
        elif gpsd.fix.speed*3.6 <= 130:
		WARNINGDISTANCE=WARNINGDISTANCEREF*WARNINGDISTANCEMULTIPLICATORHIGH
        else:
		WARNINGDISTANCE=WARNINGDISTANCEREF*WARNINGDISTANCEMULTIPLICATOROVER
        # Check proximity radars to know if we should warn
	updateStatus=0
        for counter, radar in enumerate(proxyPoi):
      	        currentDebugBody+='Proximity radar '+str(counter)+'<br/>'
		radarPos = (float(radar[1]), float(radar[0]))
		radarDis = haversine(localPos,radarPos)
		if radarDis <= radar[6] + POSIMPRECISION: # Getting closer from the radar
		   if radarDis <= WARNINGDISTANCE: # We are under warning distance
			if radar[2] == '1' or radar[2] == '4' or radar[2] == '69': # Warn only for RF, RS and RFR
				currentDebugBody+=str(radar)+'<br/>'
				lowlim = (float(radar[5])-45)%360
				hghlim = (float(radar[5])+45)%360
				if radar[4] == '0' or (radar[4] == '1' and gpsd.fix.track > lowlim and gpsd.fix.track < hghlim) or radar[4] == '2':
				   if not currentMode==4:
					if (not float(radar[3])==0) and (gpsd.fix.speed*3.6)>radar[3]:
						currentDebugBody+='- WARNING<br/>'
						currentMode=3
						updateStatus=1
					else:
						currentDebugBody+='- LIGHT WARNING<br/>'
						currentMode=2
						updateStatus=1
					if radarDis <= POSIMPRECISION:
						averageControlProxy = True
				   else:
					currentDebugBody+='- IN CONTROLLED SECTION<br/>'
					updateStatus=1
				else:
					currentDebugBody+='- Radar is not in the driving direction<br/>'
			else:
				currentDebugBody+='- Radar is not a RF, RS or RFR  one<br/>'
		   else:
			currentDebugBody+='- Radar is too far<br/>'
		else:
		   print '- Radar distance is increasing'
		   if (radar[2] == '4' and (currentMode==3 or currentMode==2) and averageControlProxy==True):
			currentMode=4
			updateStatus=1
		# Check if proxyPoi is valid
		if proxyPoiInvalidate:
			proxyPoiInvalidate=False
			break
		# update of radar distance
		proxyPoi[counter]=(radar[0], radar[1], radar[2], radar[3], radar[4], radar[5], radarDis)
	# update status
	if updateStatus==0 and currentMode>1:
		currentMode=1
		averageSpeedValue = 0
  		averageMeasureNbr = 0
		averageControlProxy = False
	# calculate average speed
	if currentMode == 4:
		averageMeasureNbr += 1
		averageSpeedValue = (averageSpeedValue*(averageMeasureNbr-1)+gpsd.fix.speed*3.6)/averageMeasureNbr
      else:
	currentMode=0
      htmlPageReady = True
      time.sleep(MAINREFRESH)
 
  except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    print "\nKilling Threads..."
    gpsp.running  = False
    poip.running  = False
    alert.running = False
    http.running  = False
    gpsp.join() # wait for the thread to finish what it's doing
    poip.join()
    alert.join()
    http.kill()
    time.sleep(1)
  print "Done.\nExiting."

