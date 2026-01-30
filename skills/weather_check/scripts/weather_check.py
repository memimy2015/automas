#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re


def check_weather(region, date_str):
    # 验证日期格式是否为yyyyMMdd
    if not re.match(r'^\d{8}$', date_str):
        return "错误：日期格式不正确，应为yyyyMMdd格式（如：20251105）"
    
    # 检查日期是否为20251105
    if region == "北方":
        return "晴天"
    elif region == "中部":
        return "阴天"
    elif region == "南方":
        return "下雨"
    else:
        return "未知"


def main():
    """主函数"""
    if len(sys.argv) != 3:
        print("错误：请提供一个区域和日期yyyyMMdd")
        print("示例: python weather_check.py 北方 20251105")
        sys.exit(1)
    
    region = sys.argv[1]
    date_str = sys.argv[2]
    weather = check_weather(region, date_str)
    print(weather)


if __name__ == "__main__":
    main()


