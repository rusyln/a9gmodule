import RPi.GPIO as GPIO
import time

# Set up the GPIO using BCM numbering
GPIO.setmode(GPIO.BCM)

# Define the GPIO pins for the buttons and LEDs
BUTTON_PIN_1 = 17
BUTTON_PIN_2 = 27
GREEN_LED_PIN = 18
RED_LED_PIN = 23
ORANGE_LED_PIN = 24

# Set up GPIO pins for the buttons as input with internal pull-up resistors enabled
GPIO.setup(BUTTON_PIN_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_PIN_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Set up GPIO pins for the LEDs as outputs
GPIO.setup(GREEN_LED_PIN, GPIO.OUT)
GPIO.setup(RED_LED_PIN, GPIO.OUT)
GPIO.setup(ORANGE_LED_PIN, GPIO.OUT)

# Turn off all LEDs initially
GPIO.output(GREEN_LED_PIN, GPIO.LOW)
GPIO.output(RED_LED_PIN, GPIO.LOW)
GPIO.output(ORANGE_LED_PIN, GPIO.LOW)

print("Waiting for button presses...")

try:
    while True:
        # Check if button connected to GPIO17 is pressed
        if GPIO.input(BUTTON_PIN_1) == GPIO.LOW:
            print("Button on GPIO17 pressed")
            GPIO.output(RED_LED_PIN, GPIO.HIGH)  # Turn on the red LED
        else:
            GPIO.output(RED_LED_PIN, GPIO.LOW)  # Turn off the red LED

        # Check if button connected to GPIO27 is pressed
        if GPIO.input(BUTTON_PIN_2) == GPIO.LOW:
            print("Button on GPIO27 pressed")
            GPIO.output(ORANGE_LED_PIN, GPIO.HIGH)  # Turn on the orange LED
        else:
            GPIO.output(ORANGE_LED_PIN, GPIO.LOW)  # Turn off the orange LED

        # If both buttons are pressed at the same time
        if GPIO.input(BUTTON_PIN_1) == GPIO.LOW and GPIO.input(BUTTON_PIN_2) == GPIO.LOW:
            print("Both buttons pressed simultaneously")
            GPIO.output(GREEN_LED_PIN, GPIO.HIGH)  # Turn on the green LED
        else:
            GPIO.output(GREEN_LED_PIN, GPIO.LOW)  # Turn off the green LED

        # Small delay to avoid bouncing issues
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Script interrupted by user")

finally:
    # Clean up GPIO settings before exiting
    GPIO.cleanup()
    print("GPIO cleanup completed")

