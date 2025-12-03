#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// --- I. 릴레이 및 푸시 버튼 정의 ---
const int buttonPin = 3;   // 푸시 버튼 입력 (D3)
const int relayPin = 4;    // 릴레이 제어 출력 (D4)

// 래치 상태 변수: true = 릴레이 ON (시스템 구동), false = 릴레이 OFF (전원 차단)
volatile bool latchState = true; 

// 디바운스 변수
long lastDebounceTime = 0;
long debounceDelay = 200; 
int buttonState;
int lastButtonState = HIGH; 

// --- II. 서보 모터 정의 (PCA9685) ---
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVOMIN  102    // 0도 펄스
#define SERVOMAX  512    // 180도 펄스
int servo0 = 0;
int servo1 = 1;
int servo2 = 2;
int servo3 = 3;
bool reverseServo[4] = {false, false, false, false};

// --- III. LM35 온도 센서 정의 ---
const int tempPin = A0; // LM35 출력(Vout)을 아날로그 핀 A0에 연결

// --- IV. 부저 및 경고 LED 정의 ---
const int buzzerPin = 8;        // 부저 제어 핀 (D8)
const int warning_ledPin = 9;
const float SET_TEMP = 26.0;    // 경고 임계 온도 (섭씨 30.0도)

const int status_ledPin1 = 11;
const int status_ledPin2 = 12;
const int status_ledPin3 = 13;


// --- 1. SETUP 함수 ---
void setup() {
  Serial.begin(9600);
  Serial.println("System Initializing...");
  
  // 릴레이 및 버튼 핀 설정
  pinMode(relayPin, OUTPUT);
  pinMode(buttonPin, INPUT_PULLUP); // 버튼은 GND에 연결되어 있으므로 내부 풀업 사용

  // <<< 부저 핀 모드 설정 추가 >>>
  pinMode(buzzerPin, OUTPUT);
  digitalWrite(buzzerPin, LOW); // 초기에는 부저 OFF

  // <<< 경고 LED 핀 모드 설정 추가 >>>
  pinMode(warning_ledPin, OUTPUT);
  digitalWrite(warning_ledPin, LOW); // 초기에는 LED OFF

  // <<< 상태 표시 LED 핀 모드 설정 추가 >>>
  pinMode(status_ledPin1, OUTPUT);
  pinMode(status_ledPin2, OUTPUT);
  pinMode(status_ledPin3, OUTPUT);
  digitalWrite(status_ledPin1, LOW); // 초기 LED OFF
  digitalWrite(status_ledPin2, LOW);
  digitalWrite(status_ledPin3, LOW);

  // PCA9685 초기화
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);
  
  // 초기 상태: 릴레이 ON (시스템 구동 시작)
  digitalWrite(relayPin, HIGH); 
  Serial.println("Initial Latch ON. System Ready.");
  
  // 초기 서보 위치 설정 (0도)
  setServoAngle(servo0, 0);
  setServoAngle(servo1, 0);
  setServoAngle(servo2, 0);
  setServoAngle(servo3, 0);
  delay(1000);
}

// --- 2. LOOP 함수 (핵심 래치 및 제어) ---
void loop() {
  // --- 2-1. LATCH DEBOUNCING LOGIC ---
  int reading = digitalRead(buttonPin);

  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading != buttonState) {
      buttonState = reading;

      // 버튼이 눌렸다면 (LOW) 래치 상태를 토글
      if (buttonState == LOW) {
        latchState = !latchState;
      }
    }
  }
  lastButtonState = reading;
  
