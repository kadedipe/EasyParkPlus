
## 8. `activity_diagrams.md`
```markdown
# Activity Diagrams - Parking Management System

## Core Business Processes

### 1. Complete Parking Process Flow
```plantuml
@startuml
title Complete Parking Process Flow
start
:Customer arrives at parking lot;

if (Has reservation?) then (yes)
  :Scan reservation QR code;
  :Validate reservation;
  if (Reservation valid?) then (yes)
    :Assign reserved spot;
  else (no)
    :Treat as walk-in;
  endif
else (no)
  :Walk-in customer;
endif

:Check spot availability;
if (Spots available?) then (yes)
  :Select spot type;
  :Assign parking spot;
  :Generate parking ticket;
  :Open entry barrier;
  :Customer parks vehicle;
  :Update spot status to OCCUPIED;
  
  repeat
    :Monitor parking duration;
    if (Customer needs extension?) then (yes)
      :Process extension payment;
      :Extend parking time;
    else (no)
    endif
  repeat while (Vehicle not exiting?)
  
  :Customer prepares to exit;
  :Scan ticket at exit;
  :Calculate parking charges;
  :Display amount due;
  
  repeat
    :Process payment;
    if (Payment successful?) then (yes)
      :Generate receipt;
    else (no)
      :Show payment error;
      :Retry payment method;
    endif
  repeat while (Payment not successful)
  
  :Open exit barrier;
  :Update spot status to AVAILABLE;
  :Log transaction;
  stop
else (no)
  :Display "LOT FULL" message;
  :Redirect to nearby lots;
  stop
endif
@enduml