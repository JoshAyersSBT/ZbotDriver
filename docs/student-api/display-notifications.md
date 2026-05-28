# Display And Notifications

Show text on the OLED:

```python
zbot.display("Line 1", "Line 2", "Line 3", "Line 4")
```

`zbot.say()` is an alias for `zbot.display()`.

Send a message over the active telemetry link:

```python
zbot.notify("Hello from user code")
```

`display()` returns `True` when the OLED is available. `notify()` returns `True`
when a telemetry connection is available.
