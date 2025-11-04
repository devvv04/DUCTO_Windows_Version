import subprocess
import time
import os
import pygame

# ------------------------
# Function to launch Cheese fullscreen
# ------------------------
def open_cheese_fullscreen():
    try:
        os.system("pkill cheese")
        process = subprocess.Popen(["cheese", "--fullscreen"])
        return process
    except Exception as e:
        print(f"[WARN] Cheese not available: {e}")
        return None

# ------------------------
# Serial setup
# ------------------------
try:
    import serial
    ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
    time.sleep(2)
except Exception as e:
    print(f"[WARN] Serial not available: {e}")
    ser = None

# ------------------------
# Safe spidev setup (for MCP3008 joystick)
# ------------------------
try:
    import spidev
    spi = spidev.SpiDev()
    spi.open(0, 0)  # bus 0, CE0
    spi.max_speed_hz = 1350000
except Exception as e:
    print(f"[WARN] spidev not available: {e}")
    spi = None

def read_adc(channel):
    if spi:
        adc = spi.xfer2([1, (8 + channel) << 4, 0])
        data = ((adc[1] & 3) << 8) | adc[2]
        return data
    return 512

# ------------------------
# Joystick setup
# ------------------------
pygame.init()
pygame.joystick.init()
usb_joystick = None
if pygame.joystick.get_count() > 0:
    usb_joystick = pygame.joystick.Joystick(0)
    usb_joystick.init()
    print(f"Using USB joystick: {usb_joystick.get_name()}")
else:
    print("No USB joystick found. Using keyboard fallback.")

# ------------------------
# State variables
# ------------------------
aux_levels = [0, 25, 50, 75, 100]
aux_index = 0
aux_off = False
b_was_pressed = False
a_was_pressed = False
y_was_pressed = False
controls_enabled = False
clock = pygame.time.Clock()
max_speed = 30

# ------------------------
# Shared status for GUI
# ------------------------
status = {"enabled": False, "brush": 0, "wheel": 1}

def update_status(key, value):
    status[key] = value
    print("[STATUS]", status)

# ------------------------
# Control functions
# ------------------------
def enable_controls():
    global controls_enabled
    controls_enabled = True
    update_status("enabled", True)

def disable_controls():
    global controls_enabled
    controls_enabled = False
    update_status("enabled", False)

def set_brush_level(level):
    global aux_index
    aux_index = max(0, min(3, level))
    update_status("brush", aux_index)

def set_wheel_speed(level):
    global max_speed
    if level == 1: max_speed = 30
    elif level == 2: max_speed = 45
    elif level == 3: max_speed = 60
    update_status("wheel", level)

# ------------------------
# Main loop
# ------------------------
def joystick_loop():
    global controls_enabled, aux_index, aux_off
    global b_was_pressed, a_was_pressed, y_was_pressed

    cheese_process = open_cheese_fullscreen()  # 🔹 restore cheese

    try:
        while True:
            pygame.event.pump()

            if usb_joystick:
                # === Original joystick logic ===
                b_pressed = usb_joystick.get_button(1)
                if b_pressed and not b_was_pressed:
                    controls_enabled = not controls_enabled
                    update_status("enabled", controls_enabled)
                    aux_index = 0
                    aux_off = False
                b_was_pressed = b_pressed

                if not controls_enabled:
                    frame = "D 0 0 0 0 0"
                    if ser: ser.write((frame + "\n").encode())
                    print(frame)
                    clock.tick(20)
                    continue

                usb_y = -usb_joystick.get_axis(1)
                usb_x = usb_joystick.get_axis(0)

                adc_x = read_adc(1)
                adc_y = read_adc(0)
                mcp_x = ((1023 - adc_x) - 512) / 512.0
                mcp_y = (adc_y - 512) / 512.0

                threshold = 0.2
                x_axis, y_axis = 0, 0
                if abs(usb_x) > threshold or abs(usb_y) > threshold:
                    x_axis, y_axis = usb_x, usb_y
                elif abs(mcp_x) > threshold or abs(mcp_y) > threshold:
                    x_axis, y_axis = mcp_x, mcp_y

                if usb_joystick.get_button(4): set_wheel_speed(1)
                if usb_joystick.get_button(2): set_wheel_speed(2)
                if usb_joystick.get_button(5): set_wheel_speed(3)

                m1 = m2 = m3 = m4 = 0
                if abs(y_axis) > threshold:
                    speed = int(y_axis * max_speed)
                    m1 = m2 = m3 = m4 = speed
                elif abs(x_axis) > threshold:
                    turn_speed = int(x_axis * max_speed)
                    m1 = m3 = turn_speed
                    m2 = m4 = -turn_speed

                a_pressed = usb_joystick.get_button(0)
                if a_pressed and not a_was_pressed:
                    aux_index = min(3, aux_index + 1)
                    set_brush_level(aux_index)
                a_was_pressed = a_pressed

                y_pressed = usb_joystick.get_button(3)
                if y_pressed and not y_was_pressed:
                    aux_index = max(0, aux_index - 1)
                    set_brush_level(aux_index)
                y_was_pressed = y_pressed

                frame = f"D {m1} {m2} {m3} {m4} {aux_index}"
                if ser: ser.write((frame + "\n").encode())
                print(frame)
                clock.tick(20)

            else:
                # === Keyboard fallback ===
                keys = pygame.key.get_pressed()
                if keys[pygame.K_e]: enable_controls()
                if keys[pygame.K_d]: disable_controls()
                if keys[pygame.K_1]: set_brush_level(1)
                if keys[pygame.K_2]: set_brush_level(2)
                if keys[pygame.K_3]: set_brush_level(3)
                if keys[pygame.K_q]: set_wheel_speed(1)
                if keys[pygame.K_w]: set_wheel_speed(2)
                if keys[pygame.K_r]: set_wheel_speed(3)
                time.sleep(0.1)

    except KeyboardInterrupt:
        if cheese_process: cheese_process.terminate()
        if ser: ser.close()
        pygame.quit()
