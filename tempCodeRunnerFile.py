
    def run(self):
        async def start_bot():
            await self.setup_scheduler()
            await self.application.initialize()
            await self.application.start()
            self.application.run_polling()
            await self.application.stop()