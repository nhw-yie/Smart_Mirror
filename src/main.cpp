// --- Simulation / ESP-SR demo ---
// audio file to play from SPIFFS. We will convert hiesp.mp3 -> hiesp.raw (16-bit LE PCM mono)
const char* kAudioPath = "/hiesp.raw"; // upload to SPIFFS via pio uploadfs
// Do not auto-play on boot; button will trigger playback
bool _sim_play_once = false;
const float kRmsThreshold = 800.0; // điều chỉnh tuỳ file (kept for RMS demo)
const int kConsecutiveThreshold = 3;

// --- Button configuration ---
const int BUTTON_PIN = 32; // GPIO32 (input)
const unsigned long DEBOUNCE_MS = 50;
bool lastButtonState = true; // assuming pull-up (true == HIGH)
unsigned long lastDebounceTime = 0;
bool buttonState = true; // stable state (true == not pressed with INPUT_PULLUP)

// --- Existing code continues here ---
#include "DHTesp.h"
#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <HTTPClient.h>
#include "SPIFFS.h"

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
  // Button: use internal pull-up so button connects to GND when pressed
  pinMode(BUTTON_PIN, INPUT_PULLUP);

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

  // Mount SPIFFS early so file presence is known
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS mount failed in setup");
  } else {
    Serial.println("SPIFFS mounted");
  }
}

// gọi khi wakeword được "phát hiện"
void on_wakeword_detected() {
  Serial.println("Wakeword detected: Hi ESP");
  // Hiển thị trên OLED
  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(0, 10);
  display.println("Wakeword:");
  display.println("Hi ESP");
  display.display();

  // Buzz ngắn
  tone(BUZZER_PIN, 2000);
  delay(300);
  noTone(BUZZER_PIN);

  // quay lại màn hình bình thường sau 1s
  delay(1000);
}

// tính RMS của mẫu int16
float compute_rms(const int16_t* samples, size_t count) {
  long acc = 0;
  for (size_t i = 0; i < count; ++i) {
    long v = samples[i];
    acc += v * v;
  }
  if (count == 0) return 0;
  return sqrt((float)acc / (float)count);
}

// đọc file âm thanh (16-bit LE PCM mono) từ SPIFFS và "feed" từng chunk
void play_audio_file_from_spiffs(const char* path, unsigned int chunkSamples = 160, unsigned int pauseMs = 20) {
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS mount failed");
    return;
  }
  File f = SPIFFS.open(path, FILE_READ);
  if (!f) {
    Serial.printf("Audio file not found: %s\n", path);
    return;
  }

  const size_t chunkBytes = chunkSamples * 2; // 16-bit
  uint8_t buf[512];
  int consecutive_high = 0;

  while (f.available()) {
    size_t toRead = min(sizeof(buf), chunkBytes);
    size_t r = f.read(buf, toRead);
    size_t samples = r / 2;
    static int16_t sarr[256]; // đủ cho chunkSamples <= 256
    if (samples > sizeof(sarr)/sizeof(sarr[0])) samples = sizeof(sarr)/sizeof(sarr[0]);
    for (size_t i = 0; i < samples; ++i) {
      sarr[i] = (int16_t)((buf[2*i+1] << 8) | (buf[2*i] & 0xFF));
    }

    float rms = compute_rms(sarr, samples);
    Serial.printf("chunk samples=%u rms=%.1f\n", (unsigned)samples, rms);

    if (rms > kRmsThreshold) {
      consecutive_high++;
      if (consecutive_high >= kConsecutiveThreshold) {
        on_wakeword_detected();
        break; // chỉ demo 1 lần
      }
    } else {
      consecutive_high = 0;
    }

    delay(pauseMs);
  }

  f.close();
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

  // --- Button handling (debounce) ---
  int reading = digitalRead(BUTTON_PIN);
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > DEBOUNCE_MS) {
    // If the reading has been stable and is different from the current stable state
    if (reading != buttonState) {
      buttonState = reading;
      // active low button pressed
      if (buttonState == LOW) {
        Serial.println("Button pressed: starting playback...");
        play_audio_file_from_spiffs(kAudioPath, 160, 20);
        Serial.println("Playback finished.");
      }
    }
  }
  lastButtonState = reading;

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin("http://172.17.33.191:5000/update");  // Đổi IP tại đây!
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
  delay(180000);
  //delay(3000);
}
