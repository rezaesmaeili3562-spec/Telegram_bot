from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import json
from datetime import datetime, timedelta
import os
import re

# 🔑 توکن ربات را اینجا قرار بده
TOKEN = "8531861676:AAGefz_InVL9y4FtKYcETGAFTRHggaJCnhA"

# نام فایل ذخیره هزینه‌ها
FILE = "expenses.json"

# اگر فایل وجود ندارد ایجادش کن
if not os.path.exists(FILE):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)

# لود کردن هزینه‌ها
def load_expenses(user_id=None):
    with open(FILE, "r", encoding="utf-8") as f:
        all_expenses = json.load(f)
    
    if user_id:
        return [e for e in all_expenses if e.get("user_id") == str(user_id)]
    return all_expenses

# ذخیره هزینه‌ها
def save_expenses(expenses):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(expenses, f, ensure_ascii=False, indent=4)

# تبدیل مبلغ فارسی/انگلیسی
def parse_amount(amount_str):
    try:
        # حذف فاصله و ویرگول
        amount_str = amount_str.replace(",", "").replace(" ", "")
        
        # تبدیل کلمات فارسی
        persian_numbers = {
            "هزار": "000",
            "میلیون": "000000",
            "میلیارد": "000000000",
            "تومان": "",
            "ت": ""
        }
        
        for word, replacement in persian_numbers.items():
            amount_str = amount_str.replace(word, replacement)
        
        # تبدیل اعداد فارسی به انگلیسی
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        amount_str = amount_str.translate(persian_to_english)
        
        # حذف حروف غیرعددی
        amount_str = re.sub(r'[^\d]', '', amount_str)
        
        return int(amount_str)
    except:
        return None

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
سلام {user.first_name}! 😊
من ربات مدیریت هزینه‌های شخصی تو هستم.

📋 **دستورات موجود:**

➕ ثبت هزینه جدید:
`/add 50000 ناهار`
`/add 50هزار ناهار`
`/add ۵۰۰۰۰ ناهار`

📅 امروز: `/today`

📊 این ماه: `/month`

💰 مجموع کل: `/total`

🗑️ پاک کردن همه: `/clear`

📈 گزارش هفته: `/week`

🔍 جستجو: `/search قهوه`

