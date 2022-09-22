#!/usr/bin/python3
#
# This script monitors the FactoryGame.log to detect and predict when
# autosaves will start and complete.  This information is servered to
# save_monitor_client.py to provide the information directly to the user.
#
# Please open TCP port 15001 for this server to function.
#
# Tested with Python 3.10.4 on Ubuntu 22.04.1 LTS.
# Also tested with systemd 249 (249.11-0ubuntu3.4).
#

import argparse
import socket
import threading
import time
import struct
from _thread import *
from datetime import datetime, timedelta, timezone

parser = argparse.ArgumentParser(description="Server for monitor Satisfactory save state.")
parser.add_argument('--fgpath', help='Path of FactoryGame folder', type=str, required=True)
parser.add_argument('--port', help='Server TCP port', type=int, default=15001)
args = parser.parse_args()

logFilename = args.fgpath + "/Saved/Logs/FactoryGame.log"
usrFilename = args.fgpath + "/Saved/Config/LinuxServer/GameUserSettings.ini"

globalStatus_mutex = threading.Lock()
globalStatus_increment = 0
globalStatus_savingFlag = False
globalStatus_predictedNextSaveStartTime = None
globalStatus_predictedSaveEndTime = None
globalStatus_autosaveInterval = 300.0  # (seconds) Default to 5 minutes
globalStatus_lastSaveTimeLength = 0

def statusMonitorThread():
	global globalStatus_mutex
	global globalStatus_increment
	global globalStatus_savingFlag
	global globalStatus_predictedNextSaveStartTime
	global globalStatus_predictedSaveEndTime
	global globalStatus_autosaveInterval
	global globalStatus_lastSaveTimeLength

	try:
		usrFile = open(usrFilename, "r")
		if usrFile:  # If the file can't be opened, fall base on the game default
			while True:
				line = usrFile.readline()
				if not line:
					break;
				if line.startswith('mFloatValues=(("FG.AutosaveInterval", ', 0):
					globalStatus_mutex.acquire()
					globalStatus_autosaveInterval = float(line[38:len(line)-3])
					print(f"Loaded user setting for autosave interval, {globalStatus_autosaveInterval} seconds")
					globalStatus_mutex.release()
			usrFile.close()
	except FileNotFoundError:
		pass

	logFile = open(logFilename, "r")
	if not logFile:
		print("Failed to open log file")
	else:
		while True:
			line = logFile.readline()
			if not line:
				time.sleep(1)
				continue
			isLogin = line.startswith("LogNet: Join succeeded: ", 30)
			isAutosaveReconfig = line.startswith('LogServerConnection: FG.AutosaveInterval = "', 30)
			isSave1 = line.startswith("LogGame: World Serialization (save): ", 30)
			isSave2 = line.startswith("LogGame: Compression: ", 30)
			isSave3 = line.startswith("LogGame: Write To Disk: ", 30)
			isSave4 = line.startswith("LogGame: Write Backup to Disk and Cleanup time: ", 30)
			isSaveDone = line.startswith("LogGame: Total Save Time took ", 30)
			if isLogin or isAutosaveReconfig or isSave1 or isSaveDone:
				year = int(line[1:5])
				month = int(line[6:8])
				day = int(line[9:11])
				hour = int(line[12:14])
				minutes = int(line[15:17])
				seconds = int(line[18:20])
				milliseconds = int(line[21:24])
				timestamp = datetime(year, month, day, hour, minutes, seconds, milliseconds * 1000, timezone.utc)
				if isLogin:
					print(timestamp, "Login")
					if globalStatus_predictedNextSaveStartTime:
						globalStatus_mutex.acquire()
						if globalStatus_predictedSaveEndTime < datetime.now(timezone.utc):
							globalStatus_increment += 1
							globalStatus_savingFlag = False
							globalStatus_predictedNextSaveStartTime = timestamp + timedelta(seconds=globalStatus_autosaveInterval)
							globalStatus_predictedSaveEndTime = globalStatus_predictedNextSaveStartTime + timedelta(seconds=totalSaveTimeThisTime)
							print(f"Predicted next save in past.  Save to end at {globalStatus_predictedSaveEndTime} with next save at {globalStatus_predictedNextSaveStartTime}\n")
						globalStatus_mutex.release()
				elif isAutosaveReconfig:
					print(f"DEBUG: {line}")
					print(f"DEBUG: {line[104:len(line)-2]}")
					globalStatus_mutex.acquire()
					globalStatus_autosaveInterval = float(line[104:len(line)-2])
					print(timestamp, f"Operator changed autosave interval to {globalStatus_autosaveInterval} seconds")
					globalStatus_mutex.release()
				elif isSave1:
					saveTimeSoFar = float(line[67:len(line)-9])
					print(timestamp, f"Save detected. Saving for {saveTimeSoFar} seconds so far.")
					globalStatus_mutex.acquire()
					globalStatus_increment += 1
					globalStatus_savingFlag = True
					calculatedStartTime = timestamp - timedelta(seconds=saveTimeSoFar)
					#print(f"Calculated start time {calculatedStartTime}")
					globalStatus_predictedSaveEndTime = calculatedStartTime + timedelta(seconds=globalStatus_lastSaveTimeLength)
					globalStatus_predictedNextSaveStartTime = globalStatus_predictedSaveEndTime + timedelta(seconds=globalStatus_autosaveInterval)
					print(f"Save to end at {globalStatus_predictedSaveEndTime} with next save at {globalStatus_predictedNextSaveStartTime}")
					globalStatus_mutex.release()
				elif isSaveDone:
					totalSaveTimeThisTime = float(line[60:len(line)-9])
					print(timestamp, f"Save completed after {totalSaveTimeThisTime} seconds.")
					globalStatus_mutex.acquire()
					globalStatus_increment += 1
					globalStatus_savingFlag = False
					#print(f"Calculated start time {timestamp - timedelta(seconds=totalSaveTimeThisTime)}")
					globalStatus_predictedNextSaveStartTime = timestamp + timedelta(seconds=globalStatus_autosaveInterval)
					globalStatus_predictedSaveEndTime = globalStatus_predictedNextSaveStartTime + timedelta(seconds=totalSaveTimeThisTime)
					globalStatus_lastSaveTimeLength = totalSaveTimeThisTime
					print(f"Next save from {globalStatus_predictedNextSaveStartTime} to {globalStatus_predictedSaveEndTime}\n")
					globalStatus_mutex.release()

