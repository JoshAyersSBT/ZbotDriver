# Sensors

ZebraBot exposes sensors through the global `zbot` object. Plug a sensor into one
of the six sensor ports, then read it by port number from student code.

The most common sensor helpers are:

```python
distance = zbot.tof(1)
color = zbot.color(2)
rgb = zbot.rgb(2)
```

Sensor topics:

- [Sensor ports](sensor-ports.md)
- [Distance sensor](distance-sensor.md)
- [Color sensor](color-sensor.md)
- [Full sensor snapshot](sensor-snapshot.md)
- [Sensor notes](sensor-notes.md)
