; ChipID: PT3210

;Stack Configuration------------------------------------------------------------
Stack_Size      EQU     0x00001000
                AREA    STACK, NOINIT, READWRITE, ALIGN=3
Stack_Mem       SPACE   Stack_Size
__initial_sp
;-------------------------------------------------------------------------------

;Heap Configuration-------------------------------------------------------------
Heap_Size       EQU     0
                AREA    HEAP, NOINIT, READWRITE, ALIGN=3
__heap_base
Heap_Mem        SPACE   Heap_Size
__heap_limit
;-------------------------------------------------------------------------------
                PRESERVE8
                THUMB

; Vector Table Mapped to Address 0 at Reset-------------------------------------
                AREA    RESET, DATA, READONLY
                EXPORT  __Vectors

__Vectors       DCD     __initial_sp                    ; 0,  load top of stack
                DCD     Reset_Handler                   ; 1,  reset handler
                DCD     NMI_Handler                     ; 2,  nmi handler
                DCD     HardFault_Handler               ; 3,  hard fault handler
                DCD     0                               ; 4,  Reserved
                DCD     0                               ; 5,  Reserved
                DCD     0                               ; 6,  Reserved
                DCD     0                               ; 7,  Reserved
                DCD     0                               ; 8,  Reserved
                DCD     0                               ; 9,  Reserved
                DCD     0                               ; 10, Reserved
                DCD     SVCall_Handler                  ; 11, svcall handler
                DCD     0                               ; 12, Reserved
                DCD     0                               ; 13, Reserved
                DCD     PendSV_Handler                  ; 14, pendsv handler
                DCD     SysTick_Handler                 ; 15, systick handler

                ; External Interrupts
                DCD    EXTI_IRQHandler                  ;  irq0  EXTI 
                DCD    WWDG_IRQHandler                  ;  irq1  WWDG 
                DCD    AON_WKUP_IRQHandler              ;  irq2  APB2AON Wakeup 
                DCD    BLE_IRQHandler                   ;  irq3  BLE Combined 
                DCD    RTC_IRQHandler                   ;  irq4  RTC
                DCD    DMAC_IRQHandler                  ;  irq5  DMAC 
                DCD    QSPI_IRQHandler                  ;  irq6  QSPI
                DCD    0                                ;  irq7  Reserved
                DCD    CRYPT_IRQHandler                 ;  irq8  CRYPT
                DCD    BOD_IRQHandler                   ;  irq9  BOD
                DCD    IWDG_IRQHandler                  ;  irq10 IWDG
                DCD    0                                ;  irq11 Reserved
                DCD    0                                ;  irq12 Reserved
                DCD    BLE_WKUP_IRQHandler              ;  irq13 BLE Wakeup
                DCD    0                                ;  irq14 Reserved
                DCD    ATMR_IRQHandler                  ;  irq15 Advance Timer
                DCD    BTMR_IRQHandler                  ;  irq16 Base Timer 
                DCD    CTMR2_IRQHandler                 ;  irq17 Common Timer2
                DCD    CTMR1_IRQHandler                 ;  irq18 Common Timer1
                DCD    0                                ;  irq19 Reserved
                DCD    0                                ;  irq20 Reserved
                DCD    CTMR3_IRQHandler                 ;  irq21 Common Timer3
                DCD    LTMR_IRQHandler                  ;  irq22 Lowpower Timer
                DCD    I2C1_IRQHandler                  ;  irq23 I2C1  
                DCD    0                                ;  irq24 Reserved
                DCD    SPI1_IRQHandler                  ;  irq25 SPI1
                DCD    SPI2_IRQHandler                  ;  irq26 SPI2
                DCD    UART1_IRQHandler                 ;  irq27 UART1
                DCD    UART2_IRQHandler                 ;  irq28 UART2
                DCD    0                                ;  irq29 Reserved
                DCD    SUART1_IRQHandler                ;  irq30 SUART1
                DCD    0                                ;  irq31 Reserved

__Vectors_End

__Vectors_Size  EQU  __Vectors_End - __Vectors

;-------------------------------------------------------------------------------
                AREA    |.text|, CODE, READONLY 
                ;AREA    INT, CODE, READONLY       

