import subprocess
import time
import re
import RPi.GPIO as GPIO

# GPIO setup
GREEN_LED_PIN = 18  # Pin 12 on the Raspberry Pi
GPIO.setmode(GPIO.BCM)
GPIO.setup(GREEN_LED_PIN, GPIO.OUT)
GPIO.output(GREEN_LED_PIN, GPIO.LOW)  # Initially turn off the LED

def run_bluetoothctl():
    """Start bluetoothctl as a subprocess and return the process handle."""
    return subprocess.Popen(
        ['bluetoothctl'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line-buffered
        universal_newlines=True
    )

def run_command(process, command):
    """Run a command in bluetoothctl."""
    print(f"Running command: {command}")
    process.stdin.write(command + '\n')
    process.stdin.flush()
    time.sleep(1)  # Allow some time for processing

def check_connected_devices():
    """Check for connected devices and return their MAC addresses."""
    process = subprocess.Popen(
        ['bluetoothctl', 'devices', 'Connected'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate()
    
    connected_devices = []
    for line in stdout.split('\n'):
        match = re.search(r"Device ([\w:]+) (.+)", line)
        if match:
            device_mac = match.group(1)
            device_name = match.group(2)
            connected_devices.append((device_mac, device_name))
    
    return connected_devices

def blink_led(pin, times, interval):
    """Blink the LED a specified number of times."""
    for _ in range(times):
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(interval)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(interval)

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

    # Set as default agent and turn on the green LED
    print("Setting default agent...")
    run_command(process, "default-agent")
    GPIO.output(GREEN_LED_PIN, GPIO.HIGH)  # Turn on the green LED to indicate the agent is ready

    # Start device discovery
    print("Starting device discovery...")
    run_command(process, "scan on")

    # Wait for 5 seconds before stopping scan
    time.sleep(5)

    # Stop scanning and quit
    print("Stopping device discovery...")
    run_command(process, "scan off")
    run_command(process, "quit")

    # Wait for 2 seconds before checking connected devices
    time.sleep(2)

    # Check for connected devices
    connected_devices = check_connected_devices()
    if connected_devices:
        print(f"Connected device found: {connected_devices[0][1]} ({connected_devices[0][0]})")
        
        # Turn on the LED
        GPIO.output(GREEN_LED_PIN, GPIO.HIGH)

        # Blink the LED 3 times for confirmation
        blink_led(GREEN_LED_PIN, 3, 0.5)

        # Leave the LED on for 3 seconds
        time.sleep(3)

        # Turn off the LED
        GPIO.output(GREEN_LED_PIN, GPIO.LOW)
    else:
        print("No connected devices found.")

    # Cleanup GPIO
    GPIO.cleanup()

if __name__ == "__main__":
    main()
