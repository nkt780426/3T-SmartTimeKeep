import requests
from datetime import datetime

from utils.AppLogger import AppLogger
from utils.ConfigLoader import ConfigLoader
from utils.date import get_time_period, is_weekend

# Check timekeep để biết ai đó tháng này quên/đã checkin/out ngày nào.

class TimeKeepService:
    
    def __init__(self, app_config: ConfigLoader):
        self.logger = AppLogger.get_logger(self.__class__.__name__)
        self.app_config = app_config
        
    
    def _get_access_key(self, user_id: str) -> tuple[int, str]:
        try:
            headers = {
                "Content-Type": "application/json-patch+json",
                "Accept": "text/plain",
                "abp.tenantid": "1",
                "Origin": "https://timekeep.mobifi.vn",
                "Referer": "https://timekeep.mobifi.vn/",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
                "X-Requested-With": "XMLHttpRequest",
            }

            data = {
                "userNameOrEmailAddress": user_id,
                "password": user_id,
                "loginByCode": True,
                "rememberClient": False,
                "singleSignIn": False,
                "returnUrl": None
            }

            res = requests.post(self.app_config.get('timekeep').get('authorization'), json=data, headers=headers)

            return res.status_code, res.json()['result']['accessToken']
        
        except Exception as e:
            self.logger.error(f"Error in __get_access_key: {repr(e)}")
            raise Exception(f"Error in __get_access_key: {repr(e)}")
    
    
    # Hàm chính của service
    def _get_current_month_status_in_timekeep(self, user_id: str, run_date: datetime) -> dict:
        try: 
            current_year = int(run_date.year)
            current_month = int(run_date.month)
            current_day_in_month = int(run_date.day)
            
            code, access_token = self._get_access_key(user_id)
            if code != 200:
                raise Exception(f"Lỗi khi lấy access token, status code: {code}")
            
            headers = {
                "authorization": f"Bearer {access_token}"
            }


            data = {
                "viewYear": current_year,
                "viewMonth": current_month
            }

            res = requests.post(self.app_config.get('timekeep').get('get_data'), json=data, headers=headers)
            if res.status_code != 200:
                raise Exception(f"Lỗi khi lấy dữ liệu tháng, status code: {code}")
            
            status = {}
            for day in res.json()['result']:
                if day['dayInMonth'] > current_day_in_month:
                    continue
                
                # Khong tinh ngay hoi nang xuat, thu 7 va chu nhat
                if is_weekend(datetime(current_year, current_month, day['dayInMonth'])):
                    continue
                
                status_day = {
                    "checkInTime": day['checkInTime'],
                    "checkOutTime": day['checkOutTime']
                }
                
                status[day['dayInMonth']] = status_day
                
            return dict(sorted(status.items(), key=lambda x: x[0]))
            
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy báo cáo tháng của {user_id}: {repr(e)}")
            raise Exception(f"Lỗi khi lấy báo cáo tháng của {user_id}: {repr(e)}")


    # Phát hiện link timekeeper dead
    def get_status_of_link(self) -> bool:
        try:
            self._get_current_month_status_in_timekeep("NV150", datetime.now())
            return True
        except Exception as e:
            self.logger.error(f"Link dead detected in get_status_of_link: {repr(e)}")
            return False
    
    
    # Thực hiện gọi hàm này sau mỗi khi check bằng google form sẽ cho ra kết quả tổng kết 
    def get_month_status(self, user_id: str, run_date:datetime, remove_days: list = None) -> dict:
        '''
            "remove_days": list[int]  # các ngày trong tháng không cần checkin/out
        }
        '''
        try:
            res = {}
            status = self._get_current_month_status_in_timekeep(user_id, run_date)
            
            current_day_in_month = int(run_date.day)
            time_period = get_time_period(run_date)
            
            for day, status_of_day in status.items():
                # Bỏ qua các ngày không cần chấm công
                if remove_days:
                    day_datetime = datetime(run_date.year, run_date.month, day).date()
                    if day_datetime in remove_days:
                        continue
                
                if is_weekend(datetime(run_date.year, run_date.month, day)):
                    continue
                
                missing = []  # danh sách các mục thiếu
                
                # Nếu chưa check in
                if status_of_day.get("checkInTime") is None:
                    missing.append("check in")

                # Nếu chưa check out
                if status_of_day.get("checkOutTime") is None:
                    if day < current_day_in_month:
                        missing.append("check out")
                        
                    # chỉ sau 12h mới thêm check out hôm nay
                    elif day == current_day_in_month and not time_period:
                        missing.append("check out")

                # Ghép chuỗi kết quả
                tmp = " & ".join(missing) if missing else None
                if tmp:
                    res[datetime(run_date.year, run_date.month, day).date()] = tmp
            
            return dict(sorted(res.items(), key=lambda x: x[0]))

        except Exception as e:
            self.logger.error(f"Lỗi khi lấy báo cáo tháng của {user_id}: {repr(e)}")
            raise Exception(f"Lỗi khi lấy báo cáo tháng của {user_id}: {repr(e)}")
        
        