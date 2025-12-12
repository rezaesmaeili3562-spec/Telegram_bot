from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import json
from datetime import datetime, timedelta
import os
import re
from typing import Dict, List

# 🔐 Token robot
TOKEN = "8531861676:AAGefz_InVL9y4FtKYcETGAFTRHggaJCnhA"  # Enter your token here

# 📁 Database files
EXPENSES_FILE = "expenses.json"
USERS_FILE = "users.json"
BUDGETS_FILE = "budgets.json"
INCOMES_FILE = "incomes.json"
CATEGORIES_FILE = "categories.json"

# Load data
def load_data(filename, default=None):
    if default is None:
        default = {} if not filename.endswith('.json') else []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_data(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ========== 🎨 Dropdown Menu System ==========
class DropdownMenu:
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Main dropdown menu"""
        keyboard = [
            [InlineKeyboardButton("➕ ثبت هزینه جدید", callback_data="add_expense")],
            [InlineKeyboardButton("💰 ثبت درآمد جدید", callback_data="add_income")],
            [InlineKeyboardButton("📊 گزارش‌ها و آمار", callback_data="reports")],
            [InlineKeyboardButton("🎯 مدیریت بودجه‌ها", callback_data="budgets")],
            [InlineKeyboardButton("📋 سرویس‌های من", callback_data="my_services")],
            [InlineKeyboardButton("🛒 خرید سرویس", callback_data="buy_service")],
            [InlineKeyboardButton("❓ راهنما و پشتیبانی", callback_data="help")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def categories_menu(selected=None) -> InlineKeyboardMarkup:
        """Categories dropdown menu"""
        categories = [
            ["🍔 غذا و رستوران", "food"],
            ["🚕 حمل و نقل", "transport"],
            ["🛒 خرید روزانه", "shopping"],
            ["🏠 خانه و قبوض", "house"],
            ["💊 سلامت و درمان", "health"],
            ["🎬 تفریح و سرگرمی", "entertainment"],
            ["📚 آموزش و کتاب", "education"],
            ["👕 پوشاک و مد", "clothing"],
            ["💻 فناوری و اینترنت", "tech"],
            ["🎁 هدیه و مناسبت", "gift"]
        ]
        
        keyboard = []
        for text, callback in categories:
            if selected == callback:
                text = f"✅ {text}"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"cat_{callback}")])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def amounts_menu() -> InlineKeyboardMarkup:
        """Quick amounts dropdown menu"""
        amounts = [
            ["۵,۰۰۰ تومان", "5000"],
            ["۱۰,۰۰۰ تومان", "10000"],
            ["۲۰,۰۰۰ تومان", "20000"],
            ["۵۰,۰۰۰ تومان", "50000"],
            ["۱۰۰,۰۰۰ تومان", "100000"],
            ["۲۰۰,۰۰۰ تومان", "200000"],
            ["۵۰۰,۰۰۰ تومان", "500000"],
            ["۱,۰۰۰,۰۰۰ تومان", "1000000"]
        ]
        
        keyboard = []
        row = []
        for i, (text, amount) in enumerate(amounts, 1):
            row.append(InlineKeyboardButton(text, callback_data=f"amount_{amount}"))
            if i % 2 == 0 or i == len(amounts):
                keyboard.append(row)
                row = []
        
        keyboard.append([InlineKeyboardButton("✍️ وارد کردن مبلغ دلخواه", callback_data="amount_custom")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_add")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def reports_menu() -> InlineKeyboardMarkup:
        """Reports dropdown menu"""
        keyboard = [
            [InlineKeyboardButton("📅 گزارش امروز", callback_data="report_today")],
            [InlineKeyboardButton("📆 گزارش این هفته", callback_data="report_week")],
            [InlineKeyboardButton("📊 گزارش این ماه", callback_data="report_month")],
            [InlineKeyboardButton("📈 گزارش سه ماهه", callback_data="report_quarter")],
            [InlineKeyboardButton("📋 گزارش سالانه", callback_data="report_year")],
            [InlineKeyboardButton("🔍 جستجو در هزینه‌ها", callback_data="search_expenses")],
            [InlineKeyboardButton("📤 خروجی Excel/PDF", callback_data="export_data")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def budgets_menu() -> InlineKeyboardMarkup:
        """Budget management dropdown menu"""
        keyboard = [
            [InlineKeyboardButton("➕ ایجاد بودجه جدید", callback_data="budget_create")],
            [InlineKeyboardButton("📊 مشاهده بودجه‌ها", callback_data="budget_view")],
            [InlineKeyboardButton("✏️ ویرایش بودجه", callback_data="budget_edit")],
            [InlineKeyboardButton("🗑️ حذف بودجه", callback_data="budget_delete")],
            [InlineKeyboardButton("🔔 تنظیم هشدارها", callback_data="budget_alerts")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def services_menu() -> InlineKeyboardMarkup:
        """Services dropdown menu"""
        keyboard = [
            [InlineKeyboardButton("🟢 سرویس فعال", callback_data="service_active")],
            [InlineKeyboardButton("⏳ تاریخ انقضا", callback_data="service_expiry")],
            [InlineKeyboardButton("📊 حجم مصرفی", callback_data="service_usage")],
            [InlineKeyboardButton("🔄 تمدید سرویس", callback_data="service_renew")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def buy_menu() -> InlineKeyboardMarkup:
        """Purchase dropdown menu"""
        keyboard = [
            [InlineKeyboardButton("💎 پلن طلایی - ۱ ماه", callback_data="buy_gold_1")],
            [InlineKeyboardButton("💎 پلن طلایی - ۳ ماه", callback_data="buy_gold_3")],
            [InlineKeyboardButton("💎 پلن طلایی - ۱۲ ماه", callback_data="buy_gold_12")],
            [InlineKeyboardButton("⚡ پلن نقرهای - ۱ ماه", callback_data="buy_silver_1")],
            [InlineKeyboardButton("⚡ پلن نقرهای - ۳ ماه", callback_data="buy_silver_3")],
            [InlineKeyboardButton("🎁 اعمال کد تخفیف", callback_data="apply_coupon")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def help_menu() -> InlineKeyboardMarkup:
        """Help dropdown menu"""
        keyboard = [
            [InlineKeyboardButton("📖 آموزش استفاده", callback_data="help_tutorial")],
            [InlineKeyboardButton("❓ سوالات متداول", callback_data="help_faq")],
            [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data="help_contact")],
            [InlineKeyboardButton("🔄 ریستارت ربات", callback_data="restart")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_menu() -> InlineKeyboardMarkup:
        """Confirm/cancel dropdown menu"""
        keyboard = [
            [
                InlineKeyboardButton("✅ تایید", callback_data="confirm_yes"),
                InlineKeyboardButton("❌ لغو", callback_data="confirm_no")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_menu(return_to: str = "main") -> InlineKeyboardMarkup:
        """Back button menu"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_{return_to}")]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def period_menu() -> InlineKeyboardMarkup:
        """Time period dropdown menu"""
        keyboard = [
            [
                InlineKeyboardButton("روزانه", callback_data="period_daily"),
                InlineKeyboardButton("هفتگی", callback_data="period_weekly")
            ],
            [
                InlineKeyboardButton("ماهانه", callback_data="period_monthly"),
                InlineKeyboardButton("سه‌ماهه", callback_data="period_quarterly")
            ],
            [
                InlineKeyboardButton("سالانه", callback_data="period_yearly"),
                InlineKeyboardButton("بازه دلخواه", callback_data="period_custom")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_reports")]
        ]
        return InlineKeyboardMarkup(keyboard)

menu = DropdownMenu()

# ========== 📊 Expense Management System ==========
class ExpenseManager:
    
    @staticmethod
    def add_expense(user_id: str, amount: int, category: str, description: str = "") -> Dict:
        """Add new expense"""
        expense = {
            "id": str(datetime.now().timestamp()),
            "user_id": str(user_id),
            "amount": amount,
            "category": category,
            "description": description,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "timestamp": datetime.now().isoformat()
        }
        
        expenses = load_data(EXPENSES_FILE, [])
        expenses.append(expense)
        save_data(EXPENSES_FILE, expenses)
        
        return expense
    
    @staticmethod
    def get_today_expenses(user_id: str) -> List:
        """Get today's expenses"""
        expenses = load_data(EXPENSES_FILE, [])
        today = datetime.now().strftime("%Y-%m-%d")
        
        user_expenses = [
            e for e in expenses 
            if e["user_id"] == str(user_id) and e["date"] == today
        ]
        
        return user_expenses
    
    @staticmethod
    def get_category_name(callback_data: str) -> str:
        """Convert callback to Persian category name"""
        category_map = {
            "food": "🍔 غذا و رستوران",
            "transport": "🚕 حمل و نقل",
            "shopping": "🛒 خرید روزانه",
            "house": "🏠 خانه و قبوض",
            "health": "💊 سلامت و درمان",
            "entertainment": "🎬 تفریح و سرگرمی",
            "education": "📚 آموزش و کتاب",
            "clothing": "👕 پوشاک و مد",
            "tech": "💻 فناوری و اینترنت",
            "gift": "🎁 هدیه و مناسبت"
        }
        
        cat_key = callback_data.replace("cat_", "")
        return category_map.get(cat_key, "سایر")

# ========== 🤖 Main Commands ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /start"""
    user = update.effective_user
    
    welcome_text = f"""
🤖 **ربات مدیریت هوشمند هزینه‌ها**

سلام {user.first_name} 👋
به ربات مدیریت هزینه خوش آمدید!

🔹 **امکانات ربات:**
• ثبت هزینه و درآمد
• گزارش‌گیری و آمار
• مدیریت بودجه
• هشدارهای هوشمند

📱 **از منوی زیر انتخاب کنید:**
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=menu.main_menu(),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /help"""
    help_text = """
📞 **راهنمای اتصال به سرویس‌ها**

🔹 **مراحل استفاده:**
1. روی '🛒 خرید سرویس' کلیک کنید
2. پلن مورد نظر را انتخاب کنید
3. پرداخت را انجام دهید
4. سرویس فعال می‌شود

🔹 **دستورات سریع:**
/start - راه‌اندازی مجدد ربات
/services - مشاهده سرویس‌های من
/buy - خرید سرویس جدید
/help - نمایش این راهنما

🔹 **پشتیبانی:**
برای ارتباط با پشتیبانی از دکمه زیر استفاده کنید:
"""
    
    await update.message.reply_text(
        help_text,
        reply_markup=menu.help_menu(),
        parse_mode="Markdown"
    )

async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /services"""
    user_id = str(update.effective_user.id)
    
    # Simulate service data
    service_text = f"""
📋 **سرویس‌های من**

👤 کاربر: {update.effective_user.first_name}
🆔 کد کاربری: {user_id[-8:]}

🔹 **سرویس فعال:**
• نوع: 💎 پلن طلایی
• وضعیت: 🟢 فعال
• تاریخ انقضا: ۱۴۰۳/۱۲/۲۹
• حجم مصرفی: ۲.۳ گیگ از ۱۰ گیگ

🔹 **گزینه‌های مدیریت:**
"""
    
    await update.message.reply_text(
        service_text,
        reply_markup=menu.services_menu(),
        parse_mode="Markdown"
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /buy"""
    buy_text = """
🛒 **خرید سرویس**

🔹 **پلن‌های موجود:**

💎 **پلن طلایی**
• مدت: ۱ ماه
• حجم: نامحدود
• قیمت: ۶۰,۰۰۰ تومان
• امکانات: تمامی ویژگی‌ها

⚡ **پلن نقرهای**
• مدت: ۱ ماه
• حجم: ۵۰ گیگابایت
• قیمت: ۳۰,۰۰۰ تومان
• امکانات: پایه

🎁 **تخفیف ویژه:**
با کد `WELCOME10` از ۱۰٪ تخفیف بهره‌مند شوید!

🔹 **لطفاً پلن مورد نظر را انتخاب کنید:**
"""
    
    await update.message.reply_text(
        buy_text,
        reply_markup=menu.buy_menu(),
        parse_mode="Markdown"
    )

# ========== 🎯 Dropdown Button Handlers ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for all dropdown buttons"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    print(f"Button clicked: {data} by user: {user_id}")
    
    # 📌 Main handlers
    if data == "add_expense":
        await show_category_menu(query, context)
    
    elif data == "add_income":
        await query.edit_message_text(
            "💰 **ثبت درآمد جدید**\n\nلطفاً مبلغ درآمد را انتخاب کنید:",
            reply_markup=menu.amounts_menu(),
            parse_mode="Markdown"
        )
    
    elif data == "reports":
        await query.edit_message_text(
            "📊 **گزارش‌ها و آمار**\n\nلطفاً نوع گزارش را انتخاب کنید:",
            reply_markup=menu.reports_menu(),
            parse_mode="Markdown"
        )
    
    elif data == "budgets":
        await query.edit_message_text(
            "🎯 **مدیریت بودجه‌ها**\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
            reply_markup=menu.budgets_menu(),
            parse_mode="Markdown"
        )
    
    elif data == "my_services":
        await services_command_callback(query)
    
    elif data == "buy_service":
        await buy_command_callback(query)
    
    elif data == "help":
        await help_command_callback(query)
    
    # 📌 Category handlers
    elif data.startswith("cat_"):
        await handle_category_selection(query, data, context)
    
    # 📌 Amount handlers
    elif data.startswith("amount_"):
        await handle_amount_selection(query, data, user_id, context)
    
    # 📌 Report handlers
    elif data.startswith("report_"):
        await handle_report_selection(query, data, user_id)
    
    # 📌 Budget handlers
    elif data.startswith("budget_"):
        await handle_budget_selection(query, data, user_id)
    
    # 📌 Purchase handlers
    elif data.startswith("buy_"):
        await handle_buy_selection(query, data)
    
    # 📌 Service handlers
    elif data.startswith("service_"):
        await handle_service_selection(query, data, user_id)
    
    # 📌 Help handlers
    elif data.startswith("help_"):
        await handle_help_selection(query, data)
    
    # 📌 Back handlers
    elif data.startswith("back_"):
        await handle_back_button(query, data)
    
    # 📌 Other handlers
    elif data == "restart":
        await start_callback(query)
    
    elif data == "apply_coupon":
        await apply_coupon(query, context)
    
    elif data == "search_expenses":
        await search_expenses(query, context)
    
    elif data == "export_data":
        await export_data(query, user_id)

# ========== 🎯 Helper Functions for Handlers ==========
async def show_category_menu(query, context):
    """Show category menu"""
    await query.edit_message_text(
        "🏷️ **انتخاب دسته‌بندی**\n\nلطفاً دسته هزینه را انتخاب کنید:",
        reply_markup=menu.categories_menu(),
        parse_mode="Markdown"
    )

async def handle_category_selection(query, data, context):
    """Category selection handler"""
    category_name = ExpenseManager.get_category_name(data)
    
    # Save selected category in context.user_data
    context.user_data["selected_category"] = data.replace("cat_", "")
    
    await query.edit_message_text(
        f"✅ **دسته انتخاب شد:** {category_name}\n\n"
        f"💰 لطفاً مبلغ هزینه را انتخاب کنید:",
        reply_markup=menu.amounts_menu(),
        parse_mode="Markdown"
    )

async def handle_amount_selection(query, data, user_id, context):
    """Amount selection handler"""
    if data == "amount_custom":
        await query.edit_message_text(
            "✍️ **مبلغ دلخواه**\n\n"
            "لطفاً مبلغ را به عدد وارد کنید:\n"
            "مثال: 15000 یا 50هزار",
            reply_markup=menu.back_menu("add"),
            parse_mode="Markdown"
        )
        context.user_data["awaiting_custom_amount"] = True
        context.user_data["awaiting_amount_for"] = "expense"
        return
    
    amount = int(data.replace("amount_", ""))
    
    # Save amount in context.user_data
    context.user_data["selected_amount"] = amount
    
    await query.edit_message_text(
        f"💰 **مبلغ انتخاب شد:** {amount:,} تومان\n\n"
        f"📝 لطفاً توضیحات هزینه را وارد کنید:\n"
        f"(می‌توانید خالی بگذارید یا 'لغو' تایپ کنید)",
        reply_markup=menu.back_menu("add"),
        parse_mode="Markdown"
    )
    
    context.user_data["awaiting_description"] = True

async def handle_report_selection(query, data, user_id):
    """Report selection handler"""
    report_type = data.replace("report_", "")
    
    if report_type == "today":
        expenses = ExpenseManager.get_today_expenses(user_id)
        
        if not expenses:
            text = "🎉 امروز هیچ هزینه‌ای ثبت نکرده‌اید!"
        else:
            total = sum(e["amount"] for e in expenses)
            text = f"📅 **گزارش امروز**\n\n"
            text += f"💰 **مجموع هزینه‌ها:** {total:,} تومان\n"
            text += f"📝 **تعداد:** {len(expenses)} مورد\n\n"
            
            for i, exp in enumerate(expenses, 1):
                category_name = ExpenseManager.get_category_name(f"cat_{exp.get('category', 'food')}")
                text += f"{i}. {exp['amount']:,} تومان - {category_name}\n"
                if exp.get('description'):
                    text += f"   📌 {exp['description']}\n"
    
    elif report_type == "week":
        text = "📆 **گزارش این هفته**\n\n(این بخش در حال توسعه است...)"
    
    elif report_type == "month":
        text = "📊 **گزارش این ماه**\n\n(این بخش در حال توسعه است...)"
    
    else:
        text = f"📋 **گزارش {report_type}**\n\n(این بخش در حال توسعه است...)"
    
    await query.edit_message_text(
        text,
        reply_markup=menu.back_menu("reports"),
        parse_mode="Markdown"
    )

async def handle_budget_selection(query, data, user_id):
    """Budget operation selection handler"""
    action = data.replace("budget_", "")
    
    if action == "create":
        text = "🎯 **ایجاد بودجه جدید**\n\nلطفاً دسته‌بندی را انتخاب کنید:"
        await query.edit_message_text(
            text,
            reply_markup=menu.categories_menu(),
            parse_mode="Markdown"
        )
    
    elif action == "view":
        text = "📊 **بودجه‌های شما**\n\n(این بخش در حال توسعه است...)"
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("budgets"),
            parse_mode="Markdown"
        )
    
    else:
        text = f"🔧 **عملیات {action}**\n\n(این بخش در حال توسعه است...)"
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("budgets"),
            parse_mode="Markdown"
        )

