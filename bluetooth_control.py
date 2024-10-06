from gpiozero import Button
from signal import pause
import subprocess
import threading
import serial
import time
import re

# Define GPIO pin for the button
BUTTON_PIN = 17

# Initialize the button
button = Button(BUTTON_PIN)

def enable_bluetooth():
    print("Enabling Bluetooth...")
    # Enable Bluetooth and make it discoverable and pairable
    subprocess.run(["bluetoothctl", "power", "on"])
    subprocess.run(["bluetoothctl", "discoverable", "on"])
    subprocess.run(["bluetoothctl", "pairable", "on"])
    print("Bluetooth is enabled, discoverable, and pairable.")
    
    # Start the pairing acceptance in a separate thread
    threading.Thread(target=auto_accept_pairing, daemon=True).start()

def auto_accept_pairing():
    print("Listening for pairing requests...")
    # Start bluetoothctl interactively and respond to prompts
    process = subprocess.Popen(['bluetoothctl'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        while True:
            output = process.stdout.readline()
            if output:
                output = output.strip()  # Clean the output
                print(output)  # Print the output for debugging

                # Respond to "Confirm passkey" and "Authorize service" prompts
                if 'Confirm passkey' in output or 'Request confirmation' in output:
                    print("Automatically confirming the passkey...")
                    process.stdin.write('yes\n')  # Automatically respond with 'yes'
                    process.stdin.flush()

                elif 'Authorize service' in output:
                    print("Automatically authorizing service...")
                    process.stdin.write('yes\n')  # Automatically respond with 'yes'
                    process.stdin.flush()

                # Extract the device MAC address from the output
                device_match = re.search(r'Device\s+([0-9A-Fa-f:]{17})', output)
                if device_match:
                    mac_address = device_match.group(1)
                    print(f"Connected device MAC address: {mac_address}")
                    save_mac_address(mac_address)
                    bind_rfcomm(mac_address)

    except KeyboardInterrupt:
        print("Exiting...")
        process.terminate()

def save_mac_address(mac_address):
    with open('device_connected.txt', 'a') as file:
        file.write(f"{mac_address}\n")
    print(f"Saved MAC address: {mac_address} to device_connected.txt")

def bind_rfcomm(mac_address):
    # Bind to the RFCOMM device
    print(f"Binding to RFCOMM for device: {mac_address}")
    subprocess.run(["sudo", "rfcomm", "bind", "/dev/rfcomm0", mac_address])
    print("RFCOMM bound.")

def wait_for_rfcomm():
    while True:
        try:
            ser = serial.Serial('/dev/rfcomm0', 9600)
            print("Connected to RFCOMM")
            return ser  # Return the connected serial object
        except serial.SerialException:
            print("Waiting for RFCOMM connection...")
            time.sleep(1)  # Wait a second before retrying

def listen_for_commands(ser):
    while True:
        try:
            if ser.in_waiting > 0:
                command = ser.readline().decode('utf-8').strip()
                print(f"Received command: {command}")

                # Execute the command using subprocess
                try:
                    subprocess.call(command, shell=True)
                except Exception as e:
                    print(f"Error executing command: {e}")

        except OSError as e:
            print(f"Error with serial port: {e}. Attempting to re-establish connection.")
            try:
                ser.close()  # Close the existing connection
                ser = wait_for_rfcomm()  # Try to open it again
                print("Re-established connection to serial port.")
            except Exception as ex:
                print(f"Failed to re-establish connection: {ex}")
                break  # Exit loop on persistent failure

# Attach the button hold event to enable Bluetooth
button.when_held = enable_bluetooth

# Print waiting message
print("Waiting for button press...")

# Wait for events
pause()

# Start listening for commands after binding RFCOMM
ser = wait_for_rfcomm()
threading.Thread(target=listen_for_commands, args=(ser,), daemon=True).start()
