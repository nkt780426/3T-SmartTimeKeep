from playwright.async_api import async_playwright
import time
import random
import asyncio

from utils.AppLogger import AppLogger
from utils.ConfigLoader import ConfigLoader

class GoogleFormService:
    
    def __init__(self, app_config: ConfigLoader):
        self.logger = AppLogger.get_logger(self.__class__.__name__)
        self.app_config = app_config

    # Hàm điền form
    async def submit_form(self, form_data: dict) -> bool:
        """
        form_data: dict
        Ví dụ:
        {
            1: {
                "Mã nhân viên": "NV1224",   # Điền text
                "User name": "Tsld",        ## Điền text
                "Phòng ban": "D&A",         # radio
                "User teamlead": "KienVQ - Vũ Quốc Kiên", # radio
                "Ca làm việc": "Fulltime", # # radio
            },
            2: {
                "Bạn muốn ?": "Check in", # radio
            },
            3: {
                "Loại chấm công - Check in?": "Onsite" # radio
            },
            4: {
                "Địa điểm": "số 5, ngõ 82, Duy Tân, Cầu Giấy, Hà Nội (quãng đường 2km)" # radio
            },
            5: {
                "1+2=? (Điền số)": "3" # Điền text
            }
        }
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ]
                )

                context = await browser.new_context()
                page = await context.new_page()

                await page.goto(self.app_config.get("google_from"), wait_until="networkidle")

                for page_number in sorted(form_data.keys()):
                    self.logger.info(f"Điền dữ liệu trang {page_number} ...")
                    for label, value in form_data[page_number].items():
                        locator = page.get_by_label(label)
                        if await locator.count() == 0:
                            raise ValueError(f"Label '{label}' không tồn tại")

                        option = page.get_by_role("radio", name=value)
                        if await option.count() > 0:
                            await option.first.click()
                        else:
                            await locator.fill(value)

                        await asyncio.sleep(random.uniform(2, 3))

                    next_buttons = page.locator('div[role="button"]:has-text("Tiếp")')
                    if await next_buttons.count() > 0:
                        await next_buttons.first.click()
                        await page.wait_for_load_state("networkidle")

                submit_buttons = page.locator('//div[@role="button"][.//span[contains(normalize-space(.), "Gư")]]')
                if await submit_buttons.count() == 0:
                    submit_buttons = page.locator('//div[@role="button"][.//span[contains(text(), "Submit")]]')

                if await submit_buttons.count() == 0:
                    raise RuntimeError("Không tìm thấy nút Gửi")

                await submit_buttons.first.click()
                await page.wait_for_load_state("networkidle")

                await browser.close()


        except Exception as e:
            self.logger.error(f"Lỗi khi kiểm tra form: {repr(e)}")
            return False
    
    # Kiểm tra cấu trúc form ko đổi 
    async def get_status_of_link(self):
        try:
            fake_data = {
                1: {
                    "User name": "NV122",        ## Điền text
                    "Phòng ban": "Data & AI (D&A)",         # radio
                    "User teamlead": "KienVQ - Vũ Quốc Kiên", # radio
                },
                2: {
                    "Bạn muốn ?": "Check in", # radio
                },
                3:{
                    "Ca làm việc": "Fulltime (Ca hành chính 8 tiếng)", # # radio
                },
                4: {
                    "Loại chấm công - Check in?": "Onsite" # radio
                },
                5: {
                    "Địa điểm": "số 5, ngõ 82, Duy Tân, Cầu Giấy, Hà Nội (quãng đường 2km)" # radio
                },
                6: {
                    "1+9=? (Điền số)": "10" # Điền text
                }
            }
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto(self.app_config.get("google_from"))
                await page.wait_for_timeout(2000)

                self.logger.info("🔍 Đang quét toàn bộ label trên form...")

                # Duyệt từng trang
                for page_number in sorted(fake_data.keys()):
                    self.logger.info(f"Điền dữ liệu trang {page_number} ...")
                    for label, value in fake_data[page_number].items():
                        # Lấy locator theo label
                        locator = page.get_by_label(label)
                        try:
                            await locator.wait_for(state="visible", timeout=3000)
                        except Exception:
                            self.logger.error(f"⚠️ Không tìm thấy label: {label}")
                            return False
                            
                        # Kiểm tra radio hay text
                        option = page.get_by_role("radio", name=value)
                        if await option.count() > 0:
                            await option.first.click()
                        else:
                            # Nếu không có radio thì coi là text input
                            await locator.fill(value)

                        await asyncio.sleep(random.uniform(2, 3))

                    # Nhấn nút Next nếu chưa phải trang cuối
                    next_buttons = page.locator('div[role="button"]:has-text("Tiếp")')
                    if await next_buttons.count() > 0:
                        await next_buttons.first.click()
                        await page.wait_for_timeout(1000)  # đợi trang mới load

                await browser.close()
                self.logger.info("✅ Đã quét xong toàn bộ nhãn form.")
                return True

        except Exception as e:
            self.logger.error(f"Lỗi khi kiểm tra form: {repr(e)}")
            return False