async def handle_buy_selection(query, data):
    """Purchase plan selection handler"""
    plan = data.replace("buy_", "")
    
    plans = {
        "gold_1": {"name": "💎 پلن طلایی - ۱ ماه", "price": "۶۰,۰۰۰ تومان"},
        "gold_3": {"name": "💎 پلن طلایی - ۳ ماه", "price": "۱۶۰,۰۰۰ تومان"},
        "gold_12": {"name": "💎 پلن طلایی - ۱۲ ماه", "price": "۶۰۰,۰۰۰ تومان"},
        "silver_1": {"name": "⚡ پلن نقرهای - ۱ ماه", "price": "۳۰,۰۰۰ تومان"},
        "silver_3": {"name": "⚡ پلن نقرهای - ۳ ماه", "price": "۸۰,۰۰۰ تومان"}
    }
    
    if plan in plans:
        selected = plans[plan]
        text = f"""
🛒 **تأیید خرید**

🔹 **پلن انتخاب شده:**
{selected['name']}
💰 قیمت: {selected['price']}

🔹 **مراحل پرداخت:**
1. روی دکمه '✅ تایید' کلیک کنید
2. به درگاه پرداخت هدایت می‌شوید
3. پرداخت را انجام دهید
4. سرویس فعال می‌شود

⚠️ **توجه:** پس از تأیید، به درگاه پرداخت متصل خواهید شد.
"""
        
        await query.edit_message_text(
            text,
            reply_markup=menu.confirm_menu(),
            parse_mode="Markdown"
        )
    
    else:
        await query.edit_message_text(
            "🛒 **خرید سرویس**\n\nلطفاً پلن مورد نظر را انتخاب کنید:",
            reply_markup=menu.buy_menu(),
            parse_mode="Markdown"
        )

