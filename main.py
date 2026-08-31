import asyncio

from client.llm_client import LLMClient


async def main():
    client = LLMClient()
    messages = [{ "role": "user", "content": "What is 2 + 2" }]
    await client.chat_completion(messages=messages, stream=False)
    print("done")
    
    
asyncio.run(main())