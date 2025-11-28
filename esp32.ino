#include <driver/i2s.h>
#include <WiFi.h>
#include <ArduinoWebsockets.h>
#include <Wire.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
//#include "USB.h"
//#include "USBCDC.h"
#include <GyverOLED.h>
//USBCDC USBSerial;
//GyverOLED<SSD1306_128x32> oled;
GyverOLED<SSD1306_128x32, OLED_NO_BUFFER> oled;

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 32
#define OLED_RESET -1

#define I2C_SDA 21//10//21//5
#define I2C_SCL 22//11//22//6

#define I2S_SD 33//7//33//33//33//9
#define I2S_WS 26//8//26//32//32//8
#define I2S_SCK 25//9//25//25//25//7
#define I2S_PORT I2S_NUM_0
#define VIBRO_PIN 18//1//18//26

#define ANALOG_PIN 10 

#define bufferCnt 16 //5
#define bufferLen 1024 //1024
int16_t sBuffer[1024]; //bufferLen

const char* ssid = "TP-Link_B3DC";//"TP-Link_B3DC";//"TP-Link_B3DC";
const char* password = "56148916";//"56148916";

const char* websocket_server_host = "192.168.0.15";//"10.150.149.17";//"192.168.0.129";
const uint16_t websocket_server_port = 8888;  // <WEBSOCKET_SERVER_PORT>

using namespace websockets;
WebsocketsClient client;
bool isWebSocketConnected;
bool active = false;

const String words[9] = {"типа", "типы", "типу", "ну", "короче", "в общем", "как бы", "так сказать", "вот"};
const int words_len = 9;

bool isBad(String word){
  for (int i = 0; i < words_len; i++){
    if (words[i] == word)
      return true;
  }
  return false;
}

void onMessageCallback(WebsocketsMessage message) {
  Serial.print("Got Message: ");
  Serial.println(message.data());
  //oled.print(message.data());
  //oled.update();
  String str = message.data();
  if(isBad(str)){
    digitalWrite(VIBRO_PIN, HIGH);
    oled.clear();
    oled.update();
    oled.home();
    oled.print(str);
    oled.update();
    unsigned long startTime = millis();
    while (millis() - startTime < 1000) {
      client.poll();
    }
    digitalWrite(VIBRO_PIN, LOW);
    //oled.setScale(1.5);
    //oled.print("(0_0)");
    //oled.update();

  }
  
}

void onEventsCallback(WebsocketsEvent event, String data) {
  if (event == WebsocketsEvent::ConnectionOpened) {
    Serial.println("Connnection Opened");
    isWebSocketConnected = true;
  } else if (event == WebsocketsEvent::ConnectionClosed) {
    Serial.println("Connnection Closed");
    isWebSocketConnected = false;
  } else if (event == WebsocketsEvent::GotPing) {
    Serial.println("Got a Ping!");
  } else if (event == WebsocketsEvent::GotPong) {
    Serial.println("Got a Pong!");
  } 
}

void i2s_install() {
  const i2s_config_t i2s_config = {
    .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = 44100,
    //.sample_rate = 16000,
    .bits_per_sample = i2s_bits_per_sample_t(16),
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),//i2s_comm_format_t(
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = bufferCnt,
    .dma_buf_len = bufferLen,
    .use_apll = true
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
}

void i2s_setpin() {
  const i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD
  };

  i2s_set_pin(I2S_PORT, &pin_config);
}
void micTask();
void setup() {
  Serial.begin(115200);
  
  pinMode(VIBRO_PIN, OUTPUT);
  
  Wire.begin(I2C_SDA, I2C_SCL);
  oled.init();
  
  
  oled.clear();
  oled.update();
  oled.setScale(2);
  oled.home();        // курсор в 0,0
  oled.print("(0_0)");
  oled.update();
  
  connectWiFi();
  connectWSServer();
  client.poll();

  micTask();
  //xTaskCreatePinnedToCore(micTask, "micTask", 10000, NULL, 1, NULL, 1);
  //xTaskCreatePinnedToCore(serialTask, "serialTask", 4096, NULL, 1, NULL, 1);
}

void loop() {
client.onMessage(onMessageCallback);
//if (!isWebSocketConnected)
//  connectWSServer();
//client.onEvent(onEventsCallback);
}

void connectWiFi() {
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
}

void connectWSServer() {
  client.onMessage(onMessageCallback);
  client.onEvent(onEventsCallback);
  while (!client.connect(websocket_server_host, websocket_server_port, "/")) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("Websocket Connected!");
}

void micTask() {
  
  delay(1000);

  i2s_install();
  i2s_setpin();
  i2s_start(I2S_PORT);

   ////////////////////////

  int counter = 0;
  const int pollInterval = 5;
  size_t bytesIn = 0;
  while (1) {
    esp_err_t result = i2s_read(I2S_PORT, &sBuffer, bufferLen, &bytesIn, portMAX_DELAY);
    
    if (result == ESP_OK && isWebSocketConnected) {
      
      client.sendBinary((const char*)sBuffer, bytesIn);
      client.poll();
      /*
      counter++;
      if (counter >= pollInterval){
        client.poll();
      }
      */
    }
  }
}



