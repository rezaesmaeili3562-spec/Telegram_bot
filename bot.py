from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
import json
from datetime import datetime, timedelta
import os
import re
import hashlib
import secrets
from typing import Dict, List, Optional, Tuple
import csv
import io
import asyncio
from collections import defaultdict

# 🔐 توکن ربات
TOKEN = "8531861676:AAGefz_InVL9y4FtKYcETGAFTRHggaJCnhA"

# 📁 فایل‌های دیتابیس
EXPENSES_FILE = "expenses.json"
USERS_FILE = "users.json"
BUDGETS_FILE = "budgets.json"
INCOMES_FILE = "incomes.json"
GOALS_FILE = "goals.json"
FAMILIES_FILE = "families.json"
PREFERENCES_FILE = "preferences.json"
BACKUP_DIR = "backups/"

# ایجاد پوشه‌ها
os.makedirs(BACKUP_DIR, exist_ok=True)

# حالت‌های گفتگو
(
    AWAITING_PASSWORD,
    AWAITING_LOGIN,
    AWAITING_EXPENSE_AMOUNT,
    AWAITING_EXPENSE_DESC,
    AWAITING_INCOME_AMOUNT,
    AWAITING_INCOME_SOURCE,
    AWAITING_BUDGET_AMOUNT,
    AWAITING_BUDGET_CATEGORY,
    AWAITING_GOAL_AMOUNT,
    AWAITING_GOAL_NAME,
    AWAITING_SEARCH_QUERY,
    AWAITING_FAMILY_NAME
) = range(12)