def statusTxThread(localSocket, clientAddress):
	global globalStatus_mutex
	global globalStatus_increment
	global globalStatus_savingFlag
	global globalStatus_predictedNextSaveStartTime
	global globalStatus_predictedSaveEndTime
	global globalStatus_autosaveInterval
	global globalStatus_lastSaveTimeLength

	localSocket.settimeout(1)
	lastStatusSent = 0
	while True:
		globalStatus_mutex.acquire()
		localStatus_increment = globalStatus_increment
		localStatus_savingFlag = globalStatus_savingFlag
		localStatus_predictedNextSaveStartTime = globalStatus_predictedNextSaveStartTime
		localStatus_predictedSaveEndTime = globalStatus_predictedSaveEndTime
		localStatus_autosaveInterval = globalStatus_autosaveInterval
		localStatus_lastSaveTimeLength = globalStatus_lastSaveTimeLength
		globalStatus_mutex.release()
		if lastStatusSent == localStatus_increment:
			try:
				ignore = localSocket.recv(1)  # Both sleeps and checks for dead connections
			except socket.timeout:
				continue
			except ConnectionResetError:
				break

		predictedNextSaveStartTimeInMs = int(localStatus_predictedNextSaveStartTime.timestamp())
		predictedSaveEndTimeInMs = int(localStatus_predictedSaveEndTime.timestamp())
		statusData = struct.pack("<?", localStatus_savingFlag)
		statusData += struct.pack("<I", predictedNextSaveStartTimeInMs)
		statusData += struct.pack("<I", predictedSaveEndTimeInMs)
		statusData += struct.pack("<f", localStatus_autosaveInterval)
		statusData += struct.pack("<f", localStatus_lastSaveTimeLength)
		localSocket.send(statusData)
		lastStatusSent = localStatus_increment
		print("Sent status")
	localSocket.close()
	print(f"Client {clientAddress} disconnected")

if __name__ == "__main__":

	start_new_thread(statusMonitorThread, ())

	mainSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	mainSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	mainSocket.bind(("", args.port))
	mainSocket.listen(5)

	try:
		while True:
			try:
				newSocket, addressPort = mainSocket.accept()
			except KeyboardInterrupt:
				print("")
				break
			print(f"Client connected from {addressPort[0]}:{addressPort[1]}")
			start_new_thread(statusTxThread, (newSocket, addressPort[0]))
	finally:
		mainSocket.close()
