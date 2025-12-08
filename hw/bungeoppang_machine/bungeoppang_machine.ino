#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// --- I. 릴레이 및 푸시 버튼 정의 ---
const int buttonPin = 3;   // 푸시 버튼 입력 (D3) - 비상 스위치 역할
const int systemPowerRelayPin = 4;    // 릴레이 제어 출력 (D4)

// 래치 상태 변수: true = 릴레이 ON (시스템 구동), false = 릴레이 OFF (전원 차단)
volatile bool systemState = true; 

// 디바운스 변수
long lastDebounceTime = 0;
long debounceDelay = 200; 
int buttonState;
int lastButtonState = HIGH; 

// --- II. 서보 모터 정의 (PCA9685) ---
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVOMIN  102    // 0도 펄스
#define SERVOMAX  512    // 180도 펄스
int servo0 = 0; // 세트 1 - 첫 번째 서보
int servo1 = 1; // 세트 1 - 두 번째 서보
int servo2 = 2; // 세트 2 - 첫 번째 서보
int servo3 = 3; // 세트 2 - 두 번째 서보
bool reverseServo[4] = {false, false, false, false};

// --- III. LM35 온도 센서 정의 ---
const int tempPin = A0; // LM35 출력(Vout)을 아날로그 핀 A0에 연결

// --- IV. 부저 및 경고 LED 정의 ---
const int buzzerPin = 8;        // 부저 제어 핀 (D8)
const int sensorErrorLedPin = 9;
const float SET_TEMP = 50.0;    // 경고 임계 온도 (섭씨 40도)

// --- V. 상태 표시 LED 정의 (D11, D12, D13) ---
const int status_led_IDLE_Pin = 11; // 준비 상태 (Ready)
const int status_led_RUNNING_Pin = 12; // 작동 중 (Working)
const int status_led_DONE_Pin = 13; // 작동 완료/일시 정지 (Complete/Pause)

// --- VI. 작동 관련 변수 (전역) ---
int totalCount = 5;     // GUI에서 입력받을 총 개수 (테스트를 위해 3으로 초기 설정)
int currentCount = 0;   // 현재까지 완료된 작업 개수 (세트 1 기준)
bool jobStarted = false; // 작업 시작 플래그
bool jobComplete = false; // 전체 작업 완료 플래그

// **타이머 변수 전역화**
long readyTime = 0;         // 5초 대기 시작 시간
bool waitingForJob = true;  // 초기 구동 및 복귀 시 5초 대기를 시작할 준비가 되었는지 표시
unsigned long moveStartTime = 0; // 서보 시퀀스 타이머
int stage = 0;                  // 서보 시퀀스 단계

// --- 3. 사용자 정의 함수 (선언 위치 이동) ---

// 서보 각도 설정 함수
void setServoAngle(int channel, int angle) {
  if (reverseServo[channel]) {
    angle = 180 - angle;
  }
  int pulse = map(angle, 0, 180, SERVOMIN, SERVOMAX);
  pwm.setPWM(channel, 0, pulse);
}

// LM35 값을 섭씨 온도로 변환하는 함수 (노이즈 완화를 위해 20회 평균값 사용)
float getTemperatureC() {
  const int NUM_READINGS = 20; 
  long sumValue = 0;           

  for (int i = 0; i < NUM_READINGS; i++) {
    sumValue += analogRead(tempPin);
  }

  float avgTempValue = (float)sumValue / NUM_READINGS;
  float voltage = avgTempValue * (5000.0 / 1024.0); // 밀리볼트(mV) 단위
  float temperatureC = voltage / 10.0; 

  return temperatureC;
}

// 상태 표시 LED 업데이트 함수
// mode: 0=All OFF, 1=준비(11 ON), 2=작동 중(12 ON), 3=작동 완료(13 ON)
void updateStatusLED(int mode) {
    digitalWrite(status_led_IDLE_Pin, LOW); 
    digitalWrite(status_led_RUNNING_Pin, LOW); 
    digitalWrite(status_led_DONE_Pin, LOW); 

    if (mode == 1) { // 준비 상태
        digitalWrite(status_led_IDLE_Pin, HIGH);
    } else if (mode == 2) { // 작동 중
        digitalWrite(status_led_RUNNING_Pin, HIGH);
    } else if (mode == 3) { // 작동 완료/일시 정지
        digitalWrite(status_led_DONE_Pin, HIGH);
    }
}

