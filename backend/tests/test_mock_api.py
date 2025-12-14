"""
快速测试模拟数据API是否工作
需要先获取一个有效的JWT token
"""
import requests
import json

BASE_URL = "http://localhost:5300"

# 注意：这个脚本需要有效的JWT token
# 您需要先登录获取token，或者创建一个测试用户

print("=" * 60)
print("模拟数据API测试")
print("=" * 60)
print("\n⚠️  注意：此测试需要有效的JWT token")
print("   请先登录前端获取token，或使用以下方式：")
print("\n1. 访问 http://localhost:3000")
print("2. 使用Google登录")
print("3. 打开浏览器开发者工具 -> Network")
print("4. 查看API请求的Authorization header")
print("5. 复制Bearer token")
print("\n" + "=" * 60)

