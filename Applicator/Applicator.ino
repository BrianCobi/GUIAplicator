//**************************************************************
//*                                                            *
//*          Author: Brian Cobian                              *
//*          Project: Label Detector                           *
//*          Date: JULY 8, 2024                                *
//*          Description: This program re-engineers the label  *
//*                       applicator detector. It uses a       *
//*                       photodiode aligned with an infrared  *
//*                       LED to detect labels passing through *
//*                       a head unit.                         *
//*                                                            *
//**************************************************************


#include <AccelStepper.h>
#include <Ethernet.h>
#include <EthernetUdp.h>




//********************* UDP COMMUNICATION *********************
// Enter a MAC address and IP address for your controller below.
// The IP address will be dependent on your local network:
byte mac[] = {
  0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED
};
IPAddress ip(192, 168, 111, 179);

unsigned int localPort = 2212;      // local port to listen on

// buffers for receiving and sending data
char packetBuffer[UDP_TX_PACKET_MAX_SIZE];  // buffer to hold incoming packet
char ReplyBuffer[] = "RESPONSEEEEE";        // a string to send back

// An EthernetUDP instance to let us send and receive packets over UDP
EthernetUDP Udp;





// ********************* STEPPER MOTOR CONTROL ****************
// Define stepper motors using DRIVER interface, pins 7 and 6 for step and direction
AccelStepper stepper(AccelStepper::DRIVER, 7, 6);


// Parameters
// [speed][offset][cal][feed][Stop][count][paperlow][Head]
int currentValues[8] = {1200, 0, 0, 0, 1, 0, 0, 0};

// Define pins and constants
const int button1 = 11; // Button for start/stop
const int button2 = 2; // PhotosensorSimulator
const int button3 = 3; // Calibration button it was 4 before but for some reason 4 doesn't work well
const int Headsensor = 5; // Head open
const int RelayTakeUpReel = 8; //  Stopping and starting AC motor

const int sensorPin = A0; // Analog sensor pin
const int DistanceSensor = A1; //PaperLowSignal
const int labelQuantity = 3; // Number of labels to average
const int marginError = 50; // Margin of error in sensor readings

// Operation variables
int direction = 1; // Motor direction, 1 or -1
int tags = 0; // Label detection counter
int tagscalibration = 0;
int average[labelQuantity] = {0}; // Array to store steps for averaging
bool stop = 1; // Flag to indicate when to stop the motor
bool controlGaps = false; // Flag to control gap detection logic
int previousLight = 0; // Previous sensor value for gap detection
int LabelSize = 0; // Calculated label size in steps
bool calibrationMode = true; // Flag indicating calibration mode
int offset = 300; // Calculated offset in steps based on sensor distance to label output
int offsetuser = 0;
bool headopen = false; // Label detection flag
bool paperlow = false;

int ambientLight = 0; // Ambient light value
int closedLight = 0; // Light value with head closed
int labelLight = 0; // Light value with a label present
int gapLight = 0; // Light value with a gap
int threshold = 220; // Threshold for label and gap detection
bool Alertmessage = false;

// Motor speed
int speed = 300; // MAX speed = 1200 pulses per second
bool label = true; // Label detection flag




void setup() {
  // Initialize stepper motor speed and acceleration
  stepper.setMaxSpeed(speed);
  stepper.setAcceleration(speed);
  stepper.setSpeed(speed);

  // Configure button pins as input with pull-up resistors
  pinMode(button1, INPUT_PULLUP); // When pressed, reads 0; normally 1
  pinMode(button2, INPUT_PULLUP); // When pressed, reads 0; normally 1
  pinMode(button3, INPUT_PULLUP); // When pressed, reads 0; normally 1
  pinMode(Headsensor, INPUT_PULLUP); // When pressed, reads 0; normally 1

  Ethernet.begin(mac, ip);
  Serial.begin(9600);
  Udp.begin(localPort);
}

void loop() {
  updcheck();

  
  // Check if start/stop button is pressed
  if (!digitalRead(button1)) {
    while (!digitalRead(button1)) {} 
    stop = !stop; // Toggle stop state
    Serial.println("Button 1 pressed");
  }

  if (!digitalRead(Headsensor)) {
    delay(100);
    if (!headopen) {
      Serial.println("Head Open");
      updatedata();
      headopen = true;
    }
  } else {
    if (headopen) {
      Serial.println("Head Closed");
      tagscalibration = 0; // Enable label detection
      label = true;
      offset = 300;
      headopen = false;
    }
  }

  if (stop || headopen) {
    if (!Alertmessage) {
      updatedata();
      Alertmessage = true;
    }
  } else {   
    if (Alertmessage)  {
      updatedata();
      Alertmessage = false;
    }

    if (!digitalRead(button2)) {
      while (!digitalRead(button2)) {} // Wait until item goes through
      Serial.println("Button 2 pressed");
      label = true; // Enable label detection
    }

    if (!digitalRead(button3)) {
      while (!digitalRead(button3)) {} // Wait until item goes through
      Serial.println("Button 3 pressed");
      tagscalibration = 0; // Enable label detection
      label = true;
      offset = 300;
    }

    if (tagscalibration <= labelQuantity) {
      calibrationMode = true;
      DefineLabelsize();
      return;
    } else {
      calibrationMode = false;
    }

    if (label && !calibrationMode) {
      detectLabels();
    }
  }
}

