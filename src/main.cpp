#include "DHTesp.h"
#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <HTTPClient.h>

// --- Cấu hình chân ---
const int DHT_PIN = 15;
const int BUZZER_PIN = 27;
const int LDR_PIN = 34;

// --- Cấu hình màn hình OLED ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

DHTesp dht;

// --- Thông tin WiFi ---
const char* ssid = "Wokwi-GUEST";      
const char* password = ""; 

void setup() {
  Serial.begin(115200);
  dht.setup(DHT_PIN, DHTesp::DHT22);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LDR_PIN, INPUT);

  // --- Khởi tạo màn hình OLED ---
  Wire.begin(21, 22);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("Không tìm thấy màn hình OLED!");
    for (;;);
  }

  // --- Hiển thị khởi tạo ---
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("Smart Mirror Booting...");
  display.display();

  // --- Kết nối WiFi ---
  WiFi.begin(ssid, password);
  display.println("Connecting WiFi...");
  display.display();

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("WiFi Connected!");
  display.print("IP: ");
  display.println(WiFi.localIP());
  display.display();
  delay(2000);
}

void loop() {
  // --- Đọc dữ liệu cảm biến ---
  TempAndHumidity data = dht.getTempAndHumidity();
  int lightValue = analogRead(LDR_PIN);
  float brightness = map(lightValue, 0, 4095, 0, 100);
  // --- Giả lập dữ liệu bụi mịn ---
  float pm25 = random(10, 80);
  float pm10 = random(20, 150);

  // --- In ra Serial ---
  Serial.println("testtttttttt");
  Serial.println("-----");
  Serial.printf("Nhiet do: %.2f °C\n", data.temperature);
  Serial.printf("Do am: %.2f %%\n", data.humidity);
  Serial.printf("Anh sang: %.0f %%\n", brightness);
  Serial.printf("PM2.5: %.2f µg/m³\n", pm25);
  Serial.printf("PM10: %.2f µg/m³\n", pm10);

  // --- Hiển thị lên OLED ---
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Temp: ");
  display.print(data.temperature, 1);
  display.println(" C");

  display.print("Humi: ");
  display.print(data.humidity, 1);
  display.println(" %");

  display.print("Light: ");
  display.print(brightness, 0);
  display.println(" %");

  display.print("PM2.5: ");
  display.print(pm25, 0);
  display.println(" ug/m3");

  display.print("PM10 : ");
  display.print(pm10, 0);
  display.println(" ug/m3");

  // --- Kiểm tra ngưỡng cảnh báo ---
  bool alert = false;
  String alertMsg = "";

  if (data.temperature > 30) {
    alert = true;
    alertMsg = "Nhiet do cao!";
  } else if (pm25 > 30) {
    alert = true;
    alertMsg = "PM2.5 cao!";
  } else if (pm10 > 100) {
    alert = true;
    alertMsg = "PM10 cao!";
  } else if (brightness < 20) {
    alert = true;
    alertMsg = "Anh sang thap!";
  }

  display.setCursor(0, 50);
  if (alert) {
    display.print("Canh bao: ");
    display.println(alertMsg);
    tone(BUZZER_PIN, 1000);
    delay(500);
    noTone(BUZZER_PIN);
  } else {
    display.println("Trang thai: OK");
  }

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin("http://10.144.210.159:5000/update");  // ⚠️ Đổi IP tại đây!
    http.addHeader("Content-Type", "application/json");

    String json = "{\"temperature\": " + String(data.temperature, 2) +
                  ", \"humidity\": " + String(data.humidity, 2) +
                  ", \"light\": " + String(brightness, 2) +
                  ", \"pm25\": " + String(pm25, 2) +
                  ", \"pm10\": " + String(pm10, 2) + "}";

    int code = http.POST(json);
    if (code > 0) {
      Serial.printf("Sent data: %s\n", json.c_str());
      Serial.println(http.getString());
    } else {
      Serial.printf("HTTP POST failed, code: %d\n", code);
    }
    http.end();
  }

  display.display();
  delay(3000);
}
