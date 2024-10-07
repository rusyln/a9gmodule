import subprocess
import time
import re

# GPIO library for LED control
import RPi.GPIO as GPIO

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)

def run_bluetoothctl():
    """Start bluetoothctl as a subprocess and return the process handle."""
    return subprocess.Popen(
        ['bluetoothctl'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line-buffered
    )

def run_command(process, command):
    """Run a command in bluetoothctl."""
    print(f"Running command: {command}")
    process.stdin.write(command + '\n')
    process.stdin.flush()
    time.sleep(1)  # Allow some time for processing

def main():
    # Start bluetoothctl
    process = run_bluetoothctl()

    # Power on the Bluetooth adapter
    print("Powering on the Bluetooth adapter...")
    run_command(process, "power on")

    # Make the device discoverable
    print("Making device discoverable...")
    run_command(process, "discoverable on")

    # Enable the agent
    print("Enabling agent...")
    run_command(process, "agent on")

    # Set as default agent
    print("Setting default agent...")
    run_command(process, "default-agent")

    # Start device discovery
    print("Starting device discovery...")
    run_command(process, "scan on")

    try:
        print("Waiting for a device to connect...")
        while True:
            # Read output continuously
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break  # Exit loop if the process is terminated
            if output:
                print(f"Output: {output.strip()}")

                # Check for the passkey confirmation prompt
                if "Confirm passkey" in output:
                    print("Responding 'yes' to passkey confirmation...")
                    run_command(process, "yes")

                # Check for authorization service prompt
                if "[agent] Authorize service" in output:
                    print("Responding 'yes' to authorization service...")
                    run_command(process, "yes")

                # Check for new device connection
                if "NEW Device" in output:
                    match = re.search(r"NEW Device ([\w:]+)", output)
                    if match:
                        device_mac = match.group(1)
                        print(f"Found new device: {device_mac}")

                        # Pairing with the detected device
                        print(f"Pairing with device {device_mac}...")
                        run_command(process, f"pair {device_mac}")

                        # Trust the device
                        print(f"Trusting device {device_mac}...")
                        run_command(process, f"trust {device_mac}")

                        # Connect to the device
                        print(f"Connecting to device {device_mac}...")
                        run_command(process, f"connect {device_mac}")

                # Check for the invalid command message
                if "Invalid command in menu main" in output:
                    print("Invalid command detected, waiting to quit bluetoothctl...")

                    # Wait for 5 seconds before sending quit command
                    time.sleep(5)

                    # Now wait for the expected prompt that ends with #
                    while True:
                        next_output = process.stdout.readline()
                        if next_output:
                            print(f"Next Output: {next_output.strip()}")
                            if next_output.strip().endswith('#'):
                                print("Sending quit command...")
                                run_command(process, "quit")
                                break  # Exit the while loop after sending quit command

                    # Turn on the LED light after quitting
                    GPIO.output(17, GPIO.HIGH)  # Turn on LED
                    print("LED turned on. Waiting for user command...")
                    # Wait for a command (e.g., just wait here)
                    while True:
                        time.sleep(1)  # Just wait indefinitely

    except KeyboardInterrupt:
        print("Exiting...")

    finally:
        # Stop scanning
        print("Stopping device discovery...")
        run_command(process, "scan off")
        process.terminate()
        GPIO.cleanup()  # Clean up GPIO settings

if __name__ == "__main__":
    main()
