#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// -------------------- PCA9685 서보 설정 --------------------
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// 서보 펄스 범위 (MG90S 기준, 필요시 조정)
#define SERVOMIN  102   // 0도 (약 0.732ms)
#define SERVOMAX  512   // 180도 (약 2.93ms)

// 서보 채널 정의
int servo0 = 0;
int servo1 = 1;
int servo2 = 2;
int servo3 = 3;

// 반대 방향 서보 설정 (true = 각도 반전)
bool reverseServo[4] = {false, false, false, false};  // 필요시 true로 변경

// -------------------- ULN2003 스텝모터 설정 --------------------
const int IN1 = 8;
const int IN2 = 9;
const int IN3 = 10;
const int IN4 = 11;

// half-step 시퀀스 (8 단계)
const int steps = 8;
const int seq[steps][4] = {
  {1,0,0,0},
  {1,1,0,0},
  {0,1,0,0},
  {0,1,1,0},
  {0,0,1,0},
  {0,0,1,1},
  {0,0,0,1},
  {1,0,0,1}
};
int stepDelay = 5; // 각 스텝 사이 delay(ms). 2~10 권장

// -------------------- setup --------------------
void setup() {
  Serial.begin(9600);
  Serial.println("PCA9685 + 28BYJ-48 Test");

  // PCA9685 초기화
  pwm.begin();
  pwm.setPWMFreq(50);  // 서보모터 표준 50Hz
  delay(10);

  // 서보 초기 위치
  Serial.println("Moving servos to 0 degrees...");
  setServoAngle(servo0, 0);
  setServoAngle(servo1, 0);
  setServoAngle(servo2, 0);
  setServoAngle(servo3, 0);
  delay(1000);

  Serial.println("Moving servos to 90 degrees...");
  setServoAngle(servo0, 90);
  setServoAngle(servo1, 90);
  setServoAngle(servo2, 90);
  setServoAngle(servo3, 90);
  delay(500);

  // 스텝모터 핀 모드 설정
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  Serial.println("Setup complete!");
}

// -------------------- loop --------------------
void loop() {
  // 스텝모터 연속 회전 (시계 방향)
  for (int i = 0; i < steps; i++) {
    setCoils(i);
    delay(stepDelay);
  }

  // 필요시 서보 이동 예제 (원하면 여기서 추가 가능)
  // 예: setServoAngle(servo0, 45);
}

// -------------------- 서보 제어 함수 --------------------
void setServoAngle(int channel, int angle) {
  if (reverseServo[channel]) {
    angle = 180 - angle;
  }
  int pulse = map(angle, 0, 180, SERVOMIN, SERVOMAX);
  pwm.setPWM(channel, 0, pulse);

  Serial.print("Servo ");
  Serial.print(channel);
  Serial.print(" -> ");
  Serial.print(angle);
  Serial.println(" degrees");
}

// -------------------- 스텝모터 코일 제어 함수 --------------------
void setCoils(int index) {
  digitalWrite(IN1, seq[index][0]);
  digitalWrite(IN2, seq[index][1]);
  digitalWrite(IN3, seq[index][2]);
  digitalWrite(IN4, seq[index][3]);
}