void updcheck() {
  int packetSize = Udp.parsePacket();
  if (packetSize) {
    IPAddress remote = Udp.remoteIP();
    for (int i = 0; i < 4; i++) {
      Serial.print(remote[i], DEC);
      if (i < 3) {
        Serial.print(".");
      }
    }
    Serial.print(", port ");
    Serial.println(Udp.remotePort());

    Udp.read(packetBuffer, UDP_TX_PACKET_MAX_SIZE);
    int newValues[6] = {0, 0, 0, 0, 0, 0};

    sscanf(packetBuffer, "[%d|%d|%d|%d|%d|%d]", &newValues[0], &newValues[1], &newValues[2], &newValues[3], &newValues[4],&newValues[5]);
    
    if(newValues[5] == 0){
        tags = 0;
    }


    bool valuesChanged = false;
    for (int i = 0; i < 6; i++) {
      if (newValues[i] != currentValues[i]) {
        valuesChanged = true;
        break;
      }
    }

    if (valuesChanged) {
      Serial.println("Values have changed. Updating current values.");
      for (int i = 0; i < 6; i++) {
        currentValues[i] = newValues[i];
      }
      updatedata();
    } else {
      Serial.println("Values have not changed.");
    }

    memset(packetBuffer, 0, UDP_TX_PACKET_MAX_SIZE);
  }
}

void updatedata() {
  if (currentValues[0] != speed) {
    speed = currentValues[0];
    Serial.print("Updated Speed to: ");
    Serial.println(speed);
    stepper.setMaxSpeed(speed);
    stepper.setAcceleration(speed);
    stepper.setSpeed(speed);

  }

  if (currentValues[1] != offsetuser) {
    offsetuser = currentValues[1];
    Serial.print("Updated Offset to: ");
    Serial.println(offsetuser);
  }

  if (currentValues[2]) { // Calibration
    tagscalibration = 0; // Enable label detection
    label = true;
    offset = 300;
    calibrationMode = true;
    currentValues[2] = 0;
  }

  if (currentValues[3]) { // FEED
    label = true;
    currentValues[3] = 0;
  }

  stop = currentValues[4] != 0;

  if (currentValues[5] != tags) {
    currentValues[5] = tags;
  }

  currentValues[6] = paperlow ? 1 : 0;
  currentValues[7] = headopen ? 1 : 0;

  String dataToSend = formatCurrentValues();
  Serial.println(dataToSend);
  Udp.beginPacket("192.168.111.192", 2212);
  Udp.print(dataToSend);
  Udp.endPacket();
  // Udp.beginPacket("192.168.111.190", 2212);
  // Udp.print(dataToSend);
  // Udp.endPacket();
  // Udp.beginPacket("192.168.111.169", 2212);
  // Udp.print(dataToSend);
  // Udp.endPacket();
}

String formatCurrentValues() {
  int cal = calibrationMode ? 1 : 0;
  int feed = label ? 1 : 0;
  char formattedData[50]; // Adjust size as necessary
  sprintf(formattedData, "[%d|%d|%d|%d|%d|%d|%d|%d]", currentValues[0], currentValues[1], cal, feed, currentValues[4], currentValues[5], currentValues[6], currentValues[7]);
  return String(formattedData);
}

void DefineLabelsize() {
  int rawLight = analogRead(sensorPin); // Read sensor value
  if (rawLight >= 450) {
    Serial.println("No labels");
    stop = true;
    return loop();
  }

  if (rawLight < (threshold - marginError) && !controlGaps) {
    tagscalibration++;
    tags++; // Increment label counter
    controlGaps = true; // Set control gap flag
    Serial.print("Tag Detected: ");
    Serial.println(tags);
    if (tagscalibration >= 2) {
      average[(tagscalibration - 1) % labelQuantity] = stepper.currentPosition(); // Store steps in array
    }

    stepper.setCurrentPosition(0); // Reset stepper position
    stepper.setSpeed(speed * direction); // Set stepper speed

    updatedata();
    if (tagscalibration >= labelQuantity) {
      LabelSize = calculateAverage(average, labelQuantity); // Calculate average size
      Serial.print("LabelSize: ");
      Serial.println(LabelSize);
    }
  } else if (rawLight > (threshold + marginError) && controlGaps) {
    controlGaps = false; // Reset control gap flag
  }
  stepper.runSpeed(); // Run stepper at constant speed

  // Adjust offset if necessary
  if (LabelSize < offset && tagscalibration == labelQuantity + 1) {
    Serial.print("Missing steps: ");
    Serial.println(offset);
    offset = abs(LabelSize - offset);
    Serial.print("New Offset: ");
    Serial.println(offset);
  }
}

void detectLabels() {
  int rawLight = analogRead(sensorPin); // Read sensor value

  if (rawLight < (threshold - marginError) && !controlGaps) {
    tags++; // Increment label counter
    controlGaps = true; // Set control gap flag
    Serial.print("Tag detected: ");
    Serial.println(tags);
    average[tags % labelQuantity] = stepper.currentPosition(); // Store steps in array
    stepper.setCurrentPosition(0); // Reset stepper position
    stepper.setSpeed(speed * direction); // Set stepper speed
  
    while (stepper.currentPosition() != (offset + offsetuser) * direction) {
      stepper.runSpeed();
    }

    if (tags >= labelQuantity) {
      LabelSize = calculateAverage(average, labelQuantity); // Calculate average size
      Serial.print("Tag size: ");
      Serial.println(LabelSize);
    }
    label = false; // Reset label flag
    updatedata();
  } else if (rawLight > (threshold + marginError) && controlGaps) {
    controlGaps = false; // Reset control gap flag
  }
  stepper.runSpeed(); // Run stepper at constant speed
}

// Calculate average of an array of values
int calculateAverage(int *values, int count) {
  long sum = 0; // Accumulator for sum of values
  for (int i = 0; i < count; i++) {
    sum += values[i]; // Sum each value
  }
  return sum / count; // Return average
}