async def handle_service_selection(query, data, user_id):
    """Service selection handler"""
    action = data.replace("service_", "")
    
    if action == "active":
        text = "🟢 **سرویس فعال**\n\nسرویس شما در حال حاضر فعال است."
    
    elif action == "expiry":
        text = "⏳ **تاریخ انقضا**\n\nانقضای سرویس: ۱۴۰۳/۱۲/۲۹"
    
    elif action == "usage":
        text = "📊 **حجم مصرفی**\n\nمصرف شده: ۲.۳ گیگ از ۱۰ گیگ"
    
    elif action == "renew":
        text = "🔄 **تمدید سرویس**\n\nبرای تمدید سرویس لطفاً به بخش خرید مراجعه کنید."
    
    else:
        text = "📋 **سرویس‌های من**\n\nلطفاً گزینه مورد نظر را انتخاب کنید:"
        await query.edit_message_text(
            text,
            reply_markup=menu.services_menu(),
            parse_mode="Markdown"
        )
        return
    
    await query.edit_message_text(
        text,
        reply_markup=menu.back_menu("services"),
        parse_mode="Markdown"
    )

async def handle_help_selection(query, data):
    """Help selection handler"""
    action = data.replace("help_", "")
    
    if action == "tutorial":
        text = """
📖 **آموزش استفاده از ربات**

🔹 **مراحل ثبت هزینه:**
1. روی '➕ ثبت هزینه جدید' کلیک کنید
2. دسته‌بندی را انتخاب کنید
3. مبلغ را انتخاب یا وارد کنید
4. توضیحات را وارد کنید (اختیاری)

🔹 **گزارش‌گیری:**
• گزارش امروز: هزینه‌های روز جاری
• گزارش هفته: هزینه‌های ۷ روز گذشته
• گزارش ماه: هزینه‌های ماه جاری

🔹 **مدیریت بودجه:**
می‌توانید برای هر دسته بودجه تعریف کنید.
"""
    
    elif action == "faq":
        text = """
❓ **سوالات متداول**

🔹 **چطور هزینه ثبت کنم؟**
از منوی اصلی روی '➕ ثبت هزینه جدید' کلیک کنید.

🔹 **چطور گزارش بگیرم؟**
از منوی اصلی روی '📊 گزارش‌ها و آمار' کلیک کنید.

🔹 **چطور بودجه تنظیم کنم؟**
از منوی اصلی روی '🎯 مدیریت بودجه‌ها' کلیک کنید.

🔹 **چطور با پشتیبانی تماس بگیرم؟**
از دکمه '📞 تماس با پشتیبانی' استفاده کنید.
"""
    
    elif action == "contact":
        text = """
📞 **تماس با پشتیبانی**

🔹 **روش‌های ارتباط:**
• ایدی پشتیبانی: @SupportID
• ایمیل: support@example.com
• سایت: www.example.com

🔹 **ساعات پاسخگویی:**
شنبه تا چهارشنبه: ۹ صبح تا ۵ عصر
پنجشنبه: ۹ صبح تا ۱ ظهر

🔹 **لطفاً موارد زیر را ارسال کنید:**
1. مشکل به صورت واضح
2. شماره کاربری
3. عکس از مشکل (اگر دارد)
"""
    
    else:
        text = "❓ **راهنما و پشتیبانی**\n\nلطفاً گزینه مورد نظر را انتخاب کنید:"
        await query.edit_message_text(
            text,
            reply_markup=menu.help_menu(),
            parse_mode="Markdown"
        )
        return
    
    await query.edit_message_text(
        text,
        reply_markup=menu.back_menu("help"),
        parse_mode="Markdown"
    )

