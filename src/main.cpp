#include <sniff/packet_sniffer.hpp>

void setup() {
  ::Serial.begin(460800);
  while (!::Serial) {}

  sniff::packet_sniffer::setup();
}

void loop() {
  // allow background microcontroller work to progress
  ::yield();
}
