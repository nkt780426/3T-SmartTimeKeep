from utils.ConfigLoader import ConfigLoader
from utils.AppLogger import AppLogger

from services.GoogleFormService import GoogleFormService
from services.TimeKeepService import TimeKeepService

from datetime import datetime, timedelta
import sys
import traceback

class MessageHandlerService:
    
    def __init__(self, app_config: ConfigLoader):
        self.logger = AppLogger.get_logger(self.__class__.__name__)
        self.state_service = ConfigLoader('./state.yaml')
        self.app_config = app_config
        
        self.googleFormService = GoogleFormService(app_config)
        self.timeKeepService = TimeKeepService(app_config)
    
    
    def handle_message(self, telegram_name: str, request_message: str):
        '''
            Xử lý tin nhắn từ người dùng Telegram và trả về nội dung tin nhắn phản hồi.
            o 12,13,1/1/2026,t2,t4 (tu onboard, check in/out tai cong ty)

            d 12 (xoa thong bao ngay nay khoi bao cao hang thang)

            s (state = tu dong kiem tra check in/out trong thang cua nguoi nhan)

            c (check = kiem tra cau hinh hien tai cua nguoi nay)
        '''
        
        if telegram_name not in self.app_config.get('telegram').get('user_map'):
            self.logger.error(f"Unknown telegram user: {telegram_name} not map {self.app_config.get('telegram').get('user_map')}")
            return "Xin lỗi anh không biết em là ai. Vui lòng đăng ký với bộ phận nhân sự nhé."
        
        try:
            command_code, request_dates = self._decode_request_message(request_message)
        except Exception as e:
            print(repr(e))
            traceback.print_exc()
            return f'Từ từ em nói nhanh quá anh không theo kịp. Nói lại theo format đi em.'
        
        if command_code == 'o':
            try:
                return self._onboard_action(telegram_name, request_dates)
            except Exception as e:
                print(repr(e))
                traceback.print_exc()
                return f'Lỗi khi thêm ngày vào cấu hình onboard.'
        elif command_code == 'r':
            try:
                return self._remove_action(telegram_name, request_dates)
            except Exception as e:
                print(repr(e))
                traceback.print_exc()
                return f'Lỗi khi xóa ngày khỏi cấu hình theo dõi timekeep.'
        elif command_code == 's':
            try:
                return self._status_action(telegram_name)
            except Exception as e:
                print(repr(e))
                traceback.print_exc()
                return f'Lỗi khi kiểm tra trạng thái cấu hình của {telegram_name}.'
        elif command_code == 'c':
            try:
                return self._check_action(telegram_name)
            except Exception as e:
                print(repr(e))
                traceback.print_exc()
                return f'Lỗi khi kiểm tra tình trạng check in/out của {telegram_name} trong tháng này.'
            
        elif command_code == 'd':
            try:
                return self._delete_action(telegram_name)
            except Exception as e:
                print(repr(e))
                traceback.print_exc()
                return f'Lỗi khi xóa toàn bộ cấu hình.'
        elif command_code == 'e':
            try:
                return self._turn_off_bot_action()
            except Exception as e:
                print(repr(e))
                traceback.print_exc()
                return f'Lỗi khi turn off job.\n{repr(e)}'
        else:
            return 'Anh đang không hiểu lệnh em nói gì. Nói lại đi em.'
    
        
    def _decode_request_message(self, request_message: str) -> tuple[str, list[datetime]]:
        num_spaces = request_message.strip().count(' ')
        if num_spaces > 1:
            raise ValueError('Định dạng tin nhắn không đúng: nhiều hơn 1 dấu cách giữa các phần')
        elif num_spaces == 0:
            return request_message.strip().lower(), []
        else:
            command_code, dates_part = request_message.strip().split(' ')
            
            date_strs = dates_part.split(',')
            request_dates: list[datetime.date] = []
            today = datetime.now()
            today_weekday = today.weekday()
            
            for date_str in date_strs:
                if date_str.lower().startswith('t'):
                    try:
                        weekday_num = int(date_str[1:])
                        if not 2 <= weekday_num <= 8:
                            raise ValueError(f"Invalid weekday: {date_str}")
                        weekday_num = weekday_num - 2  # Chuyển t2 -> 0 (thứ 2)
                        
                        # nếu ngày yêu cầu đã qua hoặc là hôm nay -> chọn tuần sau
                        diff = weekday_num - today_weekday
                        if diff <= 0:
                            diff += 7
                        target_date = (today + timedelta(days=diff)).date()
                        request_dates.append(target_date)
                    except Exception:
                        raise ValueError(f"Invalid weekday token: {date_str}")
                elif '/' in date_str:
                    try:
                        day, month, year = map(int, date_str.split("/"))
                        request_dates.append(datetime(year, month, day).date())
                    except ValueError:
                        raise ValueError(f"Invalid date format: {date_str}")
                else:
                    try:
                        day = int(date_str)
                        month = today.month
                        year = today.year
                        request_dates.append(datetime(year, month, day).date())
                    except ValueError:
                        raise ValueError(f"Invalid day format: {date_str}")
            
            return command_code.lower(), request_dates
                
    # Xong
    def _onboard_action(self, telegram_user: str, request_dates: list[datetime]):
        user_states =self.state_service.get('user_states')
        
        if telegram_user not in user_states:
            user_states[telegram_user] = {
                'on_board': request_dates,
                'remove_days': []
            }
        else:
            existing_onboard_dates = user_states[telegram_user].get('on_board', [])
            for date in request_dates:
                if date not in existing_onboard_dates:
                    existing_onboard_dates.append(date)
            user_states[telegram_user]['on_board'] = existing_onboard_dates
            
        self.state_service.save_config()
        self.logger.info(f'User {telegram_user} added onboard dates: {request_dates}')
        return 'Đã thêm các ngày vào cấu hình onboard.'
  
    # Xong
    def _remove_action(self, telegram_user: str, request_dates: list[datetime]):
        user_states =self.state_service.get('user_states')
        
        if telegram_user not in user_states:
            user_states[telegram_user] = {
                'on_board': [],
                'remove_days': request_dates
            }
        else:
            existing_remove_dates = user_states[telegram_user].get('remove_days', [])
            for date in request_dates:
                if date not in existing_remove_dates:
                    existing_remove_dates.append(date)
            user_states[telegram_user]['remove_days'] = existing_remove_dates
    
        self.state_service.save_config()
        self.logger.info(f'User {telegram_user} added remove days: {request_dates}')
        return 'Đã thêm các ngày vào cấu hình không theo dõi timekeep.'
        
    # Xong   
    def _status_action(self, telegram_user):
        user_states =self.state_service.get('user_states')
        
        if telegram_user not in user_states:
            user_states[telegram_user] = {
                'on_board': [],
                'remove_days': []
            }
        count_on_boards = len(user_states[telegram_user].get('on_board', []))
        count_remove_days = len(user_states[telegram_user].get('remove_days', []))
        
        gender = self.app_config.get('telegram').get('user_map').get(telegram_user).get('gender')
        
        if count_on_boards == 0 and count_remove_days == 0:
            return f"{gender} {telegram_user} chưa có cấu hình onboard và ngày xóa thông báo nào. Tháng này tôi sẽ tự động check in/out onsite mọi ngày cho {str(gender).lower()}."
        elif count_on_boards == 0 and count_remove_days > 0:
            response_message =  f"{gender} {telegram_user} đã cấu hình không theo dõi timekeep các ngày.\n"
            
            for day in user_states[telegram_user].get('remove_days'):
                response_message += f"- {day.strftime('%d/%m/%Y')}\n"
            
            response_message += "Chủ động theo dõi các ngày trên"
            
            self.state_service.save_config()
            self.logger.info(f'User {telegram_user} checked status.')
            return response_message
        
        elif count_on_boards > 0 and count_remove_days == 0:
            response_message =  f"{gender} {telegram_user} đã cấu hình onboard các ngày.\n"
            
            for day in user_states[telegram_user].get('on_board'):
                response_message += f"- {day.strftime('%d/%m/%Y')}\n"

            response_message += "Chủ động check in/out các ngày trên"
            
            self.state_service.save_config()
            self.logger.info(f'User {telegram_user} checked status.')
            return response_message
        else:
            response_message =  f"Các ngày cấu hình onboard\n"
            for day in user_states[telegram_user].get('on_board'):
                response_message += f"- {day.strftime('%d/%m/%Y')}\n"
            response_message += "Chủ động check in/out các ngày trên\n\n"

            response_message +=  f"Các ngày cấu hình xóa thông báo\n"
            for day in user_states[telegram_user].get('remove_days'):
                response_message += f"- {day.strftime('%d/%m/%Y')}\n"
            response_message += "Chủ động check timekeep các ngày trên"

            self.state_service.save_config()
            self.logger.info(f'User {telegram_user} checked status.')
            return response_message

    # Xong
    def _check_action(self, telegram_user: str):
        status_check_in_out = self.timeKeepService.get_month_status(
            self.app_config.get('telegram').get('user_map').get(telegram_user).get('ma_nhan_vien'), 
            datetime.now(), 
            self.state_service.get('user_states').get(telegram_user).get('remove_days')
        )
        
        if len(status_check_in_out) == 0:
            self.logger.info(f'User {telegram_user} checked status.')
            return f"Em đã chấm công đầy đủ trong tháng này."
        else:
            response_message = f"Em còn thiếu chấm công các ngày sau trong tháng này:\n"
            for day, missing in status_check_in_out.items():
                response_message += f"   - Ngày {day.day}/{day.month}/{day.year}: Thiếu {missing}\n"
            response_message += "Chú ý chấm công đầy đủ nhé!"
            self.logger.info(f'User {telegram_user} checked status with missing days.')
            return response_message
    
    # Xong 
    def _delete_action(self, telegram_user: str):
        user_states =self.state_service.get('user_states')
        
        user_states[telegram_user] = {
            'on_board': [],
            'remove_days': []
        }
        self.state_service.save_config()
        self.logger.info(f'User {telegram_user} deleted all configurations.')
        return 'Đã xóa toàn bộ cấu hình'
        
    def _turn_off_bot_action(self):
        """Turn off the bot by deleting the job"""
        self.logger.info('Turning off the bot.')
        sys.exit(0)