#!/usr/bin/env bash

pio run --target upload && \
  clear && \
  pio device monitor -f esp8266_exception_decoder -b 460800
