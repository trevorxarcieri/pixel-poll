import time

from encoder.rotary_irq_rp2 import RotaryIRQ

r = RotaryIRQ(clk_pin="GP2", dt_pin="GP3", pull_up=True)

val_old = r.value()
while True:
    val_new = r.value()

    if val_old != val_new:
        val_old = val_new
        print('result =', val_new)

    time.sleep_ms(50)
