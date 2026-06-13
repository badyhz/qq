# Cancel Safety Simulation Report

Total records: 6
All simulated: True
All no real cancel: True

## Records

- CXL_182a5b2da040: order=ORD_001, valid=True, checks=('order_known', 'order_not_terminal', 'cancel_approved', 'kill_switch_not_blocking')
- CXL_03ce7f8050ae: order=ORD_002, valid=True, checks=('order_known', 'order_not_terminal', 'cancel_approved', 'kill_switch_not_blocking')
- CXL_7ed5823eae96: order=ORD_999, valid=False, checks=('ORDER_UNKNOWN', 'order_not_terminal', 'cancel_approved', 'kill_switch_not_blocking')
- CXL_1ab90669b455: order=ORD_003, valid=False, checks=('order_known', 'ORDER_ALREADY_TERMINAL', 'terminal_order_blocked', 'cancel_approved', 'kill_switch_not_blocking')
- CXL_55b816952c35: order=ORD_001, valid=False, checks=('order_known', 'order_not_terminal', 'CANCEL_NOT_APPROVED', 'kill_switch_not_blocking')
- CXL_def2e01bfb0c: order=ORD_001, valid=False, checks=('order_known', 'order_not_terminal', 'cancel_approved', 'KILL_SWITCH_BLOCKS_CANCEL')

## Conclusion

CANCEL_SAFETY_SIMULATION_PASS
