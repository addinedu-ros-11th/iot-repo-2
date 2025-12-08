/*
 * RFID RC522 카드 리더 아두이노 코드
 * 
 * 하드웨어:
 *  - Arduino Uno/Nano
 *  - MFRC522 RFID 모듈 (RC522)
 *  
 * 연결:
 *  RC522 -> Arduino
 *  SDA   -> D10
 *  SCK   -> D13
 *  MOSI  -> D11
 *  MISO  -> D12
 *  IRQ   -> (연결 안함)
 *  GND   -> GND
 *  RST   -> D9
 *  3.3V  -> 3.3V
 */

#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN         9
#define SS_PIN          10

MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
}

void loop() {
  // 새 카드가 있는지 확인
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  // 카드 읽기
  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  // UID를 16진수 문자열로 변환
  String cardUID = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) {
      cardUID += "0";
    }
    cardUID += String(mfrc522.uid.uidByte[i], HEX);
  }
  cardUID.toUpperCase();

  // 시리얼로 전송
  Serial.print(">>> 전송: RFID:");
  Serial.println(cardUID);

  // 카드 읽기 종료
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  delay(1000);
}