💡 نکته: می‌تونی مستقیماً بنویسی:
`15000 تاکسی`
"""
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# ثبت هزینه با پیام مستقیم
async def quick_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # پیدا کردن عدد در متن
    numbers = re.findall(r'[\d,]+', text)
    if not numbers:
        return
    
    amount = parse_amount(numbers[0])
    if not amount:
        return
    
    # پیدا کردن توضیح
    description = re.sub(r'[\d,]+', '', text).strip()
    if not description:
        description = "بدون توضیح"
    
    await add_expense(update, context, amount, description)

# تابع مشترک برای ثبت هزینه
async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int, description: str):
    user_id = str(update.effective_user.id)
    
    expenses = load_expenses()
    expenses.append({
        "user_id": user_id,
        "amount": amount,
        "description": description,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "timestamp": datetime.now().isoformat()
    })
    save_expenses(expenses)
    
    await update.message.reply_text(
        f"✅ ثبت شد: *{amount:,}* تومان\n"
        f"📝: {description}\n"
        f"🕐 {datetime.now().strftime('%H:%M')}",
        parse_mode="Markdown"
    )

# /add
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً مبلغ و توضیح وارد کن:\n`/add 50000 ناهار`", parse_mode="Markdown")
        return
    
    amount = parse_amount(context.args[0])
    if not amount:
        await update.message.reply_text("❌ مبلغ نامعتبر!\nمثال: `/add 50000 ناهار` یا `/add 50هزار ناهار`", parse_mode="Markdown")
        return
    
    description = " ".join(context.args[1:]) if len(context.args) > 1 else "بدون توضیح"
    
    await add_expense(update, context, amount, description)

# /today
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = load_expenses(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    today_list = [e for e in expenses if e["date"] == today]
    
    if not today_list:
        await update.message.reply_text("🎉 امروز هیچ هزینه‌ای ثبت نکردی!")
        return
    
    total = sum(e["amount"] for e in today_list)
    avg = total / len(today_list)
    
    text = f"📅 *هزینه‌های امروز ({today})*\n\n"
    for i, e in enumerate(today_list, 1):
        text += f"{i}. {e['amount']:,} تومان - {e['description']} ({e['time']})\n"
    
    text += f"\n📊 *آمار امروز:*\n"
    text += f"• تعداد: {len(today_list)}\n"
    text += f"• مجموع: {total:,} تومان\n"
    text += f"• میانگین: {avg:,.0f} تومان\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

# /week
async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = load_expenses(user_id)
    
    week_ago = datetime.now() - timedelta(days=7)
    week_list = []
    
    for e in expenses:
        exp_date = datetime.strptime(e["date"], "%Y-%m-%d")
        if exp_date >= week_ago:
            week_list.append(e)
    
    if not week_list:
        await update.message.reply_text("هفته گذشته هیچ هزینه‌ای ثبت نکردی! 💰")
        return
    
    # گروه‌بندی بر اساس روز
    days = {}
    for e in week_list:
        day = e["date"]
        if day not in days:
            days[day] = []
        days[day].append(e)
    
    total = sum(e["amount"] for e in week_list)
    avg = total / len(week_list)
    
    text = "📈 *گزارش هفته گذشته*\n\n"
    
    for day, day_expenses in sorted(days.items()):
        day_total = sum(e["amount"] for e in day_expenses)
        text += f"📅 {day} ({len(day_expenses)} مورد): {day_total:,} تومان\n"
    
    text += f"\n📊 *جمع هفته:*\n"
    text += f"• تعداد کل: {len(week_list)}\n"
    text += f"• مجموع: {total:,} تومان\n"
    text += f"• میانگین روزانه: {avg:,.0f} تومان\n"
    text += f"• میانگین در روز: {(total/7):,.0f} تومان"
    
    await update.message.reply_text(text, parse_mode="Markdown")

# /month
async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = load_expenses(user_id)
    month_key = datetime.now().strftime("%Y-%m")
    
    month_list = [e for e in expenses if e["date"].startswith(month_key)]
    
    if not month_list:
        await update.message.reply_text(f"هیچ هزینه‌ای برای ماه {month_key} ثبت نشده 📅")
        return
    
    # گروه‌بندی بر اساس دسته (بر اساس کلمات کلیدی)
    categories = {}
    for e in month_list:
        # پیدا کردن دسته ساده
        desc_lower = e["description"].lower()
        category = "دیگر"
        
        if any(word in desc_lower for word in ["غذا", "ناهار", "شام", "صبحانه"]):
            category = "غذا"
        elif any(word in desc_lower for word in ["حمل", "تاکسی", "اسنپ", "اتوبوس"]):
            category = "حمل‌ونقل"
        elif any(word in desc_lower for word in ["خرید", "سوپرمارکت", "بازار"]):
            category = "خرید"
        elif any(word in desc_lower for word in ["قهوه", "کافه"]):
            category = "کافه"
        elif any(word in desc_lower for word in ["پزشک", "دارو", "درمان"]):
            category = "سلامت"
        
        if category not in categories:
            categories[category] = 0
        categories[category] += e["amount"]
    
    total = sum(e["amount"] for e in month_list)
    avg = total / len(month_list)
    
    text = f"📊 *هزینه‌های ماه {month_key}*\n\n"
    
    for e in month_list[-15:]:  # نمایش ۱۵ مورد آخر
        text += f"• {e['amount']:,} تومان - {e['description']} ({e['date']})\n"
    
    text += f"\n💰 *جمع ماه: {total:,} تومان*\n"
    text += f"📈 میانگین هر خرید: {avg:,.0f} تومان\n"
    text += f"📝 تعداد خریدها: {len(month_list)}\n"
    
    text += "\n🎯 *دسته‌بندی هزینه‌ها:*\n"
    for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percent = (amount / total) * 100
        text += f"• {cat}: {amount:,} تومان ({percent:.1f}%)\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

# /search
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً کلمه جستجو رو وارد کن:\n`/search قهوه`", parse_mode="Markdown")
        return
    
    user_id = str(update.effective_user.id)
    expenses = load_expenses(user_id)
    
    keyword = " ".join(context.args).lower()
    results = [e for e in expenses if keyword in e["description"].lower()]
    
    if not results:
        await update.message.reply_text(f"نتیجه‌ای برای '{keyword}' پیدا نشد 🔍")
        return
    
    total = sum(e["amount"] for e in results)
    
    text = f"🔍 *نتایج جستجو برای '{keyword}'*\n\n"
    
    for i, e in enumerate(results[-10:], 1):  # نمایش ۱۰ مورد آخر
        text += f"{i}. {e['amount']:,} تومان - {e['description']} ({e['date']})\n"
    
    text += f"\n💰 مجموع: {total:,} تومان\n"
    text += f"📝 تعداد: {len(results)} مورد"
    
    if len(results) > 10:
        text += f"\n\n📌 فقط ۱۰ مورد آخر نمایش داده شد"
    
    await update.message.reply_text(text, parse_mode="Markdown")

# /total
async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = load_expenses(user_id)
    
    if not expenses:
        await update.message.reply_text("هنوز هیچ هزینه‌ای ثبت نکردی! 💰")
        return
    
    total = sum(e["amount"] for e in expenses)
    avg = total / len(expenses)
    
    # قدیمی‌ترین و جدیدترین
    dates = [datetime.strptime(e["date"], "%Y-%m-%d") for e in expenses]
    oldest = min(dates).strftime("%Y-%m-%d")
    newest = max(dates).strftime("%Y-%m-%d")
    
    text = "💰 *گزارش کلی هزینه‌ها*\n\n"
    text += f"📅 از {oldest} تا {newest}\n"
    text += f"📝 تعداد کل: {len(expenses)}\n"
    text += f"💰 مجموع کل: {total:,} تومان\n"
    text += f"📊 میانگین هر خرید: {avg:,.0f} تومان\n"
    
    if len(expenses) > 0:
        # بیشترین و کمترین هزینه
        max_exp = max(expenses, key=lambda x: x["amount"])
        min_exp = min(expenses, key=lambda x: x["amount"])
        
        text += f"\n🏆 *رکوردها:*\n"
        text += f"• بیشترین: {max_exp['amount']:,} تومان ({max_exp['description']})\n"
        text += f"• کمترین: {min_exp['amount']:,} تومان ({min_exp['description']})"
    
    await update.message.reply_text(text, parse_mode="Markdown")

# /clear
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = load_expenses()
    
    # فقط هزینه‌های کاربر فعلی را پاک کن
    remaining = [e for e in expenses if e.get("user_id") != user_id]
    
    # تعداد هزینه‌های پاک شده
    deleted_count = len(expenses) - len(remaining)
    
    save_expenses(remaining)
    
    await update.message.reply_text(f"✅ {deleted_count} هزینه پاک شد!")

# اجرای اصلی ربات
def main():
    app = Application.builder().token(TOKEN).build()
    
    # دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("month", month))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("search", search))
    
    # ثبت سریع با پیام مستقیم
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_add))
    
    print("🤖 ربات مدیریت هزینه‌ها اجرا شد...")
    print("📊 آماده دریافت هزینه‌ها!")
    app.run_polling()

if __name__ == "__main__":
    main()