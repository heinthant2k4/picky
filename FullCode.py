#---------------------------------------------------------------------------------------------

#ColorFromGrid_________________________

def ComputeSquareCoords(CenterX, CenterY, Half, Border):
    SquareCoords = []
    Offsets = [-(2 * Half + Border), 0, (2 * Half + Border)]
    for RowOff in Offsets:
        for ColOff in Offsets:
            TopLeft = (int(CenterX + ColOff - Half - (Border // 2)),
                       int(CenterY + RowOff - Half - (Border // 2)))
            BottomRight = (int(CenterX + ColOff + Half + (Border // 2)),
                           int(CenterY + RowOff + Half + (Border // 2)))
            SquareCoords.append((TopLeft, BottomRight))
    return SquareCoords

def ClassifyColor(Hsv):
    H, S, V = float(Hsv[0]), float(Hsv[1]), float(Hsv[2])
    if V < 50 or S < 40:
        return 'N'
    if (0 <= H <= 10) or (160 <= H <= 179):
        return 'R'
    elif 20 <= H <= 35:
        return 'Y'
    elif 36 <= H <= 85:
        return 'G'
    elif 86 <= H <= 125:
        return 'B'
    else:
        return '?'

def SamplePatchAvgHsv(Frame, Cx, Cy, Radius=6):
    HFrame, WFrame = Frame.shape[:2]
    X1 = max(0, Cx - Radius)
    X2 = min(WFrame, Cx + Radius + 1)
    Y1 = max(0, Cy - Radius)
    Y2 = min(HFrame, Cy + Radius + 1)

    if X1 >= X2 or Y1 >= Y2:
        Px = Frame[Cy, Cx]
        HsvPx = cv.cvtColor(np.uint8([[Px]]), cv.COLOR_BGR2HSV)[0, 0]
        return HsvPx.astype(float)

    Roi = Frame[Y1:Y2, X1:X2]
    if Roi.size == 0:
        Px = Frame[Cy, Cx]
        HsvPx = cv.cvtColor(np.uint8([[Px]]), cv.COLOR_BGR2HSV)[0, 0]
        return HsvPx.astype(float)

    HsvRoi = cv.cvtColor(Roi, cv.COLOR_BGR2HSV)
    Avg = HsvRoi.mean(axis=(0, 1))
    return Avg

#ColorFromGrid_________________________



#---------------------------------------------------------------------------------------------

##############################################################################################

import cv2 as cv
import numpy as np
from pydobot import Dobot
import os
import json

# import times

print(f"\nStarting the program...")

##############################################################################################

#ColorFromGrid________________________________________________________________________________---------

print(f"\nColor grid input:")
print("Attempting to connect to the camera...")

CameraIndex = 2
Video = cv.VideoCapture(CameraIndex)
if not Video.isOpened():
    print(f"Cannot open camera index {CameraIndex}. Try another index (0/1/2...).")
    exit()

Half = 55
Border = 26
DisplayBorderThickness = 26
SampleRadius = 6

print(f"Connected to camera. \nPress 'q' after aligning the 3x3 grid with your own.")

while True:
    Ret, Frame = Video.read()
    if not Ret:
        print("Err: Cannot read from camera.")
        exit()

    Height, Width = Frame.shape[:2]
    CenterX, CenterY = Width // 2, Height // 2

    SquareCoords = ComputeSquareCoords(CenterX, CenterY, Half, Border)

    GridColor = np.full((3, 3), '?', dtype='U1')
    for I, (TopLeft, BottomRight) in enumerate(SquareCoords):
        Cx = (TopLeft[0] + BottomRight[0]) // 2
        Cy = (TopLeft[1] + BottomRight[1]) // 2
        Cx = np.clip(Cx, 0, Width - 1)
        Cy = np.clip(Cy, 0, Height - 1)

        AvgHsv = SamplePatchAvgHsv(Frame, Cx, Cy, Radius=SampleRadius)
        ColorLetter = ClassifyColor(AvgHsv)

        Row = I // 3
        Col = I % 3
        GridColor[Row, Col] = ColorLetter

    OverlayColor = (0, 0, 225)
    for I, (TopLeft, BottomRight) in enumerate(SquareCoords):
        cv.rectangle(Frame, TopLeft, BottomRight, OverlayColor, DisplayBorderThickness)
        Cx = (TopLeft[0] + BottomRight[0]) // 2
        Cy = (TopLeft[1] + BottomRight[1]) // 2
        cv.circle(Frame, (Cx, Cy), 4, (255, 255, 255), -1)

        Row = I // 3
        Col = I % 3
        Letter = GridColor[Row, Col]
        cv.putText(Frame, Letter, (Cx - 8, Cy + 18),
                    cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv.LINE_AA)

    cv.imshow("CameraOverlay", Frame)

    Key = cv.waitKey(1) & 0xFF
    if Key == ord('q'):
        break

Video.release()
cv.destroyAllWindows()

#Dobot________________________________________________________________________________

#Intialize
device = Dobot('/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0')
print("Connecting to Dobot...")

#variable
margin = 0.5

#Functions
def go_to_block(cordx, cordy, cordz):
        device.move_to(x = home[0] + (cordx * gap[0]), y = home[1] + (cordy * gap[1]), z = home[2] + (cordz * gap[2]), r = 0)

def stack_from_block(cordx, cordy, margin, cycle):
                # Common initial moves
                z_margin = home[2] + ((cycle + margin) * gap[2])
                x_pos = home[0] + (cordx * gap[0])
                y_pos = home[1] + (cordy * gap[1])
                if cycle == 1:
                        device.move_to(x=home[0], y=home[1], z=z_margin, r=0)  # Move up a margin at 0 0
                        device.move_to(x=x_pos, y=y_pos, z=z_margin, r=0)  # move to x y with margin
                else:
                        device.move_to(x=home[0], y=home[1], z=home[2] + ((cycle -1 + margin) * gap[2]), r=0)  # Move up a margin at 0 0
                        device.move_to(x=x_pos, y=y_pos, z=home[2] + ((cycle -1 + margin) * gap[2]), r=0)  # move to x y with margin        
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

# Calibration persistence via JSON
calibration_file = "calibration.json"
if os.path.exists(calibration_file):
        with open(calibration_file, "r") as f:
                calibration = json.load(f)
        home = calibration["home"]
        gap = calibration["gap"]
        print("Loaded calibration:", home, gap)
else:
        input("Home?")
        ((x, y, z, r),(j1, j2, j3, j4)) = device.get_pose()
        home = [x, y ,z]
        print(home)

        input("Calibrate at block 1 1 1?")
        ((x, y, z, r),(j1, j2, j3, j4)) = device.get_pose()
        gap = [x - home[0], y - home[1], z - home[2]]
        print(gap)
        calibration = {"home": home, "gap": gap}
        with open(calibration_file, "w") as f:
                json.dump(calibration, f)
        print("Calibration saved.")

print("Done Calibration, moving back")
go_to_block(1, 1, 1+margin)
go_to_block(0, 0, 1+margin)


#Mix________________________________________________________________________________

print(f"\nCreating a tower from block around the center [R,G,B,Y]")
print("Getting information from the base to the top:")
ValidColor = [None] * 4
ColourInitial = ['R', 'G', 'B', 'Y']
ColourLocation = np.full((3, 3), '0', dtype='int')
i=0
while i<4:
    ValidColor[i] = input("Enter color[" + str(i+1) + "]: ")
    ValidColor[i] = ValidColor[i].upper()
    if ValidColor[i] not in ColourInitial:
        print("Invalid, please re-enter")
    else:
        i = i+1

GridColor[1][1] = '-' #Center    
print(GridColor)

CoordMap = {
    (0,0): (1,-1),
    (0,1): (1,0),
    (0,2): (1,1),
    (1,0): (0,-1),
    (1,1): (0,0),
    (1,2): (0,1),
    (2,0): (-1,-1),
    (2,1): (-1,0),
    (2,2): (-1,1)
}

temp = 0


for k in range(4):
    moved = False
    for i in range(3):
        for j in range(3):
            # skip the special 4th color if it is at (0,1)
            if ValidColor[2] == ValidColor[3] and i == 0 and j == 1 and GridColor[i][j] == ValidColor[3]:
                temp=1
            elif GridColor[0][1] == ValidColor[3] and i == 0 and j == 1 and GridColor[i][j] == ValidColor[3]:
                continue
            if GridColor[i][j] == ValidColor[k]:
                x, y = CoordMap[(i,j)]  # convert to Dobot coordinates
                stack_from_block(x, y, margin, k+1)
                print(f" Dobot move command for color {ValidColor[k]} at ({i},{j}) -> ({x},{y})\n")
                moved = True
                GridColor[i][j] = '0'
                break  # stop inner loop after first match
        if moved:
            break  # stop outer loop after first match

go_to_block(0, 0, 5)

print(GridColor)