// --- 2-2. RELAY CONTROL (D4) ---
if (latchState) {
  // 릴레이 ON (시스템 구동 시작) -> 모터 구동을 위해 릴레이 코일은 꺼져야 NC 연결
  digitalWrite(relayPin, LOW); 
  
} else {
  // 릴레이 OFF (전원 차단) -> 모터 정지를 위해 릴레이 코일은 켜져야 NC 차단
  digitalWrite(relayPin, HIGH); 
}

  // --- 2-3. CONDITIONAL MOVEMENT (테스트) ---
  if (latchState) {
    // 릴레이가 ON일 때만 모터 구동
    static long lastMoveTime = 0;
    static long lastTempCheckTime = 0; 

    if (millis() - lastMoveTime > 2500) { // 2.5초마다 동작
      Serial.println("System ON: Moving Motors...");
      
      // 서보 모터 테스트 (0도 <-> 90도)
      setServoAngle(servo0, 0);
      setServoAngle(servo1, 90);
      setServoAngle(servo2, 0);
      setServoAngle(servo3, 90);
      delay(500);

      setServoAngle(servo0, 90);
      setServoAngle(servo1, 0);
      setServoAngle(servo2, 90);
      setServoAngle(servo3, 0);
      lastMoveTime = millis();
    }

    // 1초마다 온도 측정 및 시리얼 출력 (모터 동작과 별개로 실행)
    if (millis() - lastTempCheckTime > 1000) { 
      
      float currentTemp = getTemperatureC();
      Serial.print("Current Temperature: ");
      Serial.print(currentTemp);
      Serial.println(" C");

      // <<< 부저 제어 로직 추가 >>>
      if (currentTemp > SET_TEMP) {
        // 임계 온도 초과: 부저 켜기, LED 켜기
        digitalWrite(buzzerPin, HIGH);
        digitalWrite(warning_ledPin, HIGH);
        Serial.println("!!! OVERHEAT WARNING: BUZZER ON !!!");
      } else {
        // 임계 온도 미만: 부저 끄기
        digitalWrite(buzzerPin, LOW);
        digitalWrite(warning_ledPin, LOW);
      }
    lastTempCheckTime = millis();
    }
  } else {
    // 릴레이 OFF 시 모터 정지 (전원 차단으로 자동 정지됨)
    Serial.println("EMERGENCY LATCH ENGAGED: Motors OFF.");
    // 서보 펄스 끄기 (혹시 모를 잔류 움직임 방지)
    pwm.setPWM(servo0, 0, 0); 
    pwm.setPWM(servo1, 0, 0);
    pwm.setPWM(servo2, 0, 0);
    pwm.setPWM(servo3, 0, 0);
    delay(500); 
  }
}

// --- 3. 사용자 정의 함수 ---

// LM35 값을 섭씨 온도로 변환하는 함수 (노이즈 완화를 위해 10회 평균값 사용)
float getTemperatureC() {
  const int NUM_READINGS = 20; // 20회 측정 횟수 정의
  long sumValue = 0;           // 20회 측정한 아날로그 값의 합계

  // 1. 10회 반복하여 아날로그 값을 읽고 합산
  for (int i = 0; i < NUM_READINGS; i++) {
    sumValue += analogRead(tempPin);
    // 아두이노는 매우 빠르게 연속 측정이 가능합니다.
  }

  // 2. 평균 아날로그 값 계산 (0 ~ 1023)
  float avgTempValue = (float)sumValue / NUM_READINGS;

  // 3. 전압(mV)으로 변환
  // 아두이노 5V = 5000mV. 해상도: 5000mV / 1024 = 약 4.88mV/bit
  float voltage = avgTempValue * (5000.0 / 1024.0); // 밀리볼트(mV) 단위

  // 4. 섭씨 온도(°C)로 변환
  // LM35는 1°C당 10mV를 출력: Temperature = Voltage(mV) / 10
  float temperatureC = voltage / 10.0; 

  return temperatureC;
}

// 서보 각도 설정 함수
void setServoAngle(int channel, int angle) {
  if (reverseServo[channel]) {
    angle = 180 - angle;
  }
  int pulse = map(angle, 0, 180, SERVOMIN, SERVOMAX);
  pwm.setPWM(channel, 0, pulse);
}