async def handle_back_button(query, data):
    """Back button handler"""
    target = data.replace("back_", "")
    
    if target == "main":
        await start_callback(query)
    
    elif target == "add":
        await show_category_menu(query, None)
    
    elif target == "reports":
        await query.edit_message_text(
            "📊 **گزارش‌ها و آمار**\n\nلطفاً نوع گزارش را انتخاب کنید:",
            reply_markup=menu.reports_menu(),
            parse_mode="Markdown"
        )
    
    elif target == "budgets":
        await query.edit_message_text(
            "🎯 **مدیریت بودجه‌ها**\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
            reply_markup=menu.budgets_menu(),
            parse_mode="Markdown"
        )
    
    elif target == "services":
        await services_command_callback(query)
    
    elif target == "help":
        await help_command_callback(query)
    
    else:
        await start_callback(query)

async def apply_coupon(query, context):
    """Apply discount code"""
    await query.edit_message_text(
        "🎁 **اعمال کد تخفیف**\n\n"
        "لطفاً کد تخفیف خود را وارد کنید:\n\n"
        "⚠️ **توجه:**\n"
        "• فقط حروف انگلیسی (A-Z) و اعداد (0-9)\n"
        "• طول کد نباید بیش از ۲۰ کاراکتر باشد\n"
        "• مثال صحیح: WELCOME10\n\n"
        "برای لغو، روی دکمه بازگشت کلیک کنید.",
        reply_markup=menu.back_menu("buy"),
        parse_mode="Markdown"
    )
    
    context.user_data["awaiting_coupon"] = True