;Reset Handler----------------------------------------------
Reset_Handler   PROC
                EXPORT  Reset_Handler                      [WEAK]
                IMPORT  __main

                ;SYSCFG->SRAMPSICTR.Word = 0;
                MOVS    R0, #0x00
                LDR     R1, =0x40101504 
                STR     R0, [R1]
                
                ;SRAM1 0x08000000 ~ 0x08009FFF[40K] + 0x0800A000 ~ 0x0800BFFF [8K]
                ;SRAM2 0x20000000 ~ 0x20005FFF[24K] + 0x20006000 ~ 0x20009FFF [16K] + 0x2000A000 ~ 0x2000B7FF[6K]
                ;SYSCFG->SRAMCTRL.Word = 0x29;
                MOVS    R0, #0x29
                LDR     R1, =0x40101428 
                STR     R0, [R1]

                MOVS    R0, #00
                LDR     R1, =0x4007C040 
                STR     R0, [R1]

                LDR     R0, =__main
                BX      R0

                ENDP

; Dummy Exception Handlers (infinite loops here, can be modified)

NMI_Handler     PROC
                EXPORT  NMI_Handler                        [WEAK]
                B       .
                ENDP

HardFault_Handler\
                PROC
                EXPORT  HardFault_Handler                  [WEAK]
                B       .
                ENDP

SVCall_Handler  PROC
                EXPORT  SVCall_Handler                     [WEAK]
                B       .
                ENDP

PendSV_Handler  PROC
                EXPORT  PendSV_Handler                     [WEAK]
                B       .
                ENDP

SysTick_Handler PROC
                EXPORT  SysTick_Handler                    [WEAK]
                B       .
                ENDP

BLE_WKUP_IRQHandler PROC
                EXPORT                                     [WEAK]
                BX      LR
                ENDP

Default_Handler PROC
                EXPORT    EXTI_IRQHandler                  [WEAK]
                EXPORT    WWDG_IRQHandler                  [WEAK]
                EXPORT    AON_WKUP_IRQHandler              [WEAK]
                EXPORT    BLE_IRQHandler                   [WEAK]
                EXPORT    RTC_IRQHandler                   [WEAK]
                EXPORT    DMAC_IRQHandler                  [WEAK]
                EXPORT    QSPI_IRQHandler                  [WEAK]
                EXPORT    CRYPT_IRQHandler                 [WEAK]
                EXPORT    BOD_IRQHandler                   [WEAK]
                EXPORT    IWDG_IRQHandler                  [WEAK]
                EXPORT    ATMR_IRQHandler                  [WEAK]
                EXPORT    BTMR_IRQHandler                  [WEAK]
                EXPORT    CTMR2_IRQHandler                 [WEAK]
                EXPORT    CTMR1_IRQHandler                 [WEAK]
                EXPORT    CTMR3_IRQHandler                 [WEAK]
                EXPORT    LTMR_IRQHandler                  [WEAK]
                EXPORT    I2C1_IRQHandler                  [WEAK]
                EXPORT    SPI1_IRQHandler                  [WEAK]
                EXPORT    SPI2_IRQHandler                  [WEAK]
                EXPORT    UART1_IRQHandler                 [WEAK]
                EXPORT    UART2_IRQHandler                 [WEAK]
                EXPORT    SUART1_IRQHandler                [WEAK]

EXTI_IRQHandler
WWDG_IRQHandler
AON_WKUP_IRQHandler
BLE_IRQHandler
RTC_IRQHandler
DMAC_IRQHandler
QSPI_IRQHandler
CRYPT_IRQHandler
BOD_IRQHandler
IWDG_IRQHandler
ATMR_IRQHandler
BTMR_IRQHandler
CTMR2_IRQHandler
CTMR1_IRQHandler
CTMR3_IRQHandler
LTMR_IRQHandler
I2C1_IRQHandler
SPI1_IRQHandler
SPI2_IRQHandler
UART1_IRQHandler
UART2_IRQHandler
SUART1_IRQHandler
                B       .
                ENDP

                ALIGN
;*******************************************************************************
; User Stack and Heap initialization
;*******************************************************************************
                IF      :DEF:__MICROLIB

                EXPORT  __initial_sp
                EXPORT  __heap_base
                EXPORT  __heap_limit

                ELSE

                IMPORT  __use_two_region_memory
                EXPORT  __user_initial_stackheap
__user_initial_stackheap
                LDR     R0, =  Heap_Mem
                LDR     R1, = (Stack_Mem + Stack_Size)
                LDR     R2, = (Heap_Mem +  Heap_Size)
                LDR     R3, = Stack_Mem
                BX      LR

                ALIGN

                ENDIF

                END
