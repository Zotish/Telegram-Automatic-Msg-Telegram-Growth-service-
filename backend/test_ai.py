import asyncio
import os
import sys

# Add the current directory to sys.path to import telegram_worker
sys.path.append(os.getcwd())

from telegram_worker import get_gemini_reply

async def test_ai():
    context = "Cryptocurrency and Blockchain technology for beginners"
    print(f"Testing Gemini AI with context: {context}\n")
    
    history = "User: Hey guys, what is the best wallet for Bitcoin?\nMember: I like Ledger for security.\nMember: Metamask is good for DeFi."
    last_msg = "Metamask is good for DeFi."
    
    print("--- Testing Context-Aware Reply ---")
    reply = await get_gemini_reply(context, prompt_type="chat", user_msg=last_msg, history=history)
    print(f"History:\n{history}")
    print(f"AI Reply: {reply}")

    print("\n--- Testing Topic Initiation ---")
    start_msg = await get_gemini_reply(context, prompt_type="start")
    print(f"Start Msg: {start_msg}")

if __name__ == "__main__":
    asyncio.run(test_ai())