async def search_expenses(query, context):
    """Search in expenses"""
    await query.edit_message_text(
        "🔍 **جستجو در هزینه‌ها**\n\n"
        "لطفاً عبارت جستجو را وارد کنید:\n"
        "(می‌توانید بر اساس دسته، توضیحات یا مبلغ جستجو کنید)",
        reply_markup=menu.back_menu("reports"),
        parse_mode="Markdown"
    )
    
    context.user_data["awaiting_search"] = True

async def export_data(query, user_id):
    """Export data"""
    await query.edit_message_text(
        "📤 **خروجی گرفتن از داده‌ها**\n\n"
        "در حال آماده‌سازی گزارش...\n\n"
        "🔹 **فرمت‌های موجود:**\n"
        "• Excel (.xlsx)\n"
        "• PDF (.pdf)\n"
        "• CSV (.csv)\n\n"
        "⚠️ این بخش در حال توسعه است...",
        reply_markup=menu.back_menu("reports"),
        parse_mode="Markdown"
    )

# ========== 🔄 Helper Functions ==========
async def start_callback(query):
    """Start robot through callback"""
    user = query.from_user
    welcome_text = f"""
🤖 **ربات مدیریت هوشمند هزینه‌ها**

سلام {user.first_name} 👋
به ربات مدیریت هزینه خوش آمدید!

📱 **از منوی زیر انتخاب کنید:**
"""
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=menu.main_menu(),
        parse_mode="Markdown"
    )

