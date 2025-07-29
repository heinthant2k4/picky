from pydobot import Dobot as bot
import time
device = bot('/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0')
#device = bot('/dev/ttyUSB0')
print("Connecting to Dobot...")
# device.home()
((x, y, z, r),(j1, j2, j3, j4)) = device.get_pose()
print(f"Current position: x={x}, y={y}, z={z}, r={r}")

while True:
    ((x, y, z, r),(j1, j2, j3, j4)) = device.get_pose()
    print(f"Current position: x={x}, y={y}, z={z}, r={r}")
    if(z <= -46):
        device.suck(True)
        time.sleep(5)
        device.suck(False)
        time.sleep(5)