# لود کردن داده‌ها
def load_data(filename, default=None):
    if default is None:
        default = [] if filename.endswith('.json') else {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

# ذخیره داده‌ها
def save_data(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ========== 🔐 سیستم امنیتی ==========
class SecuritySystem:
    def __init__(self):
        self.users = load_data(USERS_FILE, {})
        self.sessions = {}
    
    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()
    
    def verify_password(self, stored: str, password: str) -> bool:
        salt, hashval = stored.split(":")
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashval
    
    def register_user(self, user_id: str, password: str) -> bool:
        if str(user_id) in self.users:
            return False
        self.users[str(user_id)] = {
            "password": self.hash_password(password),
            "created": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
            "name": "",
            "currency": "تومان"
        }
        save_data(USERS_FILE, self.users)
        return True
    
    def authenticate(self, user_id: str, password: str) -> bool:
        user = self.users.get(str(user_id))
        if not user:
            return False
        if self.verify_password(user["password"], password):
            user["last_login"] = datetime.now().isoformat()
            save_data(USERS_FILE, self.users)
            return True
        return False
    
    def is_logged_in(self, user_id: str) -> bool:
        return str(user_id) in self.users and self.users[str(user_id)].get("last_login")

security = SecuritySystem()

# ========== 🎨 سیستم منوها ==========
class MenuSystem:
    @staticmethod
    def get_main_menu() -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("➕ ثبت هزینه", callback_data="menu_add_expense"),
                InlineKeyboardButton("💰 ثبت درآمد", callback_data="menu_add_income")
            ],
            [
                InlineKeyboardButton("📊 گزارش امروز", callback_data="menu_today"),
                InlineKeyboardButton("📈 گزارش ماه", callback_data="menu_month")
            ],
            [
                InlineKeyboardButton("🎯 مدیریت بودجه", callback_data="menu_budget"),
                InlineKeyboardButton("📋 اهداف مالی", callback_data="menu_goals")
            ],
            [
                InlineKeyboardButton("🔍 جستجو", callback_data="menu_search"),
                InlineKeyboardButton("👥 خانواده", callback_data="menu_family")
            ],
            [
                InlineKeyboardButton("⚙️ تنظیمات", callback_data="menu_settings"),
                InlineKeyboardButton("📤 خروجی", callback_data="menu_export")
            ],
            [
                InlineKeyboardButton("ℹ️ راهنما", callback_data="menu_help"),
                InlineKeyboardButton("📊 آمار کلی", callback_data="menu_stats")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_back_button(return_to: str = "main") -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_{return_to}")]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_budget_menu() -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("➕ بودجه جدید", callback_data="budget_add"),
                InlineKeyboardButton("📊 وضعیت بودجه", callback_data="budget_status")
            ],
            [
                InlineKeyboardButton("✏️ ویرایش بودجه", callback_data="budget_edit"),
                InlineKeyboardButton("🗑️ حذف بودجه", callback_data="budget_delete")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_categories_menu() -> InlineKeyboardMarkup:
        categories = ["🍔 غذا", "🚕 حمل نقل", "🛒 خرید", "☕ کافه", "💊 سلامت", "🎬 تفریح", "📚 آموزش", "💡 قبوض", "👕 پوشاک", "🏠 خانه"]
        keyboard = []
        row = []
        for i, cat in enumerate(categories, 1):
            row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
            if i % 2 == 0 or i == len(categories):
                keyboard.append(row)
                row = []
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_add")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_quick_amounts() -> InlineKeyboardMarkup:
        amounts = [
            ["5,000", "10,000", "20,000"],
            ["50,000", "100,000", "200,000"],
            ["500,000", "1,000,000", "2,000,000"]
        ]
        keyboard = []
        for row in amounts:
            keyboard_row = []
            for amount in row:
                keyboard_row.append(InlineKeyboardButton(amount, callback_data=f"amount_{amount.replace(',', '')}"))
            keyboard.append(keyboard_row)
        keyboard.append([InlineKeyboardButton("✍️ مبلغ دیگر", callback_data="amount_custom")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_time_period_menu() -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("📅 امروز", callback_data="period_today"),
                InlineKeyboardButton("📆 این هفته", callback_data="period_week"),
                InlineKeyboardButton("📊 این ماه", callback_data="period_month")
            ],
            [
                InlineKeyboardButton("📈 ماه قبل", callback_data="period_last_month"),
                InlineKeyboardButton("📋 همه", callback_data="period_all"),
                InlineKeyboardButton("🗓️ بازه دلخواه", callback_data="period_custom")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_settings_menu() -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("👤 پروفایل", callback_data="settings_profile")],
            [InlineKeyboardButton("🔐 تغییر رمز", callback_data="settings_password")],
            [InlineKeyboardButton("💰 واحد پول", callback_data="settings_currency")],
            [InlineKeyboardButton("🔔 نوتیفیکیشن", callback_data="settings_notifications")],
            [InlineKeyboardButton("🗑️ پاک کردن داده", callback_data="settings_clear")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_family_menu() -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🏠 ایجاد خانواده", callback_data="family_create")],
            [InlineKeyboardButton("👤 افزودن عضو", callback_data="family_add_member")],
            [InlineKeyboardButton("📊 گزارش خانوادگی", callback_data="family_report")],
            [InlineKeyboardButton("⚙️ تنظیمات خانواده", callback_data="family_settings")],
            [InlineKeyboardButton("🚪 ترک خانواده", callback_data="family_leave")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)

menu = MenuSystem()

# ========== 💰 سیستم بودجه‌بندی ==========
class BudgetSystem:
    def __init__(self):
        self.budgets = load_data(BUDGETS_FILE, {})
    
    def set_budget(self, user_id: str, category: str, amount: int, period: str = "monthly") -> None:
        user_id = str(user_id)
        if user_id not in self.budgets:
            self.budgets[user_id] = {}
        
        self.budgets[user_id][category] = {
            "amount": amount,
            "period": period,
            "set_date": datetime.now().isoformat(),
            "spent": 0,
            "notifications": True,
            "reset_date": self._get_next_reset_date(period)
        }
        save_data(BUDGETS_FILE, self.budgets)
    
    def get_budget_status(self, user_id: str) -> Dict:
        user_id = str(user_id)
        if user_id not in self.budgets:
            return {}
        
        status = {}
        for category, budget in self.budgets[user_id].items():
            percentage = (budget["spent"] / budget["amount"]) * 100 if budget["amount"] > 0 else 0
            status[category] = {
                "budget": budget["amount"],
                "spent": budget["spent"],
                "remaining": budget["amount"] - budget["spent"],
                "percentage": percentage,
                "period": budget["period"],
                "status": "🟢" if percentage < 80 else "🟡" if percentage < 100 else "🔴"
            }
        return status

    def _get_next_reset_date(self, period: str) -> str:
        now = datetime.now()
        if period == "daily":
            return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
        elif period == "weekly":
            days_ahead = 6 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0).isoformat()
        else:  # monthly
            if now.month == 12:
                next_month = now.replace(year=now.year+1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month+1, day=1)
            return next_month.isoformat()

budget_system = BudgetSystem()

# ========== 📊 سیستم گزارش‌گیری ==========
class ReportSystem:
    @staticmethod
    def get_today_report(user_id: str) -> str:
        expenses = load_data(EXPENSES_FILE, [])
        user_expenses = [e for e in expenses if e["user_id"] == str(user_id)]
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_expenses = [e for e in user_expenses if e["date"] == today]
        
        if not today_expenses:
            return "🎉 امروز هیچ هزینه‌ای ثبت نکردی!"
        
        total = sum(e["amount"] for e in today_expenses)
        
        report = f"📅 **گزارش امروز ({today})**\n\n"
        for i, exp in enumerate(today_expenses, 1):
            report += f"{i}. {exp['amount']:,} تومان - {exp.get('description', 'بدون توضیح')} ({exp['time']})\n"
        
        report += f"\n💰 **جمع امروز:** {total:,} تومان\n"
        report += f"📝 **تعداد:** {len(today_expenses)} خرید\n"
        
        # تحلیل دسته‌بندی
        categories = defaultdict(int)
        for exp in today_expenses:
            cat = exp.get("category", "سایر")
            categories[cat] += exp["amount"]
        
        if categories:
            report += "\n🏷️ **دسته‌بندی:**\n"
            for cat, amount in categories.items():
                report += f"• {cat}: {amount:,} تومان\n"
        
        return report
    
    @staticmethod
    def get_month_report(user_id: str) -> str:
        expenses = load_data(EXPENSES_FILE, [])
        user_expenses = [e for e in expenses if e["user_id"] == str(user_id)]
        
        current_month = datetime.now().strftime("%Y-%m")
        month_expenses = [e for e in user_expenses if e["date"].startswith(current_month)]
        
        if not month_expenses:
            return f"📭 هیچ هزینه‌ای برای ماه {current_month} ثبت نشده"
        
        total = sum(e["amount"] for e in month_expenses)
        avg = total / len(month_expenses)
        
        # گروه‌بندی بر اساس روز
        daily_totals = defaultdict(int)
        for exp in month_expenses:
            daily_totals[exp["date"]] += exp["amount"]
        
        report = f"📊 **گزارش ماه {current_month}**\n\n"
        report += f"💰 **جمع ماه:** {total:,} تومان\n"
        report += f"📝 **تعداد خرید:** {len(month_expenses)}\n"
        report += f"📈 **میانگین هر خرید:** {avg:,.0f} تومان\n"
        
        # ۵ روز پرخرج
        top_days = sorted(daily_totals.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_days:
            report += "\n🏆 **۵ روز پرخرج:**\n"
            for date, amount in top_days:
                report += f"• {date}: {amount:,} تومان\n"
        
        return report

report_system = ReportSystem()

# ========== 🎯 دستورات اصلی ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    
    # چک کردن ثبت نام
    if user_id not in security.users:
        welcome_text = f"""
👋 سلام {user.first_name}!
به ربات مدیریت هوشمند هزینه‌ها خوش آمدید! 💰

برای شروع، لطفاً ثبت نام کنید:
"""
        keyboard = [
            [InlineKeyboardButton("📝 ثبت نام", callback_data="register_start")],
            [InlineKeyboardButton("ℹ️ راهنمای استفاده", callback_data="show_help")]
        ]
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return
    
    # اگر کاربر ثبت‌نام کرده، منوی اصلی رو نشون بده
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome_text = f"""
🏠 **منوی اصلی**

سلام {user.first_name}! 👋
چه کاری می‌خواهید انجام دهید؟

📊 **امکانات اصلی:**
• ثبت هزینه و درآمد
• مدیریت بودجه‌ها
• اهداف مالی
• گزارش‌گیری
• مدیریت خانواده
"""
    
    await send_menu_message(update, context, welcome_text, menu.get_main_menu())

async def send_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           text: str, reply_markup: InlineKeyboardMarkup, 
                           edit: bool = False) -> None:
    """ارسال یا ویرایش پیام با منو"""
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

# ========== 🎯 هندلرهای دکمه‌ها ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    # هندلرهای اصلی منو
    if data == "menu_add_expense":
        await show_add_expense_menu(update, context)
    
    elif data == "menu_add_income":
        await show_add_income_menu(update, context)
    
    elif data == "menu_today":
        report = report_system.get_today_report(user_id)
        await send_menu_message(update, context, report, menu.get_back_button(), edit=True)
    
    elif data == "menu_month":
        report = report_system.get_month_report(user_id)
        await send_menu_message(update, context, report, menu.get_back_button(), edit=True)
    
    elif data == "menu_budget":
        await show_budget_menu(update, context)
    
    elif data == "menu_goals":
        await show_goals_menu(update, context)
    
    elif data == "menu_search":
        await show_search_menu(update, context)
    
    elif data == "menu_family":
        await show_family_menu(update, context)
    
    elif data == "menu_settings":
        await show_settings_menu(update, context)
    
    elif data == "menu_export":
        await show_export_menu(update, context)
    
    elif data == "menu_help":
        await show_help_menu(update, context)
    
    elif data == "menu_stats":
        await show_stats_menu(update, context)
    
    elif data == "register_start":
        await start_registration(update, context)
    
    elif data.startswith("back_"):
        return_to = data.replace("back_", "")
        if return_to == "main":
            await show_main_menu(update, context)
        elif return_to == "add":
            await show_add_expense_menu(update, context)
    
    # هندلرهای ثبت هزینه
    elif data.startswith("cat_"):
        category = data.replace("cat_", "")
        context.user_data["selected_category"] = category
        await ask_expense_amount(update, context)
    
    elif data.startswith("amount_"):
        amount_str = data.replace("amount_", "")
        if amount_str == "custom":
            await ask_custom_amount(update, context)
        else:
            amount = parse_amount(amount_str)
            context.user_data["expense_amount"] = amount
            await ask_expense_description(update, context)
    
    # سایر هندلرها
    elif data == "budget_add":
        await ask_budget_category(update, context)
    
    elif data == "budget_status":
        await show_budget_status(update, context)

# ========== 🏷️ منوهای خاص ==========
async def show_add_expense_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """
➕ **ثبت هزینه جدید**

لطفاً دسته‌بندی هزینه را انتخاب کنید:
"""
    await send_menu_message(update, context, text, menu.get_categories_menu(), edit=True)

async def show_add_income_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """
💰 **ثبت درآمد جدید**

لطفاً مبلغ درآمد را انتخاب کنید:
"""
    await send_menu_message(update, context, text, menu.get_quick_amounts(), edit=True)

async def show_budget_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """
🎯 **مدیریت بودجه**

با بودجه‌بندی، هزینه‌های خود را کنترل کنید:
"""
    await send_menu_message(update, context, text, menu.get_budget_menu(), edit=True)

async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = f"""
⚙️ **تنظیمات کاربری**

کاربر: {user.first_name}
آیدی: {user.id}

لطفاً تنظیمات مورد نظر را انتخاب کنید:
"""
    await send_menu_message(update, context, text, menu.get_settings_menu(), edit=True)

async def show_family_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """
👥 **مدیریت خانواده**

با خانواده‌تان هزینه‌ها را مدیریت کنید:
"""
    await send_menu_message(update, context, text, menu.get_family_menu(), edit=True)

async def show_export_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """
📤 **خروجی گرفتن از داده‌ها**

می‌توانید داده‌های خود را به صورت فایل دریافت کنید:
"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Excel", callback_data="export_excel"),
            InlineKeyboardButton("📄 PDF", callback_data="export_pdf")
        ],
        [
            InlineKeyboardButton("📝 CSV", callback_data="export_csv"),
            InlineKeyboardButton("📋 متن", callback_data="export_text")
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ]
    await send_menu_message(update, context, text, InlineKeyboardMarkup(keyboard), edit=True)

async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """
ℹ️ **راهنمای استفاده**

📋 **دستورات سریع:**
• `10000 ناهار` - ثبت سریع هزینه
• `500000 حقوق` - ثبت سریع درآمد

🎯 **امکانات اصلی:**
1. **ثبت هزینه/درآمد** - با منو یا دستور سریع
2. **مدیریت بودجه** - تعیین محدودیت هزینه
3. **اهداف مالی** - تعیین اهداف پس‌انداز
4. **گزارش‌گیری** - گزارش روزانه، هفتگی، ماهانه
5. **خانواده** - مدیریت هزینه‌های مشترک

📞 **پشتیبانی:** @support
"""
    await send_menu_message(update, context, text, menu.get_back_button(), edit=True)

async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    
    # جمع‌آوری آمار
    expenses = load_data(EXPENSES_FILE, [])
    user_expenses = [e for e in expenses if e["user_id"] == user_id]
    
    if not user_expenses:
        text = "📭 هنوز هیچ داده‌ای برای نمایش آمار وجود ندارد."
    else:
        total = sum(e["amount"] for e in user_expenses)
        avg = total / len(user_expenses)
        
        # پیدا کردن قدیمی‌ترین و جدیدترین
        dates = [datetime.strptime(e["date"], "%Y-%m-%d") for e in user_expenses]
        oldest = min(dates).strftime("%Y-%m-%d")
        newest = max(dates).strftime("%Y-%m-%d")
        
        text = f"""
📈 **آمار کلی شما**

📅 بازه زمانی: {oldest} تا {newest}
💰 مجموع هزینه‌ها: {total:,} تومان
📝 تعداد تراکنش‌ها: {len(user_expenses)}
📊 میانگین هر خرید: {avg:,.0f} تومان

🏆 **رکوردها:**
"""
        if user_expenses:
            max_exp = max(user_expenses, key=lambda x: x["amount"])
            min_exp = min(user_expenses, key=lambda x: x["amount"])
            text += f"• بیشترین خرید: {max_exp['amount']:,} تومان ({max_exp.get('description', 'بدون توضیح')})\n"
            text += f"• کمترین خرید: {min_exp['amount']:,} تومان ({min_exp.get('description', 'بدون توضیح')})"
    
    await send_menu_message(update, context, text, menu.get_back_button(), edit=True)

async def show_budget_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    status = budget_system.get_budget_status(user_id)
    
    if not status:
        text = "🎯 هنوز بودجه‌ای تنظیم نکرده‌اید."
    else:
        text = "🎯 **وضعیت بودجه‌های شما:**\n\n"
        for category, data in status.items():
            text += f"{data['status']} **{category}**\n"
            text += f"بودجه: {data['budget']:,} تومان\n"
            text += f"خرج شده: {data['spent']:,} تومان\n"
            text += f"مانده: {data['remaining']:,} تومان\n"
            text += f"پرشدگی: {data['percentage']:.1f}%\n"
            text += f"دوره: {'ماهانه' if data['period'] == 'monthly' else 'هفتگی' if data['period'] == 'weekly' else 'روزانه'}\n\n"
    
    await send_menu_message(update, context, text, menu.get_back_button("budget"), edit=True)

async def show_goals_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    goals = load_data(GOALS_FILE, {}).get(user_id, [])
    
    if not goals:
        text = "🎯 هنوز هدف مالی تنظیم نکرده‌اید.\n\nبرای تنظیم هدف جدید روی دکمه زیر کلیک کنید:"
        keyboard = [
            [InlineKeyboardButton("🎯 هدف جدید", callback_data="goal_new")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]
    else:
        text = "🎯 **اهداف مالی شما:**\n\n"
        for i, goal in enumerate(goals, 1):
            progress = (goal.get("saved", 0) / goal["target"]) * 100
            text += f"{i}. **{goal['name']}**\n"
            text += f"   هدف: {goal['target']:,} تومان\n"
            text += f"   پس‌انداز شده: {goal.get('saved', 0):,} تومان\n"
            text += f"   پیشرفت: {progress:.1f}%\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🎯 هدف جدید", callback_data="goal_new")],
            [InlineKeyboardButton("📈 افزودن پس‌انداز", callback_data="goal_add")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]
    
    await send_menu_message(update, context, text, InlineKeyboardMarkup(keyboard), edit=True)

async def show_search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """
🔍 **جستجوی هزینه‌ها**

می‌توانید در توضیحات هزینه‌ها جستجو کنید:
"""
    keyboard = [
        [InlineKeyboardButton("🔎 جستجوی متن", callback_data="search_text")],
        [InlineKeyboardButton("🏷️ جستجو براساس دسته", callback_data="search_category")],
        [InlineKeyboardButton("💰 جستجو براساس مبلغ", callback_data="search_amount")],
        [InlineKeyboardButton("📅 جستجو براساس تاریخ", callback_data="search_date")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ]
    await send_menu_message(update, context, text, InlineKeyboardMarkup(keyboard), edit=True)

# ========== 📝 فرآیندهای ثبت ==========
async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = """
📝 **ثبت نام**

لطفاً یک رمز عبور قوی انتخاب کنید:
• حداقل ۶ کاراکتر
• ترکیبی از حروف و اعداد
"""
    await send_menu_message(update, context, text, menu.get_back_button(), edit=True)
    return AWAITING_PASSWORD

async def ask_expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    category = context.user_data.get("selected_category", "سایر")
    text = f"""
💰 **تعیین مبلغ هزینه**

دسته: {category}

لطفاً مبلغ را انتخاب کنید:
"""
    await send_menu_message(update, context, text, menu.get_quick_amounts(), edit=True)

async def ask_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """
✍️ **مبلغ دلخواه**

لطفاً مبلغ را به صورت عددی وارد کنید:
مثال: 15000 یا 50هزار
"""
    await send_menu_message(update, context, text, menu.get_back_button("add"), edit=True)
    # حالت گفتگو رو تنظیم کن
    context.user_data["awaiting_amount"] = True

async def ask_expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    amount = context.user_data.get("expense_amount", 0)
    category = context.user_data.get("selected_category", "سایر")
    
    text = f"""
📝 **توضیحات هزینه**

مبلغ: {amount:,} تومان
دسته: {category}

لطفاً توضیحات هزینه را وارد کنید:
(می‌توانید خالی بگذارید)
"""
    await send_menu_message(update, context, text, menu.get_back_button("add"), edit=True)
    context.user_data["awaiting_description"] = True

async def ask_budget_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """
🏷️ **انتخاب دسته برای بودجه**

لطفاً دسته‌ای که می‌خواهید برای آن بودجه تنظیم کنید را انتخاب کنید:
"""
    await send_menu_message(update, context, text, menu.get_categories_menu(), edit=True)
    context.user_data["awaiting_budget_category"] = True

# ========== 💬 هندلر پیام‌های متنی ==========
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    
    # چک کردن ثبت نام
    if user_id not in security.users:
        await update.message.reply_text(
            "لطفاً ابتدا با دستور /start ثبت نام کنید.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("شروع", callback_data="start_over")
            ]])
        )
        return
    
    # هندلر ثبت رمز عبور
    if context.user_data.get("awaiting_password"):
        if len(text) < 6:
            await update.message.reply_text("❌ رمز عبور باید حداقل ۶ کاراکتر باشد.")
            return
        
        if security.register_user(user_id, text):
            await update.message.reply_text(
                "✅ ثبت نام با موفقیت انجام شد!\n\n"
                "اکنون می‌توانید از امکانات ربات استفاده کنید.",
                reply_markup=menu.get_main_menu()
            )
            context.user_data.pop("awaiting_password", None)
        return
    
    # هندلر ثبت هزینه سریع
    if re.search(r'\d', text):
        await handle_quick_expense(update, context, text)
        return
    
    # هندلر توضیحات هزینه
    if context.user_data.get("awaiting_description"):
        await save_expense_with_description(update, context, text)
        return
    
    # هندلر مبلغ دلخواه
    if context.user_data.get("awaiting_amount"):
        amount = parse_amount(text)
        if amount:
            context.user_data["expense_amount"] = amount
            context.user_data.pop("awaiting_amount", None)
            await ask_expense_description(update, context)
        else:
            await update.message.reply_text("❌ مبلغ نامعتبر! لطفاً دوباره وارد کنید.")
        return
    
    # اگر هیچکدام نبود، منوی اصلی رو نشون بده
    await show_main_menu(update, context)

async def handle_quick_expense(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """هندلر ثبت سریع هزینه با متن ساده"""
    # پیدا کردن عدد در متن
    numbers = re.findall(r'[\d,]+', text)
    if not numbers:
        return
    
    amount = parse_amount(numbers[0])
    if not amount:
        return
    
    description = re.sub(r'[\d,]+', '', text).strip()
    if not description:
        description = "بدون توضیح"
    
    # تشخیص دسته
    category = "سایر"
    for cat in ["غذا", "حمل نقل", "خرید", "کافه", "سلامت", "تفریح", "آموزش", "قبوض", "پوشاک"]:
        if cat in description:
            category = cat
            break
    
    # ذخیره هزینه
    expenses = load_data(EXPENSES_FILE, [])
    expense_data = {
        "user_id": str(update.effective_user.id),
        "amount": amount,
        "description": description,
        "category": category,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "timestamp": datetime.now().isoformat()
    }
    expenses.append(expense_data)
    save_data(EXPENSES_FILE, expenses)
    
    # بروزرسانی بودجه
    budget_warning = None
    if category != "سایر":
        # اینجا باید سیستم بودجه رو فراخوانی کنی
        pass
    
    # پاسخ به کاربر
    response = (
        f"✅ هزینه ثبت شد:\n"
        f"💰 مبلغ: {amount:,} تومان\n"
        f"📝 توضیح: {description}\n"
        f"🏷️ دسته: {category}\n"
        f"🕐 زمان: {datetime.now().strftime('%H:%M')}"
    )
    
    if budget_warning:
        response += f"\n\n{budget_warning}"
    
    await update.message.reply_text(
        response,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 گزارش امروز", callback_data="menu_today"),
            InlineKeyboardButton("➕ هزینه جدید", callback_data="menu_add_expense")
        ]])
    )

async def save_expense_with_description(update: Update, context: ContextTypes.DEFAULT_TYPE, description: str) -> None:
    """ذخیره هزینه با توضیحات وارد شده"""
    user_id = str(update.effective_user.id)
    amount = context.user_data.get("expense_amount", 0)
    category = context.user_data.get("selected_category", "سایر")
    
    if amount <= 0:
        await update.message.reply_text("❌ مبلغ نامعتبر!")
        return
    
    # ذخیره هزینه
    expenses = load_data(EXPENSES_FILE, [])
    expense_data = {
        "user_id": user_id,
        "amount": amount,
        "description": description if description else "بدون توضیح",
        "category": category,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "timestamp": datetime.now().isoformat()
    }
    expenses.append(expense_data)
    save_data(EXPENSES_FILE, expenses)
    
    # پاک کردن داده‌های موقت
    context.user_data.pop("expense_amount", None)
    context.user_data.pop("selected_category", None)
    context.user_data.pop("awaiting_description", None)
    
    # پاسخ
    await update.message.reply_text(
        f"✅ هزینه با موفقیت ثبت شد!\n\n"
        f"💰 مبلغ: {amount:,} تومان\n"
        f"🏷️ دسته: {category}\n"
        f"📝 توضیح: {description if description else 'بدون توضیح'}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 گزارش امروز", callback_data="menu_today"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_main")
        ]])
    )

# ========== 🛠️ توابع کمکی ==========
def parse_amount(amount_str):
    """تبدیل مبلغ به عدد"""
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

# ========== 🚀 اجرای اصلی ==========
def main() -> None:
    """Start the bot."""
    # ساخت اپلیکیشن
    app = Application.builder().token(TOKEN).build()
    
    # اضافه کردن هندلرهای گفتگو
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AWAITING_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message),
                CallbackQueryHandler(button_handler)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    app.add_handler(conv_handler)
    
    # هندلرهای دکمه‌ها
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # هندلر پیام‌های متنی
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # هندلرهای دستوری قدیمی (برای سازگاری)
    app.add_handler(CommandHandler("today", lambda u,c: button_handler(u, c, "menu_today")))
    app.add_handler(CommandHandler("month", lambda u,c: button_handler(u, c, "menu_month")))
    app.add_handler(CommandHandler("add", show_add_expense_menu))
    app.add_handler(CommandHandler("budget", show_budget_menu))
    app.add_handler(CommandHandler("stats", show_stats_menu))
    app.add_handler(CommandHandler("help", show_help_menu))
    app.add_handler(CommandHandler("settings", show_settings_menu))
    
    print("🤖 ربات مدیریت هزینه‌ها با منوی اینتراکتیو راه‌اندازی شد...")
    print("🎯 منتظر کاربران هستیم...")
    
    # اجرای ربات
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()