import json
import os

import requests

# token 从环境变量读取，不要把真实凭据写进仓库
# 取值：调用登录接口，复制响应中的 token 字段
token = os.getenv("TEST_TOKEN")
if not token:
    raise SystemExit("请先设置环境变量 TEST_TOKEN")

base_url = "http://127.0.0.1:8080/agent/travel-route-plan"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 测试会话列表
print("=== 获取会话列表 ===")
resp = requests.get(f"{base_url}/chat/list", headers=headers)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

# 测试会话详情
print("\n=== 获取会话详情 sid=36 ===")
resp = requests.get(f"{base_url}/chat/detail/36", headers=headers)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
