from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    JobQueue
)
from utils.ConfigLoader import ConfigLoader
from utils.date import is_weekend
from services.MessageHandlerService import MessageHandlerService
from services.SchedulerReport import SchedulerReport
from datetime import datetime, time as dtime, timedelta, timezone


class TelegramBotController:
    def __init__(self):
        self.app_config = ConfigLoader('./conf.yaml')
        self.application = (
            ApplicationBuilder()
            .token(self.app_config.get("telegram").get("bot_token"))
            .job_queue(JobQueue())
            .build()
        )
        self.message_handler_service = MessageHandlerService(self.app_config)
        self.scheduler_report_service = SchedulerReport(self.app_config)
        self._setup_daily_job()
        self._setup_handlers()


    def _setup_handlers(self):
        # Lệnh /start
        self.application.add_handler(CommandHandler("start", self.start))
        # Đọc tin nhắn text thường
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.response_message))


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Xin chào! Tôi là bot của bạn 👋")
    

    async def response_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name 
        telegram_username = f"{first_name} {last_name}"
        text = update.message.text.lower()
        try:    
            response_message = self.message_handler_service.handle_message(telegram_username, text)
            await update.message.reply_text(response_message)
        except Exception as e:
            await update.message.reply_text('Từ từ em nói nhanh quá anh không theo kịp. Nói lại đi em.')


    def _setup_daily_job(self):
        VN_TZ = timezone(timedelta(hours=7))
        
        # xóa state của các job nếu vào ngày mùng 1 hàng tháng
        self.application.job_queue.run_daily(
            self._monthly_clear_job_states,
            time=dtime(hour=7, minute=0, tzinfo=VN_TZ),
            days=(0, 1, 2, 3, 4, 5, 6),
            name="monthly_clear_job_states"
        )
        
        # check link status moi 7h30 sang
        self.application.job_queue.run_daily(
            self._daily_check_link_status,
            time=dtime(hour=7, minute=30, tzinfo=VN_TZ),
            days=(0, 1, 2, 3, 4, 5, 6),
            name="daily_report_link_status"
        )
        
        # auto check in luc 7h50 den 7h55 (mỗi người được random check)
        self.application.job_queue.run_daily(
            self._daily_auto_check_in_out,
            time=dtime(hour=7, minute=50, tzinfo=VN_TZ),
            days=(0, 1, 2, 3, 4, 5, 6),
            name="auto_check_in"
        )
        
        # double check all in/out moi 7h56 phut sang
        self.application.job_queue.run_daily(
            self._daily_check_all_in_out,
            time=dtime(hour=7, minute=56, tzinfo=VN_TZ),
            days=(0, 1, 2, 3, 4, 5, 6),
            name="daily_report_check_in"
        )
        
        # auto check out luc 17h01 chieu den 17h06
        self.application.job_queue.run_daily(
            self._daily_auto_check_in_out,
            time=dtime(hour=17, minute=1, tzinfo=VN_TZ),
            days=(0, 1, 2, 3, 4, 5, 6),
            name="auto_check_out"
        )
        
        # double check all in/out moi 17h07 phut chieu
        self.application.job_queue.run_daily(
            self._daily_check_all_in_out,
            time=dtime(hour=17, minute=7, tzinfo=VN_TZ),
            days=(0, 1, 2, 3, 4, 5, 6),
            name="daily_report_check_out"
        )
        
    # Đã test thành công
    async def _daily_auto_check_in_out(self, context: ContextTypes.DEFAULT_TYPE):
        """Job chạy hằng ngày"""
        try:
            if is_weekend(datetime.now()):
                return
            await self.scheduler_report_service.auto_check_in_out(datetime.now())
        except Exception as e:
            await context.bot.send_message(
                chat_id=self.app_config.get("telegram").get("chat_id"),
                text=f"⚠️ Lỗi khi đang tự động check in/out cho em: \n{repr(e)}"
            )
    
    # Đã test thành công
    async def _daily_check_link_status(self, context: ContextTypes.DEFAULT_TYPE):
        """Job chạy hằng ngày"""
        try:
            if is_weekend(datetime.now()):
                return
            self.app_config = ConfigLoader('./conf.yaml')
            await context.bot.send_message(
                chat_id=self.app_config.get("telegram").get("chat_id"),
                text=await self.scheduler_report_service.check_link_status()
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=self.app_config.get("telegram").get("chat_id"),
                text=f"⚠️ Lỗi khi kiểm tra trạng thái link:\n{repr(e)}"
            )

    # Đã test thành công
    async def _daily_check_all_in_out(self, context: ContextTypes.DEFAULT_TYPE):
        """Job chạy hằng ngày"""
        try:
            if is_weekend(datetime.now()):
                return
            await context.bot.send_message(
                chat_id=self.app_config.get("telegram").get("chat_id"),
                text=self.scheduler_report_service.check_all_in_out()
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=self.app_config.get("telegram").get("chat_id"),
                text=f"⚠️ Lỗi khi đang kiểm tra check in/out cho em:\n{repr(e)}"
            )
    
    # Xong
    async def _monthly_clear_job_states(self, context: ContextTypes.DEFAULT_TYPE):
        """Job chạy vào ngày mùng 1 hàng tháng để xóa state của các job"""
        try:
            if datetime.now().day != 1:
                return
            await self.scheduler_report_service.clear_job_states(datetime.now())
        except Exception as e:
            await context.bot.send_message(
                chat_id=self.app_config.get("telegram").get("chat_id"),
                text=f"⚠️ Lỗi khi xóa state hàng tháng:\n{repr(e)}"
            )


    def run(self):
        print("🚀 Telegram bot is running...")
        self.application.run_polling()
