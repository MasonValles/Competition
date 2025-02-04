#!/usr/bin/env python3

import socket
import tkinter as tk
import json
import time
import requests
import threading
import math
from pymavlink import mavutil
from openAthena import *

mavDevice = mavutil.mavlink_connection('udp:COM6:9600')

# generate Lat/Long Frame


def co_ord_frame(parent, row, col, target_label=False):

    # holds latitude and longitude frames
    grid_frame = tk.Frame(parent, bg="#0f0e13")
    grid_frame.grid(row=row, column=col)

    # Latitude Frame
    lat_frame = tk.Frame(grid_frame, bg="#52607e")
    lat_frame.grid(
        row=0,
        column=0,
        padx=(10, 10),
        pady=(10, 5),
    )
    lat_gap_frame = tk.Frame(lat_frame, bg="#52607e")
    lat_gap_frame.pack(fill="both", padx=20, pady=20)
    latitude = tk.Label(lat_gap_frame,
                        text="LATITUDE",
                        bg="#52607e",
                        fg="#e3e4e2",
                        width=31,
                        anchor="w")
    lat_label = tk.Label(
        lat_gap_frame,
        text="Calculating",
        bg="#52607e",
        fg="#e3e4e2",
        font=("Arial", 50),
        anchor="w",
        width=10,
    )

    # Longitude Frame
    long_frame = tk.Frame(grid_frame, bg="#1e1e20")
    long_frame.grid(
        row=1,
        column=0,
        padx=(10, 10),
        pady=(5, 10),
    )
    long_gap_frame = tk.Frame(long_frame, bg="#1e1e20")
    long_gap_frame.pack(fill="both", padx=20, pady=20)
    longitude = tk.Label(long_gap_frame,
                         text="LONGITUDE",
                         bg="#1e1e20",
                         fg="#e3e4e2",
                         width=31,
                         anchor="w")
    long_label = tk.Label(
        long_gap_frame,
        text="Calculating",
        bg="#1e1e20",
        fg="#e3e4e2",
        font=("Arial", 50),
        anchor="w",
        width=10,
    )

    latitude.grid(row=0, column=0, pady=(0, 20))
    lat_label.grid(row=1, column=0, padx=0)
    longitude.grid(row=0, column=0, pady=(0, 20))
    long_label.grid(row=1, column=0, padx=0)

    # Update Label
    if target_label:
        target_thread = threading.Thread(target=target_endpoint,
                                         args=(lat_label, long_label, target_label))
        target_thread.start()
    else:
        primary_thread = threading.Thread(target=primary_on_time,
                                          args=(lat_label, long_label))
        primary_thread.start()


# Update Primary Lat/Long every second
def primary_on_time(lat_label, long_label):
    while True:
        primaryEndpoint(lat_label, long_label)


# Primary Status
def primaryEndpoint(lat, long):

    # send request
    request = {"method": "GET", "endpoint": "primary_status", "parameters": {}}
    request_dump_string = json.dumps(request)
    s.sendall(request_dump_string.encode('utf-8'))

    # receive response
    response_dump_string = s.recv(1024).decode('utf-8')
    response = json.loads(response_dump_string)

    # update label with lat and long on success
    if response["status"] == 200:
        lat.config(text=response["data"]["latitude"])
        long.config(text=response["data"]["longitude"])


