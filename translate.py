#Import Library
from pydobot import Dobot

#Intialize
device = Dobot('/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0')
print("Connecting to Dobot...")

#variable
margin = 0.25

#Functions
def go_to_block(cordx, cordy, cordz):
        device.move_to(x = home[0] + (cordx * gap[0]), y = home[1] + (cordy * gap[1]), z = home[2] + (cordz * gap[2]), r = 0)

def stack_from_block(cordx, cordy, margin, cycle):
                # Common initial moves
                z_margin = home[2] + ((cycle + margin) * gap[2])
                x_pos = home[0] + (cordx * gap[0])
                y_pos = home[1] + (cordy * gap[1])
                device.move_to(x=home[0], y=home[1], z=z_margin, r=0)  # Move up a margin at 0 0
                device.move_to(x=x_pos, y=y_pos, z=z_margin, r=0)  # move to x y with margin
                device.move_to(x=x_pos, y=y_pos, z=home[2] + (1 * gap[2]), r=0)  # move down to block
                device.suck(True)  # enable suction
                # Move back up, with extra height if cycle == 1
                if cycle == 1:
                        z_lift = home[2] + ((cycle + margin + 1) * gap[2])
                        device.move_to(x=x_pos, y=y_pos, z=z_lift, r=0)  # move back to x y with margin and z +1
                        device.move_to(x=home[0], y=home[1], z=z_lift, r=0)  # Move to 0 0 with z +1 and margin
                else:
                        device.move_to(x=x_pos, y=y_pos, z=z_margin, r=0)  # move back to x y with margin
                        device.move_to(x=home[0], y=home[1], z=z_margin, r=0)  # Move to 0 0 with margin
                device.move_to(x=home[0], y=home[1], z=home[2] + (cycle * gap[2]), r=0)  # Move down
                device.suck(False)  # disable suction

        
#Homing

# device.home()


input("Home?")
((x, y, z, r),(j1, j2, j3, j4)) = device.get_pose()
home = [x, y ,z]
print(home)

input("Calibrate at block 1 1 1?")
((x, y, z, r),(j1, j2, j3, j4)) = device.get_pose()
gap = [x - home[0], y - home[1], z - home[2]]
print(gap)

print("Done Calibration, moving back")
go_to_block(1, 1, 1+margin)
go_to_block(0, 0, 1+margin)
go_to_block(0, 0, 1)

input("stack up block 1 1 1?")
stack_from_block(1, 1, margin, 1)
stack_from_block(1, -1, margin, 2)
stack_from_block(-1, 1, margin, 3)
stack_from_block(-1, -1, margin, 4)
go_to_block(0, 0, 5)
