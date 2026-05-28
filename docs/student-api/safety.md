# Safety

Always stop motors when your program exits or hits an error condition.

```python
try:
    zbot.forward(40)
    # your loop here
finally:
    zbot.stop()
```

This makes user code much friendlier during testing.
