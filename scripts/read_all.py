import typing
import serial
import threading
import os
import time
import sys
import pygame
from pygame import gfxdraw
import numpy as np
from collections import defaultdict, deque


class StoppableThread(threading.Thread):
  def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self.stop_event = threading.Event()
  def start(self):
    super().start()
    return self
  def stop(self) -> None:
    self.stop_event.set()
  def should_stop(self) -> bool:
    return self.stop_event.is_set()


CapturedType = (
  typing.DefaultDict[
    typing.ByteString, 
    typing.DefaultDict[
      int,
      typing.List[typing.Tuple[int, float]]]])


def seconds_passed() -> float:
  return time.time_ns() / (10 ** 9)


# blocking io
def read_forever(
  port: str,
  port_index: int,
  captured: CapturedType
) -> None:
  ser = serial.Serial(port, baudrate=460800, timeout=1)
  # iota
  current_thread = typing.cast(StoppableThread, threading.current_thread())
  while not current_thread.should_stop():
    mac, strength = ser.readline().split()
    # ignore channel prints
    # only accept valid mac entries
    if len(mac) != 12:
      continue

    captured[mac][port_index].append((int(strength), seconds_passed()))


DrawingQueueType = typing.DefaultDict[
  typing.Tuple[typing.ByteString, int],
  typing.Tuple[typing.List[float], typing.Deque[float]]]


def append_to_drawing_queue(
  captured: CapturedType, drawing_queue: DrawingQueueType,
  animation # 1d array
) -> None:
    for mac, readings in captured.items():
      for port, strengths in readings.items():
        count = 10
        # avoid jerky movements due to reading noise
        average_rssi = sum(
          map(lambda x: x[0], strengths[-count:])) / min(len(strengths), count)
        # convert to something between 0 and 1
        average_rssi = max(0, min(1, (abs(average_rssi) - 70) / 25))

        meta_queue = drawing_queue[(mac, port)]
        queue = meta_queue[1]

        if not len(queue):
          queue.append(average_rssi)

        # this location is already in the drawing queue
        if np.isclose(queue[-1], average_rssi):
          continue
        
        # update the last touched time
        # we expect the drawing time to be 60 frames
        # so only 1 second from now should we start fading
        meta_queue[0][0] = seconds_passed() + 1
        
        start = queue[-1]
        end = average_rssi
        
        # animate from the end of the drawing queue to the new 
        queue += list(start + (end - start) * animation)


def gen_centers(port_count: int) -> typing.List[typing.Tuple[float, float]]:
  assert port_count > 0

  if port_count == 1:
    return [(0.0, 0.0)]

  import random
  offset = random.uniform(0, 2 * np.pi)

  def get_arg(i: int):
    return offset + (2 * np.pi * i) / port_count

  # this converges to a circle as port_count -> inf
  # a circle of radius 1/3
  return [
    (np.cos(get_arg(i)) / 3, np.sin(get_arg(i)) / 3) 
    for i in range(port_count)]


def gen_screen_space_centers(
  screen: pygame.Surface,
  centers: typing.List[typing.Tuple[float, float]]
) -> typing.List[typing.Tuple[int, int]]:
  half_w, half_h = (screen.get_width() // 2, screen.get_height() // 2)

  return [(
      int(half_w + x * half_w),
      int(half_h + y * half_h))
        for x, y in centers]


def draw_from_queue(
  drawing_queue: DrawingQueueType,
  screen: pygame.Surface,
  centers: typing.List[typing.Tuple[int, int]]
) -> None:

  screen.fill('black')

  # (color, radius, circle center)
  to_draw: typing.List[typing.Tuple[
    typing.List[int], int, typing.Tuple[int, int]]] = []
  # some very lazy things are going on here

  max_radius = min(
    screen.get_width(), screen.get_height()) / (2 + (len(centers) != 1))

  for (_, port), (last_written_s, queue) in drawing_queue.items():
    if not queue:
      continue
    
    rssi = queue.popleft() if len(queue) > 1 else queue[0]
    quazi_distance = int(max_radius * rssi)
    
    # determine fading based on how old the entry in the drawing queue is
    distance_fading = 1 - (
        np.tanh((seconds_passed() - last_written_s[-1]) / 10) 
          if len(queue) == 1 else 0)
    # fade based on distance as well
    # the minimum color is before applying fading based on age of a reading
    # because we want to be able to fully black out inactive readings
    # another option would be clearing stale entries, but I did not find
    # it necessary
    min_color = 20
    color = [
      int(distance_fading * (
            min_color + (255 - min_color) * (1 - rssi)))
        for _ in range(3)]

    to_draw.append((color, quazi_distance, centers[port]))

  # draw the brightest things last to avoid artifacts
  # color is the first element in the tuple
  # so lower values get drawn first
  to_draw.sort()
  
  radius = 2
  for color, quazi_distance, center in to_draw:
    # AA shenanigans
    gfxdraw.aacircle(
      screen, 
      *center,
      quazi_distance,
      color) 
    gfxdraw.aacircle(
      screen, 
      *center,
      max(0, quazi_distance - (radius - 1)),
      color) 
    pygame.draw.circle(
      screen, 
      color, 
      center, 
      radius=quazi_distance,
      width=radius)


def display_loop(captured: CapturedType, port_count: int) -> None:
  pygame.init()

  screen = pygame.display.set_mode(
    (1500, 1000), flags=pygame.RESIZABLE, vsync=1)
  clock = pygame.time.Clock()

  normalized_centers = gen_centers(port_count)
  centers = gen_screen_space_centers(screen, normalized_centers)
  
  # (mac, port) -> (last touched, queue of circle radiuses)
  drawing_queue = defaultdict(lambda: ([0.0], deque()))
  animation = np.linspace(0, 1, 60)

  log_frequency = 60 * 5
  log_counter = 1

  while True:
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        pygame.display.quit()
        pygame.quit()
        return
      if event.type == pygame.VIDEORESIZE:
        screen = pygame.display.set_mode(
          (event.w, event.h), flags=pygame.RESIZABLE, vsync=1)
        centers = gen_screen_space_centers(screen, normalized_centers)

    draw_from_queue(drawing_queue, screen, centers)
    append_to_drawing_queue(captured, drawing_queue, animation)

    pygame.display.flip()
    clock.tick(60)
    if log_counter % log_frequency == 0:
      print(f"fps: {clock.get_fps():.2f}")
    log_counter += 1


def main() -> None:
  # not really portable I know
  device_dir = '/dev/'
  ports = [
    os.path.join(device_dir, f) for f in os.listdir(device_dir) 
      if 'cu.usbserial' in f]

  if not ports:
    print("No USB serial connections detected.", file=sys.stderr)
    sys.exit(1)

  print(ports)

  captured = defaultdict(lambda: defaultdict(list))

  threads: typing.List[StoppableThread] = []
  for idx, port in enumerate(ports):
    threads.append(StoppableThread(
      target=read_forever,
      args=(port, idx, captured)
    ).start())

  display_loop(captured, len(ports))

  # kill the other threads once we close the display
  for stop in threads:
    stop.stop()


if __name__ == '__main__':
  sys.exit(main())
