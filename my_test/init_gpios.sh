#!/bin/bash

# 定义需要初始化的引脚列表
GPIO_PINS=(396 394 387 402 421 383 384 423)

echo "开始初始化 GPIO 引脚..."

for pin in "${GPIO_PINS[@]}"; do
    # 1. 导出引脚 (如果已经导出则跳过，避免报错)
    if [ ! -d /sys/class/gpio/gpio$pin ]; then
        echo $pin > /sys/class/gpio/export 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "引脚 $pin: 已导出"
        else
            echo "引脚 $pin: 导出失败 (可能已被占用或权限不足)"
            continue
        fi
    else
        echo "引脚 $pin: 已经存在，跳过导出步骤"
    fi

    # 2. 设置方向为输出 (out)
    echo out > /sys/class/gpio/gpio$pin/direction
    
    # 3. 将电平置低 (0)
    echo 1 > /sys/class/gpio/gpio$pin/value
    
    echo "引脚 $pin: 配置完毕 (输出模式, 低电平)"
done

echo "所有引脚初始化完成。"
