"""
Discord Bot Listener (Python Version)
Thư viện cần cài: pip install discord.py requests
Chạy: python discord_bot.py
"""

import os
import asyncio
# pyrefly: ignore [missing-import]
import discord
# pyrefly: ignore [missing-import]
from discord.ext import commands
from llm_engine import extract_deadline_gemini

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Cấu hình Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_DISCORD_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

@bot.event
async def on_ready():
    print(f"🤖 Discord Bot (Python) đã kết nối thành công: {bot.user.name} (ID: {bot.user.id})")

@bot.event
async def on_message(message: discord.Message):
    # Bỏ qua tin nhắn do bot tự gửi
    if message.author.bot:
        return

    # Lắng nghe tin nhắn trên kênh văn bản
    if isinstance(message.channel, discord.TextChannel):
        print(f"📩 Nhận tin nhắn mới từ [#{message.channel.name}]: {message.content}")

        try:
            # Gọi LLM Engine phân tích tin nhắn
            extracted = extract_deadline_gemini(message.content, GEMINI_KEY)

            # LỌC THÔNG MINH: Chỉ xử lý nếu là Deadline, Thông báo học tập hoặc Tài liệu
            is_valid = extracted.get("is_deadline") or extracted.get("is_relevant_announcement") or extracted.get("is_course_resource")

            if not is_valid:
                print(f"🙈 [BỎ QUA TIN RÁC/TRÒ CHUYỆN]: \"{message.content[:60]}\"")
                return

            # Tự động lưu trữ thông báo quan trọng & metadata vào storage.json local
            from storage_manager import add_extracted_item
            add_extracted_item(extracted, source="Discord")
            print("💾 Đã tự động lưu trữ Thông báo / Deadline / Tài liệu vào storage.json local!")

            # Phản hồi Embed lên Discord
            embed = discord.Embed(
                title=f"📌 {extracted.get('title') or 'Thông báo mới'}",
                description=f"**Môn học:** {extracted.get('course') or 'Chung'}",
                color=discord.Color.red() if extracted.get('priority') == 'HIGH' else (discord.Color.blue() if extracted.get('is_course_resource') else discord.Color.gold())
            )
            if extracted.get("is_deadline"):
                embed.add_field(name="⏰ Hạn nộp", value=extracted.get("due_date") or "Cần xác nhận", inline=True)
                embed.add_field(name="🔥 Ưu tiên", value=extracted.get("priority"), inline=True)
            elif extracted.get("is_course_resource"):
                embed.add_field(name="📁 Loại", value="Tài liệu / Slide đính kèm", inline=True)

            embed.add_field(name="💬 Nguồn trích dẫn", value=f'"{extracted.get("quote")}"', inline=False)
            embed.set_footer(text=f"AI Confidence: {extracted.get('confidence')}% · Đã lưu storage.json local")

            await message.reply(embed=embed)

        except Exception as e:
            print("Lỗi khi xử lý AI:", e)

    await bot.process_commands(message)

# Lệnh !scan_history: Quét N tin nhắn cũ trong channel để tìm deadline bị trôi
@bot.command(name="scan_history")
async def scan_history(ctx, limit: int = 30):
    """Quét N tin nhắn cũ gần nhất trong channel"""
    await ctx.send(f"🔍 Đang quét {limit} tin nhắn gần nhất trong channel #{ctx.channel}...")
    count = 0
    async for msg in ctx.channel.history(limit=limit):
        if msg.author.bot or not msg.content.strip():
            continue
        
        try:
            extracted = extract_deadline_gemini(msg.content, GEMINI_KEY)
            if extracted.get("is_deadline"):
                count += 1
                embed = discord.Embed(
                    title=f"📌 [Phát hiện từ tin cũ] {extracted.get('title')}",
                    description=f"**Môn học:** {extracted.get('course')}",
                    color=discord.Color.blue()
                )
                embed.add_field(name="⏰ Hạn nộp", value=extracted.get("due_date") or "Cần xác nhận", inline=True)
                embed.add_field(name="💬 Trích dẫn", value=f'"{extracted.get("quote")}"', inline=False)
                await ctx.send(embed=embed)
        except Exception as err:
            print("Error parsing history msg:", err)

    await ctx.send(f"✅ Đã quét xong! Tìm thấy {count} deadline từ lịch sử tin nhắn.")

if __name__ == "__main__":
    if BOT_TOKEN != "YOUR_DISCORD_BOT_TOKEN":
        bot.run(BOT_TOKEN)
    else:
        print("💡 Hãy gán DISCORD_BOT_TOKEN và GEMINI_API_KEY để chạy Discord Bot Python thật!")