async def services_command_callback(query):
    """Services through callback"""
    user = query.from_user
    service_text = f"""
📋 **سرویس‌های من**

👤 کاربر: {user.first_name}
🆔 کد کاربری: {str(user.id)[-8:]}

🔹 **لطفاً گزینه مورد نظر را انتخاب کنید:**
"""
    
    await query.edit_message_text(
        service_text,
        reply_markup=menu.services_menu(),
        parse_mode="Markdown"
    )

async def buy_command_callback(query):
    """Purchase through callback"""
    buy_text = """
🛒 **خرید سرویس**

🔹 **پلن‌های موجود:**

لطفاً پلن مورد نظر را انتخاب کنید:
"""
    
    await query.edit_message_text(
        buy_text,
        reply_markup=menu.buy_menu(),
        parse_mode="Markdown"
    )

async def help_command_callback(query):
    """Help through callback"""
    help_text = """
❓ **راهنما و پشتیبانی**

🔹 **لطفاً گزینه مورد نظر را انتخاب کنید:**
"""
    
    await query.edit_message_text(
        help_text,
        reply_markup=menu.help_menu(),
        parse_mode="Markdown"
    )

# ========== 💬 Text Message Handler ==========
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Text message handler"""
    text = update.message.text.strip()
    user_id = str(update.effective_user.id)
    
    # Check different states
    if context.user_data.get("awaiting_description"):
        await handle_expense_description(update, context, text)
    
    elif context.user_data.get("awaiting_custom_amount"):
        await handle_custom_amount(update, context, text)
    
    elif context.user_data.get("awaiting_coupon"):
        await handle_coupon_code(update, context, text)
    
    elif context.user_data.get("awaiting_search"):
        await handle_search_query(update, context, text)
    
    else:
        # Quick expense registration with simple text
        if re.search(r'\d', text):
            await handle_quick_expense(update, text)
        else:
            await update.message.reply_text(
                "Please select from the menu below:",
                reply_markup=menu.main_menu()
            )

async def handle_expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE, description: str):
    """Expense description handler"""
    if description.lower() in ["لغو", "cancel", "انصراف"]:
        await update.message.reply_text(
            "❌ عملیات ثبت هزینه لغو شد.",
            reply_markup=menu.main_menu()
        )
        context.user_data.clear()
        return
    
    # Get saved data from context.user_data
    amount = context.user_data.get("selected_amount", 0)
    category = context.user_data.get("selected_category", "food")
    
    if amount <= 0:
        await update.message.reply_text(
            "❌ خطا در ثبت هزینه. لطفاً مجدداً تلاش کنید.",
            reply_markup=menu.main_menu()
        )
        context.user_data.clear()
        return
    
    # Register expense
    category_name = ExpenseManager.get_category_name(f"cat_{category}")
    expense = ExpenseManager.add_expense(
        user_id=update.effective_user.id,
        amount=amount,
        category=category,
        description=description
    )
    
    # Response to user
    await update.message.reply_text(
        f"✅ **هزینه با موفقیت ثبت شد!**\n\n"
        f"💰 مبلغ: {amount:,} تومان\n"
        f"🏷️ دسته: {category_name}\n"
        f"📝 توضیحات: {description if description else 'بدون توضیح'}\n"
        f"🕐 زمان: {expense['time']}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 گزارش امروز", callback_data="report_today"),
            InlineKeyboardButton("➕ هزینه جدید", callback_data="add_expense")
        ]]),
        parse_mode="Markdown"
    )
    
    # Clear temporary data
    context.user_data.clear()

async def handle_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Custom amount handler"""
    amount = parse_amount(text)
    
    if not amount or amount <= 0:
        await update.message.reply_text(
            "❌ مبلغ نامعتبر! لطفاً عدد معتبر وارد کنید.\nمثال: 15000 یا 50هزار",
            reply_markup=menu.back_menu("add")
        )
        return
    
    # Save amount and go to next step
    context.user_data["selected_amount"] = amount
    context.user_data.pop("awaiting_custom_amount", None)
    
    await update.message.reply_text(
        f"💰 **مبلغ وارد شد:** {amount:,} تومان\n\n"
        f"📝 لطفاً توضیحات هزینه را وارد کنید:",
        reply_markup=menu.back_menu("add"),
        parse_mode="Markdown"
    )
    
    context.user_data["awaiting_description"] = True