# Target Status
def target_endpoint(lat, long, target_label):

    # receive response
    while True:
        response_dump_string = s.recv(1024).decode('utf-8')
        response = json.loads(response_dump_string)
        print(response)
        if response["message"] == "target_color":
            break

    # Response(target_color endpoint) received successfully
    if response["status"] == 200:
        target_label.config(text="TARGET: FOUND")
        entry.delete("0", tk.END)  # Clear existing text

        # sends request for parameters
        param_dump = requests.get("http://localhost:56781/mavlink/")
        parameters = json.loads(param_dump)
        altitude, rollAngle, theta, azimuth = parameters["VFR_HUD"]["msg"]["alt"], parameters["ATTITUDE"][
            "msg"]["roll"], parameters["ATTITUDE"]["msg"]["pitch"], parameters["VFR_HUD"]["msg"]["heading"]

        mavDevice.mav.param_request_list_send(
            mavDevice.target_system, mavDevice.target_component)

        # pulls altitude from mavlink
        mavAlt = mavDevice.recv_match(type='ALT', blocking=True)
        altitude = mavAlt.decode()

        mavRoll = mavDevice.recv_match(type='RLL', blocking=True)
        rollAngle = mavRoll.decode()

        mavPitch = mavDevice.recv_match(type='PTCH', blocking=True)
        theta = mavPitch.decode()

        mavComp = mavDevice.recv_match(type='COMPASS', blocking=True)
        azimuth = mavComp.decode()
        # dummy code
        """
        altitude = 416
        azimuth = 172
        rollAngle = 0
        theta = -36
        """

        # print(altitude + ' ' + rollAngle + ' ' + theta + ' ' + azimuth)

        latitude, longitude, targetX, targetY = response["data"]["latitude"], response[
            "data"]["longitude"], response["data"]["target_X"], response["data"]["target_Y"]
        azimuth = math.Float(azimuth) + 90
        setCamera(21, 1280, 1024, 0, 0, 0, 0, 0, 1, "cobb.tif")
        # OpenAthena stuff(use response payload to compute below)
        tarLat, tarLong, alt, terAlt = calcCoord(
            latitude, longitude, altitude, azimuth, theta, targetX, targetY, rollAngle)
        target_latitude = tarLat
        target_longitude = tarLong

        # send target coordinates back to pi
        # post_target_coords = {
        # "method": "POST",
        # "endpoint": "target_found",
        # "payload": {
        # "target_lat": target_latitude,
        # "target_lon": target_longitude
        # }
        # }
        # target_coords_dump_string = json.dumps(post_target_coords)
        # s.sendall(target_coords_dump_string.encode('utf-8'))

        # update label
        lat.config(text=target_latitude)
        long.config(text=target_longitude)


# Entry On-click Event Handler (Send color to pi)
def send_target_color(event=None):

    # send target color
    entry_text = entry.get()
    data = {"method": "POST", "endpoint": "target_color",
            "payload": {"color": entry_text}}
    json_data = json.dumps(data)
    s.sendall(json_data.encode('utf-8'))

    # update and destroy button widget
    entry.delete("0", tk.END)  # Clear existing text
    entry.insert("0", "Finding target...")
    button.destroy()

    # second co-ord generation on success
    target_main_frame = tk.Frame(additional_frame)
    target_main_frame.grid(row=0, column=1, padx=(30, 0), sticky="n")

    target_label = tk.Label(target_main_frame,
                            text="TARGET: NOT FOUND",
                            fg="#e3e4e2",
                            bg="#000000",
                            font="Arial, 25")
    target_label.grid(row=0, column=0, pady=(0, 7))

    co_ord_frame(target_main_frame, 1, 0, target_label=target_label)


# Boring stuff
def on_entry_focus_in(event=None):
    if entry.get() == "Enter Target Color...":
        entry.delete(0, tk.END)
        entry.config(fg="#e3e4e2")


def on_entry_focus_out(event=None):
    if entry.get() == "":
        entry.config(fg="grey")
        entry.insert(0, "Enter Target Color...")


# Execution Starts here:

HOST = "10.0.0.5"  # The server's hostname or IP address
PORT = 65438  # The port used by the server

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

    root = tk.Tk()
    root.title("GCS Interface")

    additional_frame = tk.Frame(root)
    additional_frame.pack(expand=True)

    # Center Frame
    main_frame = tk.Frame(additional_frame, bg="#000000")
    main_frame.grid(row=0, column=0, padx=(0, 30))

    # Generate Co-ordinate UI

    co_ord_frame(main_frame, 1, 0)

    # Set Color Input Frame
    color_frame = tk.Frame(main_frame)
    color_frame.grid(row=2, column=0, pady=(20, 0))

    entry = tk.Entry(color_frame, fg="grey", font=("Arial", 17))
    entry.insert(0, "Enter Target Color...")
    entry.bind("<FocusIn>", on_entry_focus_in)
    entry.bind("<FocusOut>", on_entry_focus_out)
    entry.bind("<Return>", send_target_color)

    button = tk.Button(color_frame,
                       text="Set",
                       command=send_target_color,
                       padx=0,
                       font=("Arial", 17))
    button.bind("<Return>", send_target_color)

    # Title Label
    primary_label = tk.Label(
        main_frame,
        text="PRIMARY",
        fg="#e3e4e2",
        font="Arial, 25",
    )
    primary_label.configure(bg="#000000")

    # Widget Positioning
    entry.grid(row=0, column=0)
    button.grid(row=0, column=1)
    primary_label.grid(row=0, column=0, pady=(0, 7))

    root.mainloop()
