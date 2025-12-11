import os
from PIL import Image, ImageDraw

# 确保安装了 pillow: pip install pillow
# 目标目录
base_dir = "static/icons/system"
os.makedirs(base_dir, exist_ok=True)

def create_icon(name, color, shape="circle"):
    # 创建一个 64x64 的透明底图片
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 画圆或箭头
    if shape == "circle":
        draw.ellipse([4, 4, 60, 60], fill=(0, 0, 0, 150), outline="white", width=3)
        # 画文字缩写
        draw.text((20, 20), name[0].upper(), fill="white")
    elif shape == "arrow":
        # 画一个简单的箭头
        draw.polygon([(32, 4), (60, 32), (44, 32), (44, 60), (20, 60), (20, 32), (4, 32)], fill=color, outline="white", width=2)

    # 保存
    path = f"{base_dir}/{name}.png"
    img.save(path)
    print(f"✅ 生成图标: {path}")

if __name__ == "__main__":
    try:
        create_icon("arrow", "#3498db", "arrow")  # 蓝色箭头
        create_icon("info", "#e67e22", "circle")  # 橙色圆圈
        create_icon("photo", "#2ecc71", "circle") # 绿色圆圈
        print("🎉 图标生成完毕！请重启前端刷新查看。")
    except ImportError:
        print("❌ 缺少 PIL 库。请运行: pip install pillow")