async def handle_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Discount code handler"""
    coupon = text.strip().upper()
    
    # Check code validity
    valid_coupons = ["WELCOME10", "SAVE20", "FIRSTBUY", "TEST123"]
    
    if coupon in valid_coupons:
        response = f"✅ **کد تخفیف اعمال شد!**\n\nکد: {coupon}\nتخفیف: ۱۰٪\n\nلطفاً پلن مورد نظر را انتخاب کنید:"
        await update.message.reply_text(
            response,
            reply_markup=menu.buy_menu(),
            parse_mode="Markdown"
        )
    else:
        response = f"❌ **کد تخفیف نامعتبر!**\n\nکد '{coupon}' معتبر نیست.\n\nکدهای معتبر: WELCOME10, SAVE20\n\nلطفاً مجدداً کد را وارد کنید:"
        await update.message.reply_text(
            response,
            reply_markup=menu.back_menu("buy"),
            parse_mode="Markdown"
        )
        return  # Wait for new code
    
    context.user_data.pop("awaiting_coupon", None)

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Search query handler"""
    query = text.strip()
    
    # Search operation should be done here
    # For now, a sample message:
    await update.message.reply_text(
        f"🔍 **نتایج جستجو برای '{query}'**\n\n"
        f"(این بخش در حال توسعه است...)\n\n"
        f"⚠️ جستجوی پیشرفته به زودی اضافه خواهد شد.",
        reply_markup=menu.back_menu("reports"),
        parse_mode="Markdown"
    )
    
    context.user_data.pop("awaiting_search", None)

