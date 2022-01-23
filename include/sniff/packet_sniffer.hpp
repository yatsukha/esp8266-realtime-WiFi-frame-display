#pragma once

#include <Ticker.h>

namespace sniff {

  class packet_sniffer {
    ::Ticker static ticker;
    uint32_t static current_channel;

    static void setup_sniffing();
    static void rotate_channel();
    static void promiscuous_callback(uint8_t*, uint16_t);
   public:
    static void setup();
  };

}
