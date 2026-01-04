from utils.AppLogger import AppLogger
from utils.ConfigLoader import ConfigLoader
from utils.date import get_time_period

from services.GoogleFormService import GoogleFormService
from services.TimeKeepService import TimeKeepService

from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import time, random, asyncio

class SchedulerReport:
    def __init__(self, app_config: ConfigLoader):
        self.logger = AppLogger.get_logger(self.__class__.__name__)
        self.app_config = app_config
        self.state_service = ConfigLoader("state.yaml")
        self.google_form_service = GoogleFormService(app_config)
        self.time_keep_service = TimeKeepService(app_config)
    
    # Đã test thành công
    async def check_link_status(self) -> str:
        try:
            self.logger.info("Bắt đầu kiểm tra trạng thái link...")
            scheduler_message = None

            if not await self.google_form_service.get_status_of_link():
                self.state_service.set('google_link', False)
                self.state_service.save_config()
            else:
                self.state_service.set('google_link', True)
                self.state_service.save_config()

            if not self.time_keep_service.get_status_of_link():
                self.state_service.set('timekeep_link', False)
                self.state_service.save_config()
            else:
                self.state_service.set('timekeep_link', True)
                self.state_service.save_config()

            scheduler_message = "✅ Cấu trúc Google Form không đổi" if self.state_service.get('google_link') else "❌ Cấu trúc Google Form đã bị thay đổi"
            scheduler_message += "\n"
            scheduler_message += "✅ Cấu trúc Time Keep không đổi" if self.state_service.get('timekeep_link') else "❌ Cấu trúc Time Keep đã bị thay đổi"
            
            self.logger.info(f"Kết quả kiểm tra trạng thái link: {scheduler_message}")
            return scheduler_message
            
        except Exception as e:
            self.logger.error(f"Lỗi khi kiểm tra trạng thái link: {repr(e)}")
            raise e
    
    # Đã test thành công
    def _submit_for_user(self, telegram_user: str, telegram_user_data: dict):
        try:
            time.sleep(random.uniform(0, 240))  # Thêm độ trễ trước mỗi lần submit form để tránh hr nghi ngờ
            if get_time_period(datetime.now()):
                
                form_data = {
                    1: {
                        "User name": telegram_user_data['3t_name'],
                        "Phòng ban": telegram_user_data['phong_ban'],
                        "User teamlead": telegram_user_data['user_teamlead'],
                    },
                    2: {
                        "Bạn muốn ?": "Check in", 
                    },
                    3:{
                        "Ca làm việc": telegram_user_data['work_type']
                    },
                    4: {
                        "Loại chấm công - Check in?": "Onsite"
                    },
                    5: {
                        "Địa điểm": telegram_user_data['dia_diem']
                    },
                    6: {
                        "1+9=? (Điền số)": '10'
                    }
                }
            else:
                form_data = {
                    1: {
                        "User name": telegram_user_data['3t_name'],
                        "Phòng ban": telegram_user_data['phong_ban'],
                        "User teamlead": telegram_user_data['user_teamlead'],
                    },
                    2: {
                        "Bạn muốn ?": "Check out", 
                    },
                    3:{
                        "Ca làm việc": telegram_user_data['work_type']
                    },
                    4: {
                        "Loại chấm công - Check out?": "Onsite"
                    },
                    5: {
                        "Địa điểm": telegram_user_data['dia_diem']
                    },
                    6: {
                        "2+3=? (Điền số)": '5'
                    }
                }
                
            asyncio.run(self.google_form_service.submit_form(form_data))
            
            return telegram_user
        
        except Exception as e:
            self.logger.error(f"Lỗi khi kiểm tra in/out cho user {telegram_user}: {repr(e)}")
            return f"{telegram_user} (Lỗi: {repr(e)})"
        
    # Đã test thành công   
    async def auto_check_in_out(self,run_date: datetime) -> None:
        
        if not self.state_service.get('google_link'):
            return 'Hôm nay cấu trúc Google Form bị thay đổi nên anh không check in/out hộ các em được, các em chủ động nhé.'

        user_data:dict = self.app_config.get('telegram').get('user_map')
        
        auto_check_in_out_data = {}
        for telegram_user, telegram_user_data in user_data.items():
            if telegram_user not in self.state_service.get('user_states', {}):
                user_states = self.state_service.get('user_states', {})

                if telegram_user not in user_states:
                    user_states[telegram_user] = {'remove_days': [], 'on_board': []}

                # Ghi lại toàn bộ user_states vào config
                self.state_service.set('user_states', user_states)
                
                self.state_service.save_config()
                
            # Nếu ngày check_in không nằm trong danh sách on_board thì tiếp tục check in/out tự động
            if run_date in self.state_service.get('user_states').get(telegram_user).get('on_board'):
                continue 
            
            auto_check_in_out_data[telegram_user] = telegram_user_data
                
        with ProcessPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(
                    self._submit_for_user, 
                    telegram_user, 
                    telegram_user_data
                ) for telegram_user, telegram_user_data in auto_check_in_out_data.items()
            ]
            for future in as_completed(futures):
                result = future.result()
                self.logger.info(f"Kết quả check in/out cho user: {result}")
            
    # Đã test thành công
    def check_all_in_out(self) -> dict:
        try:
            self.logger.info("Bắt đầu lấy báo cáo check in/out cho moi nguoi...")
            if not self.state_service.get('timekeep_link'):
                return 'Hôm nay cấu trúc Time Keep bị thay đổi nên anh không lấy báo cáo check in/out được, các em chủ động nhé.'
            
            result = {}
            # Duyet qua tung nguoi trong conf.yaml
            for user in self.app_config.get('telegram').get('user_map'):
                try:
                    self.logger.info(f"Lấy báo cáo check in/out cho em {user}...")
                    # Neu nguoi nay khong co trong state.yaml thi tao moi.
                    if user not in self.state_service.get('user_states'):
                        user_states = self.state_service.get('user_states')

                        if user not in user_states:
                            user_states[user] = {'remove_days': [], 'on_board': []}

                        # Ghi lại toàn bộ user_states vào config
                        self.state_service.set('user_states', user_states)
                        
                        self.state_service.save_config()
                        
                    status = self.time_keep_service.get_month_status(
                        user_id=self.app_config.get('telegram').get('user_map', {}).get(user, {}).get('ma_nhan_vien'),
                        run_date=datetime.now(),
                        remove_days=self.state_service.get('user_states', {}).get(user).get('remove_days', [])
                    )
                    
                    result[user] = status or {}
                    
                    self.logger.info(f"Kết quả lấy báo cáo check in/out cho em {user}: {status}")
                except Exception as e:
                    self.logger.error(f"Lỗi khi lấy báo cáo check in/out cho em {user}: {repr(e)}")
                    raise Exception(f"{user['telegram_name']}")
            
            scheduler_response = "Tất cả các em tháng này đã chấm công đầy đủ.\n"
            not_checked_in_out = {}
            for user, status in result.items():
                if len(status) == 0:
                    scheduler_response += f"✅ {user}\n"
                else:
                    not_checked_in_out[user] = status
                    
            if len(not_checked_in_out) > 0:
                scheduler_response += "Trừ các em sau trong tháng này còn chưa chấm công các ngày:\n"
                for user, status in not_checked_in_out.items():
                    scheduler_response += f"❌ {user}:\n"
                    for day, missing in status.items():
                        scheduler_response += f"   - Ngày {day.day}/{day.month}/{day.year}: Thiếu {missing}\n"
                scheduler_response += "\nGiải trình ngay cho tôi. Các em chú ý chấm công đầy đủ nhé!"
            
            self.logger.info("Kết quả lấy báo cáo check in/out cho mọi người hoàn tất.")
            return scheduler_response
                    
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy báo cáo check in/out: {repr(e)}")
            raise e
    
    # Xong
    def clear_job_states(self, current_date: datetime):
        try:
            for user, user_data in self.state_service.get('user_states', {}).items():
                onboard_days = user_data.get('remove_days', [])
                new_onboard_days = [day for day in onboard_days if day >= current_date.date()]
                user_data['remove_days'] = new_onboard_days
                
                onboard_days = user_data.get('on_board', [])
                new_onboard_days = [day for day in onboard_days if day >= current_date.date()]
                user_data['on_board'] = new_onboard_days

            self.state_service.save_config()
            
        except Exception as e:
            self.logger.error(f"Lỗi khi xóa trạng thái công việc định kỳ: {repr(e)}")
            raise e
        