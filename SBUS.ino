#include "sbus.h" 

// 
// const int potPin = 34;      // 电位器模拟信号输入引脚

// 
bfs::SbusTx sbus(&Serial2, 16, 17, true);

// 
uint16_t userChannels[16];

void setup() {
  Serial.begin(115200);

  // 
  Serial2.begin(100000, SERIAL_8E2, 16, 17, true);
  
  // 
  Serial2.begin(100000);

  // 
  for (int i = 0; i < 16; i++) {
    userChannels[i] = 1500;
  }

  // 
  userChannels[0] = 1500;   // CH1: 转向 中位
  userChannels[1] = 1500;   // CH2: 升降 中位
  userChannels[2] = 1000;
  userChannels[4] = 1500;   // CH5: 微调1
  userChannels[5] = 1500;   // CH6: 微调2
  userChannels[7] = 1800;   // CH8: 油门锁 

  
}

void loop() {
  // read input
  if (Serial.available()) {
   
    String command = Serial.readStringUntil('\n'); 
    command.trim();
    
    
    if (command.startsWith("<") && command.endsWith(">")) {
      
      String data = command.substring(1, command.length() - 1); 
      
      int commaIndex = 0;
      int startIndex = 0;
      int idx = 0; 
      int targetChannels[] = {0, 1, 2, 4, 5, 7}; 
      
     
      while ((commaIndex = data.indexOf(',', startIndex)) != -1 && idx < 5) {
        int val = data.substring(startIndex, commaIndex).toInt();
        userChannels[targetChannels[idx]] = constrain(val, 1000, 2000);
        startIndex = commaIndex + 1;
        idx++;
      }
      if (idx <= 5 && startIndex < data.length()) {
        int val = data.substring(startIndex).toInt();
        userChannels[targetChannels[idx]] = constrain(val, 1000, 2000);
      }

      ///show value

      Serial.print("turning(CH1):"); Serial.print(userChannels[0]);
      Serial.print('\n');
      Serial.print("liftandlower(CH2):"); Serial.print(userChannels[1]);
      Serial.print('\n');
      Serial.print("trottle(CH3):"); Serial.print(userChannels[2]);
      Serial.print('\n');
      Serial.print("finetune1(CH5):"); Serial.print(userChannels[4]);
      Serial.print('\n');
      Serial.print("finetune2(CH6):"); Serial.print(userChannels[5]);
      Serial.print('\n');
      Serial.print("trottle locker(CH8):"); Serial.println(userChannels[7]);
      Serial.print('\n');
      Serial.print('\n');
    }
  }

  // 读取电位器
  // int potRaw = analogRead(potPin);                 
  // int throttle = map(potRaw, 0, 4095, 1000, 2000); 
  // userChannels[2] = constrain(throttle, 1000, 2000); 

  //  发送 SBUS 信号 
  // 
  bfs::SbusData sbusData;
  
  
  for (int i = 0; i < 16; i++) {
    sbusData.ch[i] = userChannels[i];
  }
  
  
  sbusData.lost_frame = false;
  sbusData.failsafe = false;
  sbusData.ch17 = false;
  sbusData.ch18 = false;

  
  sbus.data(sbusData); 
  sbus.Write();

  // show value
  // static unsigned long lastPrintTime = 0;
  // if (millis() - lastPrintTime >= 100) { 
    
  //   lastPrintTime = millis();
  // }
  
  delay(14); 
}