// 1. 서보 모터 반복 작동 시퀀스 함수 (논블로킹 로직 사용)
void conditionalMovement() {
    updateStatusLED(2); // LED: 작동 중 (Working)

    // 세트 1이 담당할 총 사이클 횟수 (총 개수/2 올림. 예: 3개 주문이면 (3+1)/2 = 2 사이클)
    int requiredCycles = (totalCount + 1) / 2;
    
    // 세트 2 동작 여부: 현재 사이클(currentCount + 1)이 전체 주문 개수(totalCount)의 짝수 번째에 해당할 경우
    bool shouldSet2Run = (currentCount + 1) * 2 <= totalCount;
    
    // --- A. 세트 1 (Servo 0, 1) 동작 시퀀스 ---
    if (currentCount < requiredCycles) {
        
        switch (stage) {
            case 0: // 초기 대기
                if (millis() - moveStartTime > 1000) { 
                    Serial.print("Starting Cycle ");
                    Serial.print(currentCount + 1);
                    Serial.print("/");
                    Serial.print(requiredCycles);
                    Serial.println(" - Stage 1 (Servo 0 to 90)");
                    stage = 1;
                }
                break;
                
            case 1: // Servo 0: 90도 이동 (동시 작업 시작)
                setServoAngle(servo0, 90);
                moveStartTime = millis(); 
                
                // ** [핵심 변경: 병렬 작업 시작] **
                if (shouldSet2Run) {
                    // 세트 2의 첫 서보(Servo 2)도 거의 동시에 90도로 움직이도록 명령
                    setServoAngle(servo2, 90); 
                    Serial.println("Set 1 (Servo 0) and Set 2 (Servo 2) started simultaneously.");
                    stage = 2; // 다음 단계: 4초 대기 (S0/S2 동작 시간)
                } else {
                    stage = 2; // 다음 단계: 4초 대기 (S0 동작 시간)
                }
                break;
                
            case 2: // S0, S2: **4초 대기** 후 0도 복귀 (움직임->복귀 시간 변경 적용)
                if (millis() - moveStartTime >= 4000) {
                    setServoAngle(servo0, 0);
                    
                    if (shouldSet2Run) { 
                         setServoAngle(servo2, 0); 
                         Serial.println("Set 1 (S0) and Set 2 (S2) completed 4s movements.");
                    } else {
                         Serial.println("Servo 0 completed. Starting 6s wait for Servo 1...");
                    }
                    
                    moveStartTime = millis(); // 6초 카운트 시작
                    stage = 3; 
                }
                break;
                
            case 3: // S1, S3: **3초 대기** 후 60도, 80 이동 (다음 서보 대기 시간 변경 적용)
                if (millis() - moveStartTime >= 3000) {
                    setServoAngle(servo1, 60);
                    
                    if (shouldSet2Run) { 
                        setServoAngle(servo3, 80);
                        Serial.println("Set 1 (S1) and Set 2 (S3) moved 90 degrees after 6s wait.");
                    } else {
                        Serial.println("Servo 1 moved 90 degrees.");
                    }
                    
                    moveStartTime = millis(); // 4초 카운트 시작
                    stage = 4; 
                }
                break;
                
            case 4: // S1, S3: **4초 대기** 후 0도 복귀 및 사이클 완료 처리 (움직임->복귀 시간 변경 적용)
                if (millis() - moveStartTime >= 1000) {
                    setServoAngle(servo1, 0);
                    
                    if (shouldSet2Run) { 
                         setServoAngle(servo3, 0); 
                         currentCount++; // 세트 1 + 세트 2 완료로 1 사이클 완료 (2개 완성)
                         Serial.print("Cycle ");
                         Serial.print(currentCount);
                         Serial.println(" (Set 1 & 2) [2 Units] completed.");
                    } else {
                        currentCount++; // 세트 1만 완료로 1개 완성
                        Serial.print("Set 1 Cycle ");
                        Serial.print(currentCount);
                        Serial.println(" [1 Unit] completed.");
                    }
                    
                    moveStartTime = millis();
                    
                    if (currentCount == requiredCycles) {
                       stage = 9; // 최종 완료
                    } else {
                       stage = 0; // 다음 사이클 반복 대기 (개별 독립성)
                    }
                }
                delay(2000);
                break;
        }
    } 
    
    // --- B. 최종 완료 단계 ---
    else { // currentCount == requiredCycles
        switch (stage) {
            case 9: // 최종 완료 단계: 3초 완료 LED 표시 -> 대기 모드 복귀
                updateStatusLED(3); // LED: 작동 완료 (Complete/Pause)
                Serial.println("!!! ALL JOB SEQUENCE COMPLETE !!!");

                // 3초 후 대기 모드(준비 상태)로 전환
                if (millis() - moveStartTime >= 3000) {
                    jobStarted = false; 
                    jobComplete = false; 
                    currentCount = 0; 
                    
                    waitingForJob = true; // 다음 5초 대기를 위해 플래그 활성화
                    stage = 0; // 스테이지 초기화
                    moveStartTime = millis(); // 타이머 갱신
                    updateStatusLED(1); // LED: 준비 상태 (Ready)
                }
                break;
        }
    }
}


