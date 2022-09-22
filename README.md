# Satisfactory Save Monitor
A tool to notify Satisfactory players when a save is going to occur on the server, providing a countdown until the next save, and a countdown until the save completes.

These scripts were written because players need to be cautious during saves when playing on Satisfactory servers remotely.  The game does not prevent remote players from performing actions which may get them in trouble (e.g. dead) when the save completes.  I have reported this issue to Coffee Stain Studios as [ticket 63056942ca608e080351c6b6](https://questions.satisfactorygame.com/post/63056942ca608e080351c6b6).

This is performed with a pair of Python scripts, one running on the dedicated server and a client running on the player's machine.

## Server
Tested with Python 3.10.4 on Ubuntu 22.04.1 LTS.

Usage: **./save_monitor_server.py [-h] --fgpath FGPATH [--port PORT]**

Example: **./save_monitor_server.py --fgpath /home/steam/SatisfactoryDedicatedServer/FactoryGame --port 15001**

You may need to poke a hole through your firewall for the port (default 15001).
The server is 100% unidirectional (with the exception of the standard TCP protocol exchange).  The server excepts no data from the client.

### Running the server as a daemon
Tested with systemd 249 (249.11-0ubuntu3.4).

To install and start the server as a daemon:
- Update save_monitor_server.service with the full path to save_monitor_server.py
- Copy save_monitor_server.service into /etc/systemd/system/
- sudo systemctl daemon-reload
- sudo systemctl enable save_monitor_server
- sudo systemctl start save_monitor_server

To see the status:  sudo systemctl status save_monitor_server

## Client
Tested with Python 3.9.7 on Windows 10.

Usage: **python save_monitor_client.py [-h] --address ADDRESS [--port PORT]**

Example: **python save_monitor_client.py --address 1.2.3.4 --port 15001**

The client will display a countdown until the save.
When the save starts, the client will make a short peep noise and print SAVING.  Then the client will countdown until the save is completed.

Terminate the client with Ctrl+Break.

![Client Screenshot](https://raw.githubusercontent.com/GreyHak/satisfactory_save_monitor/master/client_screenshot.jpg)

# Acknowledgement

My thanks to Bigkahuna (Bigkahuna666#0861 on discord) for allowing me to test this save_monitor_server on his server!