async def handle_quick_expense(update: Update, text: str):
    """Quick expense registration"""
    # Find number in text
    numbers = re.findall(r'[\d,]+', text)
    if not numbers:
        return
    
    amount = parse_amount(numbers[0])
    if not amount:
        return
    
    description = re.sub(r'[\d,]+', '', text).strip()
    if not description:
        description = "بدون توضیح"
    
    # Simple category detection
    category = "food"  # Default
    
    # Register expense
    expense = ExpenseManager.add_expense(
        user_id=update.effective_user.id,
        amount=amount,
        category=category,
        description=description
    )
    
    await update.message.reply_text(
        f"✅ **ثبت سریع موفق!**\n\n"
        f"💰 {amount:,} تومان - {description}\n"
        f"🕐 {expense['time']}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 گزارش امروز", callback_data="report_today"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_main")
        ]]),
        parse_mode="Markdown"
    )

def parse_amount(amount_str):
    """Convert amount to number"""
    try:
        amount_str = str(amount_str)
        amount_str = amount_str.replace(",", "").replace(" ", "")
        
        persian_numbers = {
            "هزار": "000",
            "میلیون": "000000",
            "میلیارد": "000000000",
            "تومان": "",
            "ت": ""
        }
        
        for word, replacement in persian_numbers.items():
            amount_str = amount_str.replace(word, replacement)
        
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        amount_str = amount_str.translate(persian_to_english)
        
        amount_str = re.sub(r'[^\d]', '', amount_str)
        
        return int(amount_str) if amount_str else None
    except:
        return None

# ========== 🚀 Main Robot Execution ==========
def main() -> None:
    """Start robot"""
    app = Application.builder().token(TOKEN).build()
    
    # Main commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("services", services_command))
    app.add_handler(CommandHandler("buy", buy_command))
    
    # Dropdown button handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Text message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    print("🤖 Robot e modiriat e hazine ba menu haye keshide run shod...")
    print("📱 Montazer e karbaran hastim...")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()