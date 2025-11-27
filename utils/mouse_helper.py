# utils/mouse_helper.py
import random
import asyncio
from playwright.async_api import Page

def bezier_curve(p0, p1, p2, p3, steps=20):
    """Tạo đường cong Bézier bậc 3"""
    path = []
    for t in range(steps + 1):
        t /= steps
        # Công thức Bézier cubic
        x = (1-t)**3*p0[0] + 3*(1-t)**2*t*p1[0] + 3*(1-t)*t**2*p2[0] + t**3*p3[0]
        y = (1-t)**3*p0[1] + 3*(1-t)**2*t*p1[1] + 3*(1-t)*t**2*p2[1] + t**3*p3[1]
        path.append((x, y))
    return path

async def human_move(page: Page, target_x: float, target_y: float):
    """
    Di chuyển chuột từ vị trí hiện tại đến đích theo đường cong ngẫu nhiên.
    """
    # Vì Playwright không cho biết vị trí chuột hiện tại, ta phải ước lượng 
    # hoặc giả định từ vị trí giữa màn hình nếu chưa có dữ liệu.
    # Để đơn giản, ta random điểm bắt đầu trong vùng an toàn nếu đây là lần đầu.
    start_x = random.randint(100, 1000)
    start_y = random.randint(100, 800)
    
    # Tạo 2 điểm điều khiển (Control Points) để bẻ cong đường đi
    # Random độ lệch để đường cong luôn khác nhau
    control1 = (start_x + random.randint(-300, 300), start_y + random.randint(-300, 300))
    control2 = (target_x + random.randint(-300, 300), target_y + random.randint(-300, 300))
    
    # Tính toán đường đi
    steps = random.randint(25, 50) # Số bước di chuyển (càng cao càng mượt nhưng chậm)
    path = bezier_curve((start_x, start_y), control1, control2, (target_x, target_y), steps=steps)
    
    # Thực hiện di chuyển
    for point in path:
        await page.mouse.move(point[0], point[1])
        # Giả lập gia tốc: Nhanh ở giữa, chậm dần ở đích
        await asyncio.sleep(random.uniform(0.005, 0.015))