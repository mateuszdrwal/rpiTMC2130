#define stepper_count 2
#define message_length stepper_count * 8  // excludes start and end bytes

#include <AccelStepper.h>

byte message_buffer[256] = {0};
bool reading_message = false;
int buffer_pointer = 0;
bool running_flag = false;
bool last_running_flag = false;
byte dir_pins[stepper_count] = {0b00010000, 0b00100000};  //, 0b00000001};
long steps;

void step1() { PORTB ^= 0b00000100; }

void step2() { PORTB ^= 0b00001000; }

void step3() { PORTB ^= 0b00000010; }

void nothing() {}

AccelStepper steppers[stepper_count] = {
    AccelStepper(step1, step1),
#if stepper_count > 1
    AccelStepper(step2, step2),
#endif
#if stepper_count > 2
    AccelStepper(step3, step3),
#endif
};

// message structure from rpi:
//
//    0x53 ("S" character) - 1 byte
//    for each stepper:
//        amount of steps for each stepper motor to take - 4 bytes
//        max stepper speed in steps/s for each stepper motor - 2 bytes
//        stepper acceleration in steps/s for each stepper motor - 2 bytes
//    0x45 ("E" character) - 1 byte

void setup() {
    DDRB |= 0b00111111;
    Serial.begin(115200);
}

void process_message() {
    while (Serial.available()) {
        int read_byte = Serial.read();
        if (reading_message) {
            if (read_byte == 'E') {                      // end of message
                if (buffer_pointer == message_length) {  // valid message
                    for (int i = 0; i < stepper_count; i++) {
                        steps = (((uint32_t)message_buffer[i * 8 + 3]) << 0) |
                                (((uint32_t)message_buffer[i * 8 + 2]) << 8) |
                                (((uint32_t)message_buffer[i * 8 + 1]) << 16) |
                                (((uint32_t)message_buffer[i * 8 + 0]) << 24);
                        steppers[i].move(steps);
                        steppers[i].setMaxSpeed(
                            ((message_buffer[i * 8 + 5]) << 0) |
                            ((message_buffer[i * 8 + 4]) << 8));
                        steppers[i].setAcceleration(
                            ((message_buffer[i * 8 + 7]) << 0) |
                            ((message_buffer[i * 8 + 6]) << 8));
                        // Serial.print("move: ");
                        // Serial.println(
                        //     (((uint32_t)message_buffer[i * 8 + 3]) << 0) |
                        //     (((uint32_t)message_buffer[i * 8 + 2]) << 8) |
                        //     (((uint32_t)message_buffer[i * 8 + 1]) << 16) |
                        //     (((uint32_t)message_buffer[i * 8 + 0]) << 24));
                        // Serial.println(steppers[i].distanceToGo());
                        // Serial.print("max speed: ");
                        // Serial.println(((message_buffer[i * 8 + 5]) << 0) |
                        //                ((message_buffer[i * 8 + 4]) << 8));
                        // Serial.print("set acceleration: ");
                        // Serial.println(((message_buffer[i * 8 + 7]) << 0) |
                        //                ((message_buffer[i * 8 + 6]) << 8));
                        if (steps < 0) {
                            PORTB &= ~dir_pins[i];
                        } else {
                            PORTB |= dir_pins[i];
                        }
                    }
                }
                buffer_pointer = 0;
                reading_message = false;

            } else if (read_byte != -1) {
                message_buffer[buffer_pointer] = read_byte;
                buffer_pointer++;
            }
        } else if (read_byte == 'S') {  // start of message
            reading_message = true;
        }
    }
}

void loop() {
    last_running_flag = running_flag;
    running_flag = false;

    for (int i = 0; i < stepper_count; i++) {
        running_flag |= steppers[i].run();
    }

    if (last_running_flag && !running_flag) {
        Serial.print("D");  // done
    }

    if (!running_flag) {
        process_message();
    }
}
