import machine, time

led = machine.Pin("LED", machine.Pin.OUT)  # onboard LED = GP25

while True:
    led.toggle()
    time.sleep(0.5)  # 500 ms
