import logging
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
from telegram.error import TelegramError
import pytz

from config import BOT_TOKEN, ADMIN_USERNAME, TIMEZONE
from db import Database
from scheduler import MessageScheduler

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_CHANNEL, ENTERING_MESSAGE, ENTERING_TIME, CONFIRMING_DATE, ENTERING_CHALLENGE_DAY, ENTERING_END_DATE = range(6)

class ChallengeBot:
    def __init__(self):
        self.db = Database()
        self.scheduler = None
        self.application = (
            Application.builder()
            .token(BOT_TOKEN)
            .build()
        )
        self.setup_handlers()
        # Scheduler'ni ishga tushirish
        self.setup_scheduler_sync()
    
    def setup_handlers(self):
        """Handler'larni sozlash"""
        
        # Conversation handler for /send command
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('send', self.start_schedule)],
            states={
                CHOOSING_CHANNEL: [
                    CallbackQueryHandler(self.channel_selected, pattern='^channel_'),
                    CommandHandler('cancel', self.cancel)
                ],
                ENTERING_MESSAGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_entered),
                    CommandHandler('cancel', self.cancel)
                ],
                ENTERING_TIME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.time_entered),
                    CommandHandler('cancel', self.cancel)
                ],
                CONFIRMING_DATE: [
                    CallbackQueryHandler(self.date_confirmed, pattern='^date_'),
                    CommandHandler('cancel', self.cancel)
                ],
                ENTERING_CHALLENGE_DAY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.challenge_day_entered),
                    CommandHandler('cancel', self.cancel)
                ],
                ENTERING_END_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.end_date_entered),
                    CommandHandler('cancel', self.cancel)
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )
        
        # Kanal ulash uchun ConversationHandler
        kanal_ulash_handler = ConversationHandler(
            entry_points=[CommandHandler('kanal_ulash', self.kanal_ulash_start)],
            states={
                CHOOSING_CHANNEL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.kanal_ulash_process),
                    CommandHandler('cancel', self.cancel)
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )
        
        # Boshqa handler'lar
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(kanal_ulash_handler)
        self.application.add_handler(CommandHandler("kanallarim", self.my_channels))
        self.application.add_handler(CommandHandler("rejalarim", self.my_schedules))
        self.application.add_handler(conv_handler)
        self.application.add_handler(CallbackQueryHandler(self.delete_schedule_callback, pattern="^delete_"))
        self.application.add_handler(CallbackQueryHandler(self.delete_channel_callback, pattern="^deletechan_"))
        
        # Xatoliklar uchun
        # add_error_handler expects (object, context) not (Update, context)
        async def error_handler_wrapper(update_or_obj, context):
            # Only call if update_or_obj is Update
            if isinstance(update_or_obj, Update):
                await self.error_handler(update_or_obj, context)
            # else: do nothing (do not call with None)
        self.application.add_error_handler(error_handler_wrapper)

    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Botni ishga tushirish"""
        if not update.effective_user or not update.message:
            return
        
        user = update.effective_user
        self.db.add_user(user.id, user.username or "")
        
        welcome_text = f"""Salom {user.first_name or 'Foydalanuvchi'}!

Men Challenge Bot - har kuni avtomatik xabar yuborish uchun yaratilgan bot.

📋 Mening imkoniyatlarim:
• /kanal_ulash - Kanal ulash
• /kanallarim - Ulangan kanallar
• /send - Xabar rejalashtirish
• /rejalarim - Rejalashtirilgan xabarlar

