/**
 * @file main.c
 * @brief 
 * @author your name (xxx@xxx.com)
 * @date 2024-12-13 01:09:53
 * 
 * @copyright Copyright (c) 2024 by xxx, All Rights Reserved. 
 */

#include <stdio.h>
#include "xfusion.h"

#if defined(CONFIG_PORT_USE_FREERTOS)

#include "FreeRTOS.h"
#include "task.h"

static StackType_t xTaskStackXFusion[CONFIG_PORT_FREERTOS_XF_TASK_STACK_SIZE];
static StaticTask_t xTaskBufferXFusion;

static void xfusion_task(void *pvParameters)
{
    xfusion_init();
    while (1)
    {
        xfusion_run();
    }
}

int main(void)
{
    xTaskCreateStatic( xfusion_task,
                        "xfusion_task",
                        CONFIG_PORT_FREERTOS_XF_TASK_STACK_SIZE,
                        ( void * ) NULL,
                        configMAX_PRIORITIES - 1,
                        xTaskStackXFusion,
                        &xTaskBufferXFusion);

    vTaskStartScheduler();
}

#else

int main(void)
{
    xfusion_init();

    while (1)
    {
        xfusion_run();
    }
}
#endif
