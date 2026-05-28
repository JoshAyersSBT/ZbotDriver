# Button

Use `zbot.button(id)` to read a button. Button IDs start at `1` in student code.

```python
button = zbot.button(1)

if button.pressed():
    zbot.stop()
```

Button wrapper methods:

- `read()`: return `True` when pressed, otherwise `False`
- `value()`: alias for `read()`
- `pressed()`: return `True` while held down
- `released()`: return `True` while not held down
- `was_pressed()`: return `True` once after a press event
- `was_released()`: return `True` once after a release event
- `presses(reset=False)`: return the press count
- `releases(reset=False)`: return the release count
- `snapshot()`: return the full button status dictionary

Example press counter:

```python
button = zbot.button(1)

if button.was_pressed():
    zbot.notify("Pressed {}".format(button.presses()))
```
