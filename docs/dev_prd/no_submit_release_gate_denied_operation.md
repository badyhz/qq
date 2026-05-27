# No-Submit Release Gate Denied Operations

Task: T1183

## Operations

| Operation       | Category  | Severity |
|-----------------|-----------|----------|
| place_order     | execution | critical |
| cancel_order    | execution | critical |
| modify_order    | execution | critical |
| close_position  | position  | critical |
| open_position   | position  | critical |
| transfer_funds  | account   | critical |

All listed operations are blocked unconditionally in no-submit mode.
