import asyncio

from client.llm_client import LLMClient


class CLI:
    def __init__(self):
        pass
    
    def run_single(self):
        pass


async def main():
    client = LLMClient()
    messages = [{ "role": "user", "content": "What is 2 + 2" }]
    async for event in client.chat_completion(messages=messages, stream=True):
        print(event)
    print("done")
    
    
asyncio.run(main())