❓ Savollar bo'lsa: {ADMIN_USERNAME}
        """
        
        await update.message.reply_text(welcome_text)
    
    async def kanal_ulash_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        
        await update.message.reply_text(
            "📢 Kanal ulash uchun kanal username yoki ID ni yuboring:\n\n"
            "Masalan: @mychannel yoki -1001234567890\n\nBekor qilish uchun /cancel"
        )
        return CHOOSING_CHANNEL

    async def kanal_ulash_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.message:
            return CHOOSING_CHANNEL
        user_id = update.effective_user.id
        channel_input = update.message.text.strip() if update.message.text else ""
        try:
            if channel_input.startswith('@'):
                chat = await context.bot.get_chat(channel_input)
            else:
                chat = await context.bot.get_chat(int(channel_input))
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await update.message.reply_text(
                    "❌ Bot kanalda admin emas! Botni admin qiling va xabar yuborish ruxsatini bering."
                )
                return CHOOSING_CHANNEL
            kanal_nomi = chat.title if chat.title else "Noma'lum"
            self.db.add_channel(user_id, str(chat.id), kanal_nomi)
            await update.message.reply_text(
                f"✅ Kanal muvaffaqiyatli ulandi!\n\n"
                f"📢 Kanal: {kanal_nomi}\n"
                f"🆔 ID: {chat.id}"
            )
            return ConversationHandler.END
        except TelegramError as e:
            await update.message.reply_text(
                f"❌ Xatolik: {str(e)}\n\nKanal username yoki ID ni to'g'ri kiriting yoki /cancel bosing."
            )
            return CHOOSING_CHANNEL
        except Exception as e:
            await update.message.reply_text(
                f"❌ Kutilmagan xatolik: {str(e)}\n\nKanal username yoki ID ni to'g'ri kiriting yoki /cancel bosing."
            )
            return CHOOSING_CHANNEL
    
    async def my_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchining kanallarini ko'rsatish (yangilangan ko'rinish, o'chirish tugmasi bilan)"""
        if not update.effective_user or not update.message:
            return
            
        user_id = update.effective_user.id
        channels = self.db.get_user_channels(user_id)

        if not channels:
            await update.message.reply_text(
                "📭 Sizda ulangan kanallar yo'q.\n\n"
                "Kanal ulash uchun: /kanal_ulash"
            )
            return

        for idx, (channel_id, channel_name) in enumerate(channels, 1):
            username = "🚫 Username yo'q"
            try:
                chat = await context.bot.get_chat(channel_id)
                if getattr(chat, 'username', None):
                    username = f"@{chat.username}"
            except Exception:
                pass
            text = (
                f"{idx}\u20e3 Kanal nomi: ✅ {channel_name}\n"
                f"🔗 Username: {username}\n"
                f"🆔 ID: {channel_id}\n"
            )
            keyboard = [
                [InlineKeyboardButton("🗑 O'chirish", callback_data=f"deletechan_{channel_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)

    async def delete_channel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.callback_query or not update.effective_user:
            return
            
        query = update.callback_query
        await query.answer()
        data = query.data
        if data and data.startswith("deletechan_"):
            channel_id = data.replace("deletechan_", "")
            user_id = update.effective_user.id
            self.db.delete_channel(user_id, channel_id)
            await query.edit_message_text("✅ Kanal o'chirildi!")
    
    async def start_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.message:
            return ConversationHandler.END
            
        user_id = update.effective_user.id
        channels = self.db.get_user_channels(user_id)
        if not channels:
            await update.message.reply_text(
                "❌ Avval kanal ulashingiz kerak!\n\nKanal ulash uchun: /kanal_ulash"
            )
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton(channel_name, callback_data=f"channel_{channel_id}")]
            for channel_id, channel_name in channels
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📢 Qaysi kanalga xabar yubormoqchisiz?",
            reply_markup=reply_markup
        )
        return CHOOSING_CHANNEL

    async def channel_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.callback_query:
            return ConversationHandler.END
        query = update.callback_query
        await query.answer()
        channel_id = query.data.replace('channel_', '') if query.data else ""
        if context.user_data is None:
            context.user_data = {}
        context.user_data['selected_channel'] = channel_id

        # Kanal nomi va sana
        user_id = query.from_user.id
        channels = self.db.get_user_channels(user_id)
        kanal_nomi = next((name for cid, name in channels if cid == channel_id), channel_id)
        today = datetime.now(pytz.timezone(TIMEZONE)).strftime('%d.%m.%Y')

        await query.edit_message_text(
            f"📝 Yangi xabar matnini kiriting:\n\n"
            f"📢 Kanal: {kanal_nomi}\n"
            f"📅 Sana: {today}\n\n"
            f"Xabar matnini quyiga yozing va yuboring."
        )
        return ENTERING_MESSAGE

    async def message_entered(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return ENTERING_MESSAGE
        if context.user_data is None:
            context.user_data = {}
        context.user_data['message_text'] = update.message.text
        await update.message.reply_text(
            "⏰ Har kuni qaysi vaqtda yuborilsin?\n\nFormat: HH:MM\nMasalan: 09:30 yoki 18:45"
        )
        return ENTERING_TIME

    async def time_entered(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return ENTERING_TIME
        time_text = update.message.text
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_text):
            await update.message.reply_text(
                "❌ Noto'g'ri vaqt formati!\n\nTo'g'ri format: HH:MM\nMasalan: 09:30"
            )
            return ENTERING_TIME
        if context.user_data is None:
            context.user_data = {}
        context.user_data['time'] = time_text

        keyboard = [
            [
                InlineKeyboardButton("✅ Ha", callback_data="date_yes"),
                InlineKeyboardButton("❌ Yo'q", callback_data="date_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📅 Xabarga sana va challenge kuni qo'shilsinmi?\n\nFormat: 📅 2025-01-15  kun: ",
            reply_markup=reply_markup
        )
        return CONFIRMING_DATE

    async def date_confirmed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.callback_query or not update.effective_user:
            return ConversationHandler.END
        query = update.callback_query
        await query.answer()
        with_date = query.data == "date_yes" if query.data else False
        user_id = update.effective_user.id
        if context.user_data is None:
            context.user_data = {}
        channel_id = context.user_data.get('selected_channel', '')
        message_text = context.user_data.get('message_text', '')
        time_text = context.user_data.get('time', '')
        
        if with_date:
            # Challenge kunini so'rash
            await query.edit_message_text(
                "📅 Challenge kunini kiriting:\n\n"
                "Masalan: 1 \n\n"
               
                "Bekor qilish uchun /cancel"
            )
            context.user_data['with_date'] = True
            return ENTERING_CHALLENGE_DAY
        else:
            # Sana qo'shilmasin
            start_date = datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d')
            return await self.create_schedule(user_id, channel_id, message_text, time_text, False, start_date, context, update)

    async def challenge_day_entered(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Challenge kunini olish"""
        if not update.message or not update.message.text:
            return ENTERING_CHALLENGE_DAY
        
        challenge_day_text = update.message.text.strip()
        
        # Raqam ekanligini tekshirish
        if not challenge_day_text.isdigit():
            await update.message.reply_text(
                "❌ Noto'g'ri format!\n\n"
                "Faqat raqam kiriting. Masalan: 1, 15, 30"
            )
            return ENTERING_CHALLENGE_DAY
        
        challenge_day = int(challenge_day_text)
        if challenge_day < 1 or challenge_day > 365:
            await update.message.reply_text(
                "❌ Challenge kuni 1-365 oralig'ida bo'lishi kerak!\n\n"
                "Qaytadan kiriting:"
            )
            return ENTERING_CHALLENGE_DAY
        
        try:
            # Bugungi sanadan challenge kunini hisoblash
            today = datetime.now(pytz.timezone(TIMEZONE))
            # start_date ni timezone bilan yaratish
            start_date_dt = today - timedelta(days=challenge_day-1)
            start_date = start_date_dt.strftime('%Y-%m-%d')
            
            user_id = update.effective_user.id if update.effective_user else None
            if not user_id:
                await update.message.reply_text("❌ Foydalanuvchi ma'lumotlari topilmadi.")
                return ConversationHandler.END
                
            # context.user_data ni xavfsiz olish
            user_data = context.user_data if context.user_data else {}
            user_data['start_date'] = start_date  # start_date'ni context'ga saqlash
            if context.user_data is not None:
                context.user_data.update(user_data)  # Direct assignment o'rniga update() ishlatamiz
            
            # End date'ni so'rash
            await update.message.reply_text(
                "📅 Challenge tugash sanasini kiriting:\n\n"
                "Format: DD.MM.YYYY\n"
                "Masalan: 01.09.2028\n\n"
                "Bekor qilish uchun /cancel"
            )
            return ENTERING_END_DATE
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                "Qaytadan urinib ko'ring:"
            )
            return ENTERING_CHALLENGE_DAY

    async def end_date_entered(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """End date'ni olish"""
        if not update.message or not update.message.text:
            return ENTERING_END_DATE
        
        end_date_text = update.message.text.strip()
        
        # Sana formatini tekshirish (DD.MM.YYYY)
        import re
        if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', end_date_text):
            await update.message.reply_text(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format: DD.MM.YYYY\n"
                "Masalan: 01.09.2028"
            )
            return ENTERING_END_DATE
        
        try:
            # Sana formatini parse qilish
            day, month, year = map(int, end_date_text.split('.'))
            end_date_dt = datetime(year, month, day)
            
            # Bugungi sanani olish
            today = datetime.now(pytz.timezone(TIMEZONE))
            
            # End date bugungi sanadan oldin bo'lsa xatolik
            if end_date_dt.date() <= today.date():
                await update.message.reply_text(
                    "❌ Challenge tugash sanasi bugungi sanadan keyin bo'lishi kerak!\n\n"
                    "Qaytadan kiriting:"
                )
                return ENTERING_END_DATE
            
            # End date'ni YYYY-MM-DD formatiga o'tkazish
            end_date_str = end_date_dt.strftime('%Y-%m-%d')
            
            user_id = update.effective_user.id if update.effective_user else None
            if not user_id:
                await update.message.reply_text("❌ Foydalanuvchi ma'lumotlari topilmadi.")
                return ConversationHandler.END
                
            # context.user_data ni xavfsiz olish
            user_data = context.user_data if context.user_data else {}
            channel_id = user_data.get('selected_channel', '')
            message_text = user_data.get('message_text', '')
            time_text = user_data.get('time', '')
            start_date = user_data.get('start_date', '')
            
            if not start_date:
                await update.message.reply_text("❌ Boshlang'ich sana topilmadi. Qaytadan urinib ko'ring.")
                return ConversationHandler.END
            
            return await self.create_schedule(user_id, channel_id, message_text, time_text, True, start_date, context, update, end_date_str)
        except ValueError as e:
            await update.message.reply_text(
                "❌ Noto'g'ri sana!\n\n"
                "To'g'ri format: DD.MM.YYYY\n"
                "Masalan: 01.09.2028"
            )
            return ENTERING_END_DATE
        except Exception as e:
            await update.message.reply_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                "Qaytadan urinib ko'ring:"
            )
            return ENTERING_END_DATE

    async def create_schedule(self, user_id, channel_id, message_text, time_text, with_date, start_date, context, update, end_date_str=None):
        """Rejani yaratish"""
        try:
            # Defensive defaults
            if message_text is None:
                message_text = ""
            if start_date is None:
                start_date = datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d')
            if end_date_str is None:
                end_date_str = ""
            schedule_id = self.db.add_schedule(
                user_id, channel_id, message_text, time_text, with_date, start_date, end_date_str
            )
            if self.scheduler:
                self.scheduler.add_schedule_job(
                    user_id, channel_id, schedule_id, time_text, message_text, with_date, start_date, end_date_str
                )
            channels = self.db.get_user_channels(user_id)
            kanal_nomi = next((name for cid, name in channels if cid == channel_id), channel_id)
            status_text = (
                f"✅ Xabar rejalashtirildi!\n\n"
                f"📢 Kanal: {kanal_nomi}\n"
                f"🕒 Vaqt: {time_text}\n"
            )
            if with_date:
                status_text += f"📅 Sana: {start_date}"
            try:
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text(status_text)
                elif hasattr(update, 'edit_message_text'):
                    await update.edit_message_text(status_text)
                else:
                    # Agar hech qanday usul ishlamasa, yangi xabar yuborish
                    if hasattr(update, 'effective_user') and update.effective_user:
                        await self.application.bot.send_message(
                            chat_id=update.effective_user.id,
                            text=status_text
                        )
            except Exception as e:
                logger.warning(f"Status xabarini yuborishda xatolik: {e}")
            if hasattr(context, 'user_data') and context.user_data is not None:
                context.user_data.clear()
            return ConversationHandler.END
            
        except Exception as e:
            error_text = f"❌ Reja yaratishda xatolik: {str(e)}"
            if hasattr(update, 'message') and update.message:
                await update.message.reply_text(error_text)
            elif hasattr(update, 'edit_message_text'):
                await update.edit_message_text(error_text)
            return ConversationHandler.END
    
    async def my_schedules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchining rejalarini dublikatlarsiz, har biriga alohida o'chirish tugmasi bilan ko'rsatish"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        schedules = self.db.get_user_schedules(user_id)

        if not schedules:
            await update.message.reply_text(
                "📭 Sizda rejalashtirilgan xabarlar yo'q.\n\n"
                "Reja yaratish uchun: /send"
            )
            return

        seen = set()
        for idx, schedule in enumerate(schedules, 1):
            schedule_id, channel_id, message, time, with_date, start_date, day_count, channel_name = schedule
            key = (channel_id, message, time, start_date)
            if key in seen:
                continue
            seen.add(key)
            sana_ha = 'Ha' if with_date else "Yo'q"
            kanal_nomi = channel_name or channel_id
            text = (
                f"🔢 Reja raqami: {len(seen)}\n"
                f"📢 Kanal: {kanal_nomi}\n"
                f"⏰ Vaqt: {time}\n"
                f"📅 Sana: {sana_ha}\n"
                f"📝 Xabar: {message[:50]}{'...' if len(message) > 50 else ''}\n"
            )
            keyboard = [
                [InlineKeyboardButton(f"🗑 {len(seen)}-reja o'chirish", callback_data=f"delete_{schedule_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)

    async def delete_schedule_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.callback_query:
            return
            
        query = update.callback_query
        await query.answer()
        data = query.data
        if data and data.startswith("delete_"):
            schedule_id = int(data.replace("delete_", ""))
            # Bazadan o'chirish
            sched = self.db.get_schedule_by_id(schedule_id)
            if sched:
                user_id = sched[1]
                channel_id = sched[2]
                time = sched[4]  # schedules jadvalida 4-index: time
                self.db.delete_schedule(schedule_id)
                # Scheduler'dan ham o'chirish
                if self.scheduler and time:
                    self.scheduler.remove_schedule_job(user_id, channel_id, time)
                await query.edit_message_text("✅ Reja o'chirildi!")
            else:
                await query.edit_message_text("❌ Reja topilmadi yoki allaqachon o'chirilgan.")
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Conversation'ni bekor qilish"""
        if context.user_data:
            context.user_data.clear()
        if update is not None and hasattr(update, 'message') and update.message is not None:
            await update.message.reply_text("❌ Amaliyot bekor qilindi.")
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xatoliklarni qayd qilish"""
        logger.error(f"Xatolik: {context.error}")
        if update is not None and hasattr(update, "message") and update.message is not None:
            await update.message.reply_text(
                "❌ Kutilmagan xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
            )
    
    def setup_scheduler_sync(self):
        """Scheduler'ni sinxron tarzda ishga tushirish"""
        self.scheduler = MessageScheduler(self.application.bot)
        
        # Scheduler'ni keyinroq ishga tushirish (event loop ishlaganda)
        # self.scheduler.start()
       
        all_schedules = []
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, user_id, channel_id, message, time, with_date, start_date, end_date FROM schedules")
            all_schedules = cursor.fetchall()
        for schedule in all_schedules:
            schedule_id, user_id, channel_id, message, time, with_date, start_date, end_date = schedule
            self.scheduler.add_schedule_job(
                user_id, channel_id, schedule_id, time, message, bool(with_date), start_date, end_date or ""
            )

    async def setup_scheduler(self):
        """Scheduler'ni ishga tushirish va barcha mavjud rejalarni yuklash"""
        self.scheduler = MessageScheduler(self.application.bot)
        
        # Scheduler'ni ishga tushirish
        self.scheduler.start()
       
        all_schedules = []
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, user_id, channel_id, message, time, with_date, start_date, end_date FROM schedules")
            all_schedules = cursor.fetchall()
        for schedule in all_schedules:
            schedule_id, user_id, channel_id, message, time, with_date, start_date, end_date = schedule
            self.scheduler.add_schedule_job(
                user_id, channel_id, schedule_id, time, message, bool(with_date), start_date, end_date or ""
            )

    def run(self):
        """Botni ishga tushirish"""
        async def start_bot():
            # Scheduler'ni ishga tushirish
            if self.scheduler:
                self.scheduler.start()
            # Bot'ni ishga tushirish
            if self.application:
                await self.application.initialize()
                await self.application.start()
                if self.application.updater:
                    await self.application.updater.start_polling()
                # Bot'ni to'xtatmaslik uchun kutish
                try:
                    await asyncio.Event().wait()
                except KeyboardInterrupt:
                    await self.application.stop()
                    await self.application.shutdown()
        
        import asyncio
        asyncio.run(start_bot())

if __name__ == '__main__':
    bot = ChallengeBot()
    bot.run()