from unittest import result
from controllers.TelegramBotController import TelegramBotController
from services.TimeKeepService import TimeKeepService
from utils.ConfigLoader import ConfigLoader
    
if __name__ == "__main__":
    TelegramBotController().run()