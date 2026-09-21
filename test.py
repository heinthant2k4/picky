from pydobot import Dobot

PORT = "COM9"

print(f"Connecting to Dobot at {PORT}...")
device = Dobot(PORT)

try:
    pose, joints = device.get_pose()
    print("Connected successfully.")
    print("Pose:", pose)
    print("Joints:", joints)
finally:
    device.close()
    print("Disconnected.")
