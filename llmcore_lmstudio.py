
# llmcore_lmstudio.py - LM Studio本地LLM适配器
# 用法: 作为llmcore.py的LMStudioSession类，通过MixinSession接入fallback链
import json, requests, os, sys, uuid
from datetime import datetime

class LMStudioSession:
    """LM Studio本地LLM会话 - 兼容llmcore的session接口"""
    
    def __init__(self, model="qwen2.5-0.5b-instruct", base_url="http://127.0.0.1:1234/v1"):
        self.name = "LMStudio-Local"
        self.model = model
        self.base_url = base_url
        self.system = ""
        self.tools = []
        self.temperature = 0.7
        self.max_tokens = 4096
        self.history = []
        self.max_retries = 3
        self._available = None
    
    def check_available(self):
        """检查LM Studio是否可用"""
        try:
            resp = requests.get(f"{self.base_url}/models", timeout=3)
            self._available = resp.status_code == 200
        except:
            self._available = False
        return self._available
    
    def raw_ask(self, messages, stream=True):
        """兼容llmcore的raw_ask接口"""
        if isinstance(messages, dict):
            msgs = messages.get("content", [])
            if isinstance(msgs, list):
                # 转换content list为OpenAI格式
                formatted_msgs = []
                if self.system:
                    formatted_msgs.append({"role": "system", "content": self.system})
                # 处理content blocks
                user_content = []
                tool_results = []
                for block in msgs:
                    if isinstance(block, dict):
                        t = block.get("type")
                        if t == "text":
                            user_content.append(block.get("text", ""))
                        elif t == "tool_result":
                            tool_results.append({
                                "role": "tool",
                                "tool_call_id": block.get("tool_use_id", ""),
                                "content": block.get("content", "")
                            })
                if user_content:
                    formatted_msgs.append({"role": "user", "content": "\n".join(user_content)})
                formatted_msgs.extend(tool_results)
            else:
                formatted_msgs = [{"role": "user", "content": str(messages)}]
        elif isinstance(messages, list):
            formatted_msgs = messages
        else:
            formatted_msgs = [{"role": "user", "content": str(messages)}]
        
        payload = {
            "model": self.model,
            "messages": formatted_msgs,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.tools:
            payload["tools"] = self.tools
        
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            
            # 构造兼容的响应对象
            class Response:
                def __init__(self, raw_data):
                    self.raw = raw_data
                    choice = raw_data["choices"][0]
                    msg = choice["message"]
                    self.content = msg.get("content", "")
                    self.tool_calls = msg.get("tool_calls", [])
                    self.usage = raw_data.get("usage", {})
            
            return iter([Response(data)])
        except Exception as e:
            return iter([f"!!!Error: LM Studio request failed: {e}"])
    
    def chat(self, messages, tools=None):
        """高层chat接口"""
        merged = {"role": "user", "content": []}
        for msg in messages:
            c = msg.get("content", "")
            if isinstance(c, str):
                merged["content"].append({"type": "text", "text": c})
            elif isinstance(c, list):
                merged["content"].extend(c)
        
        return self.raw_ask(merged)
