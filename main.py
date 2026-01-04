from controllers.TelegramBotController import TelegramBotController

if __name__ == "__main__":
    TelegramBotController().run()
    
# if __name__ == "__main__":
#     from services.GoogleFormService import GoogleFormService
#     import asyncio
#     from utils.ConfigLoader import ConfigLoader
    
#     app_config = ConfigLoader('conf.yaml')
    
#     googleFormService = GoogleFormService(app_config)
    
#     form_data = {
#             1: {
#                 "User name": 'PhongHT',
#                 "Phòng ban": 'Data & AI (D&A)',
#                 "User teamlead": 'KienVQ - Vũ Quốc Kiên',
#             },
#             2: {
#                 "Bạn muốn ?": "Check in",
#             },
#             3:{
#                 "Ca làm việc": 'Fulltime (Ca hành chính 8 tiếng)'
#             },
#             4: {
#                 "Loại chấm công - Check in?": "Onsite"
#             },
#             5: {
#                 "Địa điểm": 'số 5, ngõ 82, Duy Tân, Cầu Giấy, Hà Nội (quãng đường 2km)'
#             },
#             6: {
#                 "1+9=? (Điền số)": '10'
#             }
#         }
        
#     # asyncio.run(googleFormService.submit_form(form_data))
    
#     print(asyncio.run(googleFormService.get_status_of_link()))