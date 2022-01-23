#include <sniff/packet_sniffer.hpp>

#include <Ticker.h>
#include <ESP8266WiFi.h>

namespace sniff {

#define DEFINE_STATIC(member) \
  decltype(member) member

  DEFINE_STATIC(packet_sniffer::ticker);
  DEFINE_STATIC(packet_sniffer::current_channel) = 1;

  void packet_sniffer::setup() {
    packet_sniffer::setup_sniffing();
    packet_sniffer::ticker.attach(0.33f, &packet_sniffer::rotate_channel);
  }


  void packet_sniffer::setup_sniffing() {
    ::wifi_set_opmode(STATION_MODE);
    ::wifi_promiscuous_enable(0);

    ::wifi_set_promiscuous_rx_cb(promiscuous_callback);

    ::wifi_promiscuous_enable(1);
    ::wifi_set_channel(current_channel);
  }

  void packet_sniffer::rotate_channel() {
    // 1, 6, 11, the non-overlapping bands
    current_channel = (current_channel + 5) % 15;
    ::wifi_set_channel(current_channel);
    ::Serial.printf("chan %2d\n", current_channel);

    // the blue led on the esp8266
    auto constexpr led_pin = 2;
    auto const static init_guard = []{ 
      ::pinMode(led_pin, OUTPUT);
      return false;
    }();

    if (current_channel == 1) {
      // 0 is on, 1 is off
      ::digitalWrite(led_pin, 0);
      ::delay(1);
      ::digitalWrite(led_pin, 1);
    }
  }

  void packet_sniffer::promiscuous_callback(
    ::std::uint8_t* buf,
    ::std::uint16_t len
  ) {
    // data frames we are interested in
    // 0x88: Data frame - QoS Data
    // 0x40: Probe Request frame
    // 0x94: Block Ack Request frame
    // 0xa4: Data frame - Null function (No data)
    // 0xb4: Data frame - QoS Null function (No data)
    // 0x08: Data frame - Data
    if ((buf[12] == 0x88) || (buf[12] == 0x40) || (buf[12] == 0x94) ||
        (buf[12] == 0xa4) || (buf[12] == 0xb4) || (buf[12] == 0x08)) {
      for (auto i = 0; i < 6; ++i) {
        ::Serial.printf("%02X", buf[22 + i]);
      }
      ::Serial.printf(" %3d\n", static_cast<int8_t>(buf[0]));
    }
  }

}
