#!/usr/bin/python3
#
# This client connects to save_monitor_server.py running on the Satisfactory
# Dedicated Server which provides autosave information such as when the next
# save will start, how long it will take, and when it will complete.
#
# Change the server save interval in-game using the console:  FG.AutosaveInterval <seconds as decimal>
#
# Tested with Python 3.9.7 on Windows 10.
#

import argparse
import socket
import struct
import threading
import time
import winsound
from _thread import *
from datetime import datetime, timedelta

parser = argparse.ArgumentParser(description="Client for monitor Satisfactory save state.")
parser.add_argument('--address', help='Server IP address', type=str, required=True)
parser.add_argument('--port', help='Server TCP port', type=int, default=15001)
args = parser.parse_args()

globalStatus_mutex = threading.Lock()
globalStatus_increment = 0
globalStatus_savingFlag = False
globalStatus_predictedNextSaveStartTime = None
globalStatus_predictedSaveEndTime = None
globalStatus_autosaveInterval = 300.0  # (seconds) Default to 5 minutes
globalStatus_lastSaveTimeLength = 0

def statusDisplayThread():

	global globalStatus_mutex
	global globalStatus_increment
	global globalStatus_savingFlag
	global globalStatus_predictedNextSaveStartTime
	global globalStatus_predictedSaveEndTime
	global globalStatus_autosaveInterval
	global globalStatus_lastSaveTimeLength

	lastStatusDisplayed = 0
	while True:
		globalStatus_mutex.acquire()
		nowDatetime = datetime.now()
		if globalStatus_savingFlag and globalStatus_predictedSaveEndTime < nowDatetime:
			# This either happens if the connection to the server was lost or
			# the sever has no active users and is configured only to run with active users.
			pass
		elif lastStatusDisplayed != globalStatus_increment:
			if globalStatus_savingFlag:
				print(f"Server is in the process of saving.  Expected to complete at {globalStatus_predictedSaveEndTime} based on last save that took {globalStatus_lastSaveTimeLength} seconds.  Next save expected to start at {globalStatus_predictedNextSaveStartTime} (local time) based on {globalStatus_autosaveInterval} second interval.")
			else:
				print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
				print(f"Server save completed.  Save took {globalStatus_lastSaveTimeLength} seconds.  Next save expected to start at {globalStatus_predictedNextSaveStartTime} (local time) based on {globalStatus_autosaveInterval} second interval and end at {globalStatus_predictedSaveEndTime}.\n")
			lastStatusDisplayed = globalStatus_increment
		elif lastStatusDisplayed > 0:
			if not globalStatus_savingFlag and nowDatetime >= globalStatus_predictedNextSaveStartTime:
				winsound.Beep(2500, 200)
				globalStatus_savingFlag = True
				globalStatus_predictedSaveEndTime = globalStatus_predictedNextSaveStartTime + timedelta(seconds=globalStatus_lastSaveTimeLength)
				globalStatus_predictedNextSaveStartTime += timedelta(seconds=(globalStatus_autosaveInterval + globalStatus_lastSaveTimeLength))
				print("##############################################################################")
				print(" .oooooo..o       .o.       oooooo     oooo ooooo ooooo      ooo   .oooooo.   ")
				print("d8P'    `Y8      .888.       `888.     .8'  `888' `888b.     `8'  d8P'  `Y8b  ")
				print("Y88bo.          .8\"888.       `888.   .8'    888   8 `88b.    8  888          ")
				print(" `\"Y8888o.     .8' `888.       `888. .8'     888   8   `88b.  8  888          ")
				print("     `\"Y88b   .88ooo8888.       `888.8'      888   8     `88b.8  888     ooooo")
				print("oo     .d8P  .8'     `888.       `888'       888   8       `888  `88.    .88' ")
				print("8\"\"88888P'  o88o     o8888o       `8'       o888o o8o        `8   `Y8bood8P'  ")
				print("##############################################################################")

			if globalStatus_savingFlag:
				timeToCompleteSave = globalStatus_predictedSaveEndTime - nowDatetime
				print(f"timeToCompleteSave={timeToCompleteSave}")
			else:
				timeToNextSave = globalStatus_predictedNextSaveStartTime - nowDatetime
				print(f"Countdown until save: {timeToNextSave}")

		globalStatus_mutex.release()
		time.sleep(1)

if __name__ == "__main__":

	start_new_thread(statusDisplayThread, ())

	print("Use Ctrl-Pause/Break to exit.")
	reconnectFlag = True
	sock = None
	while reconnectFlag:
		if not sock:
			print("Creating sock")
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			print("Attempting to connect...")
			sock.connect((args.address, args.port))
		except OSError:
			print("[OSError] Waiting for server...")
			time.sleep(1)
			continue
		except ConnectionRefusedError:
			print("[ConnectionRefusedError] Waiting for server...")
			time.sleep(10)
			continue

		print("Connected.  Monitoring for status...")
		while True:
			try:
				statusData = sock.recv(1+4+4+4+4)
			except KeyboardInterrupt:
				print("Cancelled by user")
				reconnectFlag = False
				break

			if not statusData:
				print("Lost connection to the server")
				break  # Remote socket probably broke. Close and reconnect.

			globalStatus_mutex.acquire()
			globalStatus_increment += 1
			globalStatus_savingFlag = struct.unpack("<?", statusData[0:1])[0]
			predictedNextSaveTimeInMs = struct.unpack("<I", statusData[1:5])[0]
			predictedSaveEndTimeInMs = struct.unpack("<I", statusData[5:9])[0]
			globalStatus_autosaveInterval = struct.unpack("<f", statusData[9:13])[0]
			globalStatus_lastSaveTimeLength = struct.unpack("<f", statusData[13:17])[0]
			globalStatus_predictedNextSaveStartTime = datetime.fromtimestamp(predictedNextSaveTimeInMs)
			globalStatus_predictedSaveEndTime = datetime.fromtimestamp(predictedSaveEndTimeInMs)
			globalStatus_mutex.release()

		print("Closing")
		sock.close()
		sock = None

	print("Exiting")
