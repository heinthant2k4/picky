import serial

PORT = "COM9"

with serial.Serial(PORT, baudrate=115200, timeout=1) as port:
    print(f"Opened {port.name}")
    print("Serial port is available.")
