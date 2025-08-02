import logging
from datetime import datetime
import pytz
from telegram import Bot
from config import BOT_TOKEN, TIMEZONE
from db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        self.CronTrigger = CronTrigger
        self.scheduler = AsyncIOScheduler(timezone=TIMEZONE)
        # Scheduler'ni keyinroq ishga tushirish
        # self.scheduler.start()
    
    def start(self):
        """Scheduler'ni ishga tushirish"""
        if not self.scheduler.running:
            try:
                self.scheduler.start()
                logger.info("Scheduler ishga tushirildi")
            except RuntimeError as e:
                if "no running event loop" in str(e):
                    logger.info("Scheduler event loop yo'q, keyinroq ishga tushiriladi")
                else:
                    raise e
    
    def add_schedule_job(self, user_id: int, channel_id: str, schedule_id: int, 
                        time: str, message: str, with_date: bool, start_date: str, end_date: str = ""):
        hour, minute = map(int, time.split(':'))
        job_id = f"{user_id}_{channel_id}_{time}"
        try:
            self.scheduler.remove_job(job_id)
        except:
            pass
        # Ensure message, start_date, and end_date are not None
        safe_message = message if message is not None else ""
        safe_start_date = start_date if start_date is not None else "1970-01-01"
        safe_end_date = end_date if end_date is not None else ""
        self.scheduler.add_job(
            func=self.send_scheduled_message,  # Async function directly
            trigger=self.CronTrigger(hour=hour, minute=minute),
            id=job_id,
            args=[user_id, channel_id, schedule_id, safe_message, with_date, safe_start_date, safe_end_date],
            replace_existing=True
        )
        logger.info(f"Yangi reja qo'shildi: {job_id}")

    async def send_scheduled_message(self, user_id: int, channel_id: str, schedule_id: int, message: str, with_date: bool, start_date: str, end_date: str = ""): 
        try:
            safe_message = message if message is not None else ""
            safe_start_date = start_date if start_date is not None else "1970-01-01"
            safe_end_date = end_date if end_date is not None else ""
            msg = safe_message
            if with_date:
                today_dt = datetime.now(pytz.timezone(TIMEZONE))
                oylar = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentyabr', 'oktyabr', 'noyabr', 'dekabr']
                kunlar = ['dushanba', 'seshanba', 'chorshanba', 'payshanba', 'juma', 'shanba', 'yakshanba']
                oy = oylar[today_dt.month - 1]
                hafta_kuni = kunlar[today_dt.weekday()]
                sana_str = f"{today_dt.day}-{oy}, {hafta_kuni}  [ {today_dt.strftime('%d.%m.%Y')} ]"
                
                start_dt = datetime.strptime(safe_start_date, '%Y-%m-%d')
                challenge_kuni = (today_dt.date() - start_dt.date()).days + 1
                
                # Asosiy xabar
                msg = f"Bugun: {sana_str}\nkun: {challenge_kuni}\n"
                
                if safe_end_date and safe_end_date.strip():
                    end_dt = datetime.strptime(safe_end_date, '%Y-%m-%d')
                    remaining_days = (end_dt.date() - today_dt.date()).days
                    
                    if remaining_days > 0:
                        msg += f"Maqsadingizga erishish uchun {remaining_days} kun qoldi\n"
                    else:
                        msg += "✅ Challenge tugagan!\n"
                
                msg += f"\n{safe_message}"
            await self.bot.send_message(chat_id=channel_id, text=msg)
            logger.info(f"Xabar yuborildi: {channel_id} - {schedule_id}")
        except Exception as e:
            logger.error(f"Xabar yuborilmadi: {e}")

    def remove_schedule_job(self, user_id: int, channel_id: str, time: str):
        job_id = f"{user_id}_{channel_id}_{time}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Reja o'chirildi: {job_id}")
        except:
            logger.warning(f"Reja topilmadi: {job_id}")
    
    def get_jobs(self):
        return self.scheduler.get_jobs()
    
    def shutdown(self):
        self.scheduler.shutdown() 