# Button

Use `zbot.button(id)` to read a button. Button IDs start at `1` in student code.

```python
async def main(zbot):
    import uasyncio as asyncio

    button = zbot.button(1)

    try:
        zbot.forward(25)

        while True:
            # pressed() is True for as long as the button is held down.
            if button.pressed():
                zbot.display("Button 1", "pressed")
                zbot.stop()
                break

            await asyncio.sleep_ms(20)

    finally:
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
async def main(zbot):
    import uasyncio as asyncio

    button = zbot.button(1)

    while True:
        # was_pressed() is an edge event. It returns True once per press,
        # which makes it better than pressed() for counters and toggles.
        if button.was_pressed():
            zbot.notify("Pressed {}".format(button.presses()))

        await asyncio.sleep_ms(20)
```
