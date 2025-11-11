from datetime import datetime


def get_time_period(date: datetime) -> bool:
    """
    Trả về:
        True  -> buổi sáng (trước 12h trưa)
        False -> buổi chiều (sau hoặc bằng 12h)
    """
    return date.hour < 12

def is_weekend(date: datetime) -> bool:
    """
    Kiểm tra xem hôm nay có phải ngày cuối tuần không
    Trả về:
        True  -> là ngày cuối tuần (Thứ 7 hoặc Chủ Nhật)
        False -> không phải ngày cuối tuần
    """
    return date.weekday() in (5, 6)  # 5 = Thứ 7, 6 = Chủ Nhật
    
    