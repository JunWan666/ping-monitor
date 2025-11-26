@echo off
chcp 65001 >nul
echo 正在启动构建和推送脚本...
python build_and_push.py
pause