# ESP8266 realtime WiFi frame visualization

Realtime display using naive distance calculations, and smooth animations.
Supports unlimited number of `esp8266`s connected using a serial connections.

## Building and running

Dependencies:
 * `platformio` CLI, e.g. `pio`

With a compatible `esp8266` connected using a serial connection, run `monitor.sh`.
This will compile, upload and monitor the serial connection.

Running `python read_all.py` will ingest the data from serial, and display it in a pygame window.

## Example

https://github.com/yatsukha/esp8266-triangulation/assets/33135465/180cfa7e-7d4c-40ae-af7b-9e675d37977e
