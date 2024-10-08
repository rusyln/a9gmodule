from gpiozero import Button
from signal import pause
import subprocess
import threading
import re
import bluetooth
import time

# Define GPIO pin for the button
BUTTON_PIN = 17
last_connected_mac = None
# Initialize the button
button = Button(BUTTON_PIN)

# Global flag to indicate pairing completion
pairing_complete = False

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
    global last_connected_mac, pairing_complete
    
    print("Listening for pairing requests...")
    process = subprocess.Popen(['bluetoothctl'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        while True:
            output = process.stdout.readline()
            if output:
                output = output.strip()
                print(output)

                # Check for device connection
                device_match = re.search(r'Device\s+([0-9A-Fa-f:]{17})', output)
                if device_match:
                    mac_address = device_match.group(1)
                    print(f"Connected device MAC address: {mac_address}")
                    
                    # Check if it's the same device as before
                    if mac_address == last_connected_mac:
                        print("Same device detected. Ignoring.")
                        continue  # Skip saving and proceed to handle other prompts

                    # Save the MAC address if it's different
                    print(f"Saving MAC address: {mac_address}")
                    save_mac_address(mac_address)
                    last_connected_mac = mac_address  # Update last connected MAC
                    
                    # Wait for [agent] Confirm passkey
                    while True:
                        output = process.stdout.readline().strip()
                        print(output)
                        if "[agent] Confirm passkey" in output:
                            print("Automatically confirming the passkey...")
                            process.stdin.write('yes\n')
                            process.stdin.flush()
                            time.sleep(5)  # Wait for 5 seconds
                            break  # Exit the inner loop after confirming

                # Wait for [agent] Authorize service
                while True:
                    output = process.stdout.readline().strip()
                    print(output)
                    if "[agent] Authorize service" in output:
                        print("Authorization request received. Automatically authorizing service...")
                        process.stdin.write('yes\n')
                        process.stdin.flush()
                        time.sleep(5)  # Wait for 5 seconds
                        break  # Exit the inner loop after authorizing

                # Check if pairing is complete
                if 'Paired: yes' in output or 'Connection successful' in output:
                    print("Pairing completed successfully.")
                    process.stdin.write('quit\n')
                    process.stdin.flush()
                    time.sleep(5)  # Wait for 5 seconds
                    pairing_complete = True  # Set the flag to indicate pairing is complete
                    break

                # Detect invalid commands
                elif 'Invalid command' in output:
                    print("Invalid command detected. Quitting bluetoothctl...")
                    process.stdin.write('quit\n')
                    process.stdin.flush()
                    break

    except KeyboardInterrupt:
        print("Exiting...")
        process.terminate()



def save_mac_address(mac_address):
    with open('device_connected.txt', 'a') as file:
        file.write(f"{mac_address}\n")
    print(f"Saved MAC address: {mac_address} to device_connected.txt")

def start_rfcomm_server():
    print("Starting RFCOMM server on channel 23...")
    
    # Bind RFCOMM after SP profile is added
    subprocess.run(["sudo", "sdptool", "add", "--channel=23", "SP"])

    # Create a Bluetooth socket
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    port = 23
    server_sock.bind(("", port))
    server_sock.listen(1)

    print(f"Listening for connections on RFCOMM channel {port}...")

    try:
        client_sock, address = server_sock.accept()
        print("Connection established with:", address)

        while True:
            recvdata = client_sock.recv(1024).decode('utf-8').strip()  # Decode bytes to string and strip whitespace
            print("Received command:", recvdata)

            if recvdata == "Q":
                print("Ending connection.")
                break

            # Execute the received command
            try:
                # Run the command using subprocess
                output = subprocess.check_output(recvdata, shell=True, text=True)
                print("Command output:", output)  # Print command output for debugging
                client_sock.send(output.encode('utf-8'))  # Send the output back to the client
            except subprocess.CalledProcessError as e:
                error_message = f"Error executing command: {e}\nOutput: {e.output}"
                print("Error:", error_message)  # Print the error for debugging
                client_sock.send(error_message.encode('utf-8'))  # Send error message back to client

    except OSError as e:
        print("Error:", e)

    finally:
        client_sock.close()
        server_sock.close()
        print("Sockets closed.")

# Function to wait for pairing completion before proceeding
def wait_for_pairing_completion():
    global pairing_complete
    print("Waiting for pairing to complete...")
    while not pairing_complete:
        time.sleep(1)  # Sleep for a second and check again
    print("Pairing completed. Proceeding with SP service setup and RFCOMM server...")

    # After pairing is done, add SP service and start RFCOMM server
    start_rfcomm_server()

# Attach the button hold event to enable Bluetooth
button.when_held = enable_bluetooth

# Print waiting message
print("Waiting for button press...")

# Wait for events
pause()

# Start waiting for pairing completion in a new thread
threading.Thread(target=wait_for_pairing_completion, daemon=True).start()