// --- 1. SETUP 함수 ---
void setup() {
  Serial.begin(9600);
  Serial.println("System Initializing...");
  
  // 릴레이 및 버튼 핀 설정
  pinMode(systemPowerRelayPin, OUTPUT);
  pinMode(buttonPin, INPUT_PULLUP); // 버튼은 GND에 연결되어 있으므로 내부 풀업 사용

  // 부저 및 경고 LED 핀 설정
  pinMode(buzzerPin, OUTPUT);
  digitalWrite(buzzerPin, LOW); 
  pinMode(sensorErrorLedPin, OUTPUT);
  digitalWrite(sensorErrorLedPin, LOW); 

  // 상태 표시 LED 핀 설정 (추가)
  pinMode(status_led_IDLE_Pin, OUTPUT); // 준비
  pinMode(status_led_RUNNING_Pin, OUTPUT); // 작동 중
  pinMode(status_led_DONE_Pin, OUTPUT); // 완료/대기

  // PCA9685 초기화
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);
  
  // 초기 상태: 릴레이 ON (시스템 구동 시작), 준비 상태 LED ON
  digitalWrite(systemPowerRelayPin, LOW); // 릴레이 코일 OFF (NC 연결)
  updateStatusLED(1); // 초기: 준비 상태 LED ON
  
  // 초기 서보 위치 설정 (0도)
  setServoAngle(servo0, 0);
  setServoAngle(servo1, 0);
  setServoAngle(servo2, 0);
  setServoAngle(servo3, 0);
  delay(1000);

  // 다음 5초 대기 로직이 작동하도록 플래그를 활성화합니다.
  waitingForJob = true;

  Serial.println("Initial Latch ON. System Ready. Waiting for job start (5 sec initial delay).");
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
        systemState = !systemState;
      }
    }
  }
  lastButtonState = reading;
  
// --- 2-2. RELAY CONTROL (D4) ---
if (!systemState) {
  // 릴레이 OFF (비상 전원 차단) -> 모터 정지를 위해 릴레이 코일은 켜져야 NC 차단
  digitalWrite(systemPowerRelayPin, HIGH); 
  
  // *** 비상 차단 시 서보 펄스 끄기 로직 (안정성 강화) ***
  pwm.setPWM(servo0, 0, 0); 
  pwm.setPWM(servo1, 0, 0);
  pwm.setPWM(servo2, 0, 0);
  pwm.setPWM(servo3, 0, 0);
  
  // 모든 작업 상태 초기화 및 LED OFF
  updateStatusLED(0); // 모든 LED OFF
  jobStarted = false;
  jobComplete = false;
  currentCount = 0;
  waitingForJob = true; // 다음 구동 시 5초 대기를 위해 플래그 활성화
  readyTime = 0;
  stage = 0;
  moveStartTime = 0;

  Serial.println("EMERGENCY LATCH ENGAGED: System OFF (Relay HIGH, Servo Pulses OFF).");
  delay(500); 
  return; // 나머지 loop 로직은 실행하지 않음
  
} else {
  // 릴레이 ON (시스템 구동 시작) -> 모터 구동을 위해 릴레이 코일은 꺼져야 NC 연결
  digitalWrite(systemPowerRelayPin, LOW); 
}

  // --- 2-3. CONDITIONAL MOVEMENT & SENSOR CHECK ---
  if (systemState) {
    // 릴레이가 ON일 때만 실행

    // 1초마다 온도 측정 및 경고 로직
    static long lastTempCheckTime = 0; 
    if (millis() - lastTempCheckTime > 1000) { 
      
      float currentTemp = getTemperatureC();
      Serial.print("Current Temperature: ");
      Serial.print(currentTemp);
      Serial.println(" C");

      if (currentTemp > SET_TEMP) {
        digitalWrite(buzzerPin, HIGH);
        digitalWrite(sensorErrorLedPin, HIGH);
        Serial.println("!!! OVERHEAT WARNING: BUZZER ON !!!");
      } else {
        digitalWrite(buzzerPin, LOW);
        digitalWrite(sensorErrorLedPin, LOW);
      }
      lastTempCheckTime = millis();
    }

    // 작업 시작 로직 (시스템 켜진 후 5초 뒤에 자동으로 시작)
    if (!jobStarted && !jobComplete) {
      
      if (waitingForJob) {
          readyTime = millis(); // 대기 상태 진입 시 현재 시간으로 타이머를 명시적 시작 (단 1회)
          waitingForJob = false; // 플래그를 false로 전환하여 다시 설정되지 않게 막음
          Serial.println("Job wait timer started.");
      }

      updateStatusLED(1); // 준비 상태 LED ON
      
      if(millis() - readyTime >= 5000) { // 5초 대기 조건 충족
          jobStarted = true;
          // waitingForJob은 jobComplete 후 다시 true로 설정됨
          currentCount = 0;
          Serial.println("Job Sequence Starting after 5 sec delay.");
      }
    }

    // 작업 실행 로직
    if (jobStarted && !jobComplete) {
      conditionalMovement(); // 서보 모터 작동 시퀀스 실행
    }
  }
}