from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import json
from datetime import datetime, timedelta
import os
import re
import hashlib
import secrets
from typing import Dict, List, Optional
import csv
import io
import asyncio
from collections import defaultdict

# 🔐 توکن ربات را اینجا قرار بده
TOKEN = "8531861676:AAGefz_InVL9y4FtKYcETGAFTRHggaJCnhA"

# 📁 فایل‌های دیتابیس
EXPENSES_FILE = "expenses.json"
USERS_FILE = "users.json"
BUDGETS_FILE = "budgets.json"
BACKUP_DIR = "backups/"

# ایجاد پوشه بک‌آپ
os.makedirs(BACKUP_DIR, exist_ok=True)

# لود کردن داده‌ها
def load_data(filename, default=None):
    if default is None:
        default = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

# ذخیره داده‌ها
def save_data(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    # ایجاد بک‌آپ خودکار
    backup_file = f"{BACKUP_DIR}{filename}.backup.{datetime.now().strftime('%Y%m%d')}"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ========== 🔐 سیستم امنیتی ==========
class SecuritySystem:
    def __init__(self):
        self.users = load_data(USERS_FILE, {})
        self.rate_limits = {}
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
            "last_login": None
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
    
    def check_rate_limit(self, user_id: str) -> bool:
        now = datetime.now()
        user_id = str(user_id)
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = []
        
        # حذف درخواست‌های قدیمی (یک دقیقه گذشته)
        self.rate_limits[user_id] = [t for t in self.rate_limits[user_id] 
                                   if (now - t).seconds < 60]
        
        # محدودیت: 30 درخواست در دقیقه
        if len(self.rate_limits[user_id]) >= 30:
            return False
        
        self.rate_limits[user_id].append(now)
        return True

security = SecuritySystem()

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
            "reset_date": self._get_next_reset_date(period)
        }
        save_data(BUDGETS_FILE, self.budgets)
    
    def add_expense_to_budget(self, user_id: str, category: str, amount: int) -> None:
        user_id = str(user_id)
        if user_id in self.budgets and category in self.budgets[user_id]:
            budget = self.budgets[user_id][category]
            
            # چک کردن ریست دوره
            if datetime.now() > datetime.fromisoformat(budget["reset_date"]):
                budget["spent"] = 0
                budget["reset_date"] = self._get_next_reset_date(budget["period"])
            
            budget["spent"] += amount
            save_data(BUDGETS_FILE, self.budgets)
            
            # هشدار اگر از 80% بودجه گذشت
            if budget["spent"] / budget["amount"] > 0.8:
                return f"⚠️ هشدار: بودجه {category} به {budget['spent']*100/budget['amount']:.1f}% رسیده!"
        return None
    
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
                "status": "🟢" if percentage < 80 else "🟡" if percentage < 100 else "🔴"
            }
        return status

budget_system = BudgetSystem()

# ========== 🏷️ دسته‌بندی هوشمند ==========
class SmartCategory:
    def __init__(self):
        self.keywords = {
            "غذا": ["ناهار", "شام", "صبحانه", "رستوران", "فست فود", "ساندویچ", "پیتزا"],
            "حمل نقل": ["تاکسی", "اسنپ", "تپسی", "مترو", "اتوبوس", "بنزین", "پارکینگ"],
            "خرید": ["سوپرمارکت", "بازار", "هایپرمارکت", "فروشگاه", "آبمیوه", "نانوایی"],
            "کافه": ["قهوه", "کافه", "کافی شاپ", "نسکافه", "اسپرسو"],
            "سلامت": ["داروخانه", "پزشک", "درمان", "بیمارستان", "دارو", "ویتامین"],
            "تفریح": ["سینما", "تئاتر", "پارک", "باشگاه", "استخر", "بازی"],
            "آموزش": ["کتاب", "کلاس", "دانشگاه", "مدرسه", "کارگاه", "سمینار"],
            "قبوض": ["برق", "آب", "گاز", "تلفن", "موبایل", "اینترنت"],
            "پوشاک": ["لباس", "کفش", "کیف", "کمربند", "عینک", "ساعت"]
        }
        
        # یادگیری رفتار کاربر
        self.user_preferences = load_data("user_preferences.json", {})
    
    def detect_category(self, description: str, user_id: str = None) -> str:
        desc_lower = description.lower()
        
        # اول چک کردن تنظیمات کاربر
        if user_id and str(user_id) in self.user_preferences:
            for user_cat, user_keywords in self.user_preferences[str(user_id)].items():
                if any(keyword in desc_lower for keyword in user_keywords):
                    return user_cat
        
        # سپس چک کردن کلمات کلیدی عمومی
        for category, keywords in self.keywords.items():
            if any(keyword in desc_lower for keyword in keywords):
                return category
        
        # یادگیری: اگر کاربر تایید کرد، اضافه کردن به تنظیمات
        return "سایر"
    
    def learn_from_user(self, user_id: str, description: str, category: str) -> None:
        user_id = str(user_id)
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        if category not in self.user_preferences[user_id]:
            self.user_preferences[user_id][category] = []
        
        # استخراج کلمات کلیدی از توضیحات
        words = description.split()
        for word in words:
            if len(word) > 2 and word not in self.user_preferences[user_id][category]:
                self.user_preferences[user_id][category].append(word.lower())
        
        save_data("user_preferences.json", self.user_preferences)

smart_category = SmartCategory()

# ========== 📊 گزارش‌گیری گرافیکی ==========
class ChartGenerator:
    @staticmethod
    def generate_monthly_chart_text(expenses: List) -> str:
        # گروه‌بندی بر اساس روز
        daily_totals = defaultdict(int)
        for exp in expenses:
            daily_totals[exp["date"]] += exp["amount"]
        
        # ایجاد نمودار متنی
        chart = "📊 نمودار هزینه‌های ماه:\n\n"
        
        # پیدا کردن بیشترین مقدار برای نرمال‌سازی
        if daily_totals:
            max_amount = max(daily_totals.values())
            for date, amount in sorted(daily_totals.items()):
                bar_length = int((amount / max_amount) * 20) if max_amount > 0 else 0
                chart += f"{date}: {'█' * bar_length}{'░' * (20 - bar_length)} {amount:,} تومان\n"
        
        return chart
    
    @staticmethod
    def generate_category_chart_text(category_totals: Dict) -> str:
        chart = "🎯 توزیع هزینه بر اساس دسته:\n\n"
        
        if category_totals:
            total = sum(category_totals.values())
            for category, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total) * 100
                bar_length = int(percentage / 5)  # هر 5% یک بلوک
                chart += f"{category}: {'█' * bar_length} {percentage:.1f}% ({amount:,})\n"
        
        return chart

chart_gen = ChartGenerator()

# ========== 👥 سیستم چندکاربره ==========
class FamilySystem:
    def __init__(self):
        self.families = load_data("families.json", {})
    
    def create_family(self, admin_id: str, family_name: str) -> str:
        family_id = secrets.token_hex(8)
        self.families[family_id] = {
            "name": family_name,
            "admin": str(admin_id),
            "members": [str(admin_id)],
            "shared_categories": ["غذا", "قبوض", "خرید"],
            "created": datetime.now().isoformat()
        }
        save_data("families.json", self.families)
        return family_id
    
    def add_member(self, family_id: str, user_id: str, admin_id: str) -> bool:
        if family_id in self.families and self.families[family_id]["admin"] == str(admin_id):
            if str(user_id) not in self.families[family_id]["members"]:
                self.families[family_id]["members"].append(str(user_id))
                save_data("families.json", self.families)
                return True
        return False
    
    def get_family_expenses(self, family_id: str) -> List:
        if family_id not in self.families:
            return []
        
        members = self.families[family_id]["members"]
        all_expenses = load_data(EXPENSES_FILE, [])
        
        # فیلتر کردن هزینه‌های اعضای خانواده
        family_expenses = [e for e in all_expenses if e["user_id"] in members]
        
        # فقط دسته‌های مشترک
        shared_cats = self.families[family_id]["shared_categories"]
        return [e for e in family_expenses if smart_category.detect_category(e["description"]) in shared_cats]

family_system = FamilySystem()

# ========== 📱 دستورات اصلی ==========

# /start با احراز هویت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # چک کردن ثبت نام
    if user_id not in security.users:
        await update.message.reply_text(
            "👋 به ربات مدیریت هزینه خوش آمدید!\n\n"
            "لطفاً برای اولین بار یک رمز عبور انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("ثبت نام", callback_data="register")
            ]])
        )
        return
    
    # درخواست رمز عبور
    await update.message.reply_text(
        "🔐 لطفاً رمز عبور خود را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("ورود", callback_data="login")
        ]])
    )

# ثبت هزینه
async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # چک کردن Rate Limit
    if not security.check_rate_limit(user_id):
        await update.message.reply_text("⏰ تعداد درخواست‌های شما زیاد است. لطفاً کمی صبر کنید.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n"
            "`/add 50000 ناهار`\n"
            "`/add 50هزار ناهار رستوران`"
        )
        return
    
    # پارس کردن مبلغ
    amount = parse_amount(context.args[0])
    if not amount:
        await update.message.reply_text("❌ مبلغ نامعتبر!")
        return
    
    description = " ".join(context.args[1:]) if len(context.args) > 1 else "بدون توضیح"
    
    # تشخیص خودکار دسته
    category = smart_category.detect_category(description, user_id)
    
    # ذخیره هزینه
    expenses = load_data(EXPENSES_FILE, [])
    expense_data = {
        "user_id": user_id,
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
    budget_warning = budget_system.add_expense_to_budget(user_id, category, amount)
    
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
    
    await update.message.reply_text(response)

# /budget - مدیریت بودجه
async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not context.args:
        # نمایش وضعیت بودجه‌ها
        status = budget_system.get_budget_status(user_id)
        if not status:
            await update.message.reply_text(
                "📊 هنوز بودجه‌ای تنظیم نکرده‌اید.\n\n"
                "برای تنظیم بودجه:\n"
                "`/budget غذا 1000000`\n"
                "`/budget حمل_نقل 500000 ماهانه`"
            )
            return
        
        response = "📊 وضعیت بودجه‌های شما:\n\n"
        for category, data in status.items():
            response += (
                f"{data['status']} **{category}**\n"
                f"بودجه: {data['budget']:,} تومان\n"
                f"خرج شده: {data['spent']:,} تومان\n"
                f"مانده: {data['remaining']:,} تومان\n"
                f"پرشدگی: {data['percentage']:.1f}%\n\n"
            )
        
        await update.message.reply_text(response, parse_mode="Markdown")
        return
    
    # تنظیم بودجه جدید
    if len(context.args) < 2:
        await update.message.reply_text("❌ فرمت صحیح: `/budget [دسته] [مبلغ] [دوره]`")
        return
    
    category = context.args[0]
    amount = parse_amount(context.args[1])
    
    if not amount:
        await update.message.reply_text("❌ مبلغ نامعتبر!")
        return
    
    period = context.args[2] if len(context.args) > 2 else "monthly"
    if period not in ["daily", "weekly", "monthly"]:
        period = "monthly"
    
    budget_system.set_budget(user_id, category, amount, period)
    
    await update.message.reply_text(
        f"✅ بودجه {category} تنظیم شد:\n"
        f"💰 مبلغ: {amount:,} تومان\n"
        f"📅 دوره: {'روزانه' if period == 'daily' else 'هفتگی' if period == 'weekly' else 'ماهانه'}"
    )

# /income - ثبت درآمد
async def income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text(
            "💰 ثبت درآمد:\n"
            "`/income 5000000 حقوق`\n"
            "`/income 1000000 فروش کتاب`"
        )
        return
    
    amount = parse_amount(context.args[0])
    if not amount:
        await update.message.reply_text("❌ مبلغ نامعتبر!")
        return
    
    source = " ".join(context.args[1:]) if len(context.args) > 1 else "بدون توضیح"
    
    # ذخیره درآمد
    incomes = load_data("incomes.json", [])
    incomes.append({
        "user_id": user_id,
        "amount": amount,
        "source": source,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat()
    })
    save_data("incomes.json", incomes)
    
    await update.message.reply_text(
        f"✅ درآمد ثبت شد:\n"
        f"💰 مبلغ: {amount:,} تومان\n"
        f"📝 منبع: {source}\n"
        f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d')}"
    )

# /stats - آمار پیشرفته
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # بارگذاری داده‌ها
    expenses = [e for e in load_data(EXPENSES_FILE, []) if e["user_id"] == user_id]
    incomes = [i for i in load_data("incomes.json", []) if i["user_id"] == user_id]
    
    if not expenses:
        await update.message.reply_text("📊 هنوز داده‌ای برای تحلیل وجود ندارد.")
        return
    
    # محاسبات آماری
    total_expenses = sum(e["amount"] for e in expenses)
    total_incomes = sum(i["amount"] for i in incomes)
    balance = total_incomes - total_expenses
    
    # دسته‌بندی هزینه‌ها
    categories = defaultdict(int)
    for e in expenses:
        category = e.get("category", "سایر")
        categories[category] += e["amount"]
    
    # بیشترین و کمترین هزینه
    max_exp = max(expenses, key=lambda x: x["amount"])
    min_exp = min(expenses, key=lambda x: x["amount"])
    
    # میانگین روزانه
    dates = set(e["date"] for e in expenses)
    avg_daily = total_expenses / len(dates) if dates else 0
    
    # ایجاد گزارش
    report = "📈 **آمار مالی پیشرفته**\n\n"
    
    report += "💰 **تراز مالی:**\n"
    report += f"• کل درآمد: {total_incomes:,} تومان\n"
    report += f"• کل هزینه: {total_expenses:,} تومان\n"
    report += f"• مانده: {balance:,} تومان\n"
    report += f"• نسبت پس‌انداز: {(balance/total_incomes*100 if total_incomes>0 else 0):.1f}%\n\n"
    
    report += "📊 **آمار هزینه‌ها:**\n"
    report += f"• تعداد تراکنش: {len(expenses)}\n"
    report += f"• میانگین هر خرید: {total_expenses/len(expenses):,.0f}\n"
    report += f"• میانگین روزانه: {avg_daily:,.0f}\n\n"
    
    report += "🏆 **رکوردها:**\n"
    report += f"• بیشترین خرید: {max_exp['amount']:,} تومان ({max_exp['description']})\n"
    report += f"• کمترین خرید: {min_exp['amount']:,} تومان ({min_exp['description']})\n\n"
    
    report += chart_gen.generate_category_chart_text(categories)
    
    await update.message.reply_text(report, parse_mode="Markdown")

# /export - خروجی گرفتن
async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # جمع‌آوری داده‌ها
    expenses = [e for e in load_data(EXPENSES_FILE, []) if e["user_id"] == user_id]
    incomes = [i for i in load_data("incomes.json", []) if i["user_id"] == user_id]
    
    if not expenses and not incomes:
        await update.message.reply_text("📭 هیچ داده‌ای برای خروجی گرفتن وجود ندارد.")
        return
    
    # ایجاد CSV
    csv_output = io.StringIO()
    csv_writer = csv.writer(csv_output)
    
    # هدر فایل
    csv_writer.writerow(["نوع", "مبلغ", "توضیح", "دسته", "تاریخ", "زمان"])
    
    # هزینه‌ها
    for exp in expenses:
        csv_writer.writerow([
            "هزینه",
            exp["amount"],
            exp["description"],
            exp.get("category", "سایر"),
            exp["date"],
            exp["time"]
        ])
    
    # درآمدها
    for inc in incomes:
        csv_writer.writerow([
            "درآمد",
            inc["amount"],
            inc["source"],
            "درآمد",
            inc["date"],
            "00:00"
        ])
    
    # ارسال فایل
    csv_data = csv_output.getvalue()
    csv_file = io.BytesIO(csv_data.encode('utf-8-sig'))
    csv_file.name = f"financial_report_{datetime.now().strftime('%Y%m%d')}.csv"
    
    await update.message.reply_document(
        document=csv_file,
        caption="📁 خروجی داده‌های مالی شما\n\n"
               "می‌توانید این فایل را در Excel باز کنید."
    )

# /family - سیستم خانوادگی
async def family(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not context.args:
        # نمایش منوی خانوادگی
        keyboard = [
            [InlineKeyboardButton("🏠 ایجاد خانواده جدید", callback_data="family_create")],
            [InlineKeyboardButton("👥 افزودن عضو", callback_data="family_add")],
            [InlineKeyboardButton("📊 گزارش خانوادگی", callback_data="family_report")],
            [InlineKeyboardButton("⚙️ تنظیمات خانواده", callback_data="family_settings")]
        ]
        
        await update.message.reply_text(
            "👨‍👩‍👧‍👦 **مدیریت خانواده**\n\n"
            "با خانواده خود هزینه‌ها را مدیریت کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return
    
    # سایر دستورات خانوادگی
    # (پیاده‌سازی کامل نیاز به کد بیشتری دارد)

# هشداردهنده خودکار
async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    for user_id in security.users:
        # محاسبه هزینه‌های امروز
        expenses = [e for e in load_data(EXPENSES_FILE, []) 
                   if e["user_id"] == user_id and e["date"] == datetime.now().strftime("%Y-%m-%d")]
        
        if expenses:
            total_today = sum(e["amount"] for e in expenses)
            
            # بررسی بودجه
            budget_status = budget_system.get_budget_status(user_id)
            warnings = []
            for category, data in budget_status.items():
                if data["percentage"] > 90:
                    warnings.append(f"⚠️ بودجه {category} تقریباً تمام شده ({data['percentage']:.1f}%)")
            
            report = (
                f"📊 گزارش روزانه {datetime.now().strftime('%Y-%m-%d')}\n\n"
                f"💰 هزینه امروز: {total_today:,} تومان\n"
                f"📝 تعداد خرید: {len(expenses)}\n"
            )
            
            if warnings:
                report += "\n" + "\n".join(warnings)
            
            try:
                await context.bot.send_message(chat_id=int(user_id), text=report)
            except:
                pass

# ========== 🎯 دستورات جدید ==========

# /reminder - تنظیم یادآور
async def reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 قبوض ماهانه", callback_data="reminder_bills")],
        [InlineKeyboardButton("💰 ثبت هزینه روزانه", callback_data="reminder_daily")],
        [InlineKeyboardButton("📊 گزارش هفتگی", callback_data="reminder_weekly")],
        [InlineKeyboardButton("⏰ زمان‌بندی سفارشی", callback_data="reminder_custom")]
    ]
    
    await update.message.reply_text(
        "⏰ **سیستم یادآور**\n\n"
        "یادآورهای خود را تنظیم کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# /goal - اهداف مالی
async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not context.args:
        goals = load_data("goals.json", {}).get(user_id, [])
        
        if not goals:
            await update.message.reply_text(
                "🎯 **اهداف مالی**\n\n"
                "هنوز هدفی تنظیم نکرده‌اید.\n\n"
                "برای تنظیم هدف:\n"
                "`/goal پس‌انداز 5000000 1403/01/30`\n"
                "`/goal خرید لپ‌تاپ 15000000`"
            )
            return
        
        response = "🎯 **اهداف مالی شما:**\n\n"
        for i, goal in enumerate(goals, 1):
            progress = (goal.get("saved", 0) / goal["target"]) * 100
            response += (
                f"{i}. **{goal['name']}**\n"
                f"   هدف: {goal['target']:,} تومان\n"
                f"   پس‌انداز شده: {goal.get('saved', 0):,} تومان\n"
                f"   پیشرفت: {progress:.1f}%\n"
                f"   مهلت: {goal.get('deadline', 'ندارد')}\n\n"
            )
        
        await update.message.reply_text(response, parse_mode="Markdown")
        return
    
    # تنظیم هدف جدید
    if len(context.args) < 2:
        await update.message.reply_text("❌ فرمت صحیح: `/goal [نام] [مبلغ] [تاریخ]`")
        return
    
    goal_name = context.args[0]
    target = parse_amount(context.args[1])
    
    if not target:
        await update.message.reply_text("❌ مبلغ نامعتبر!")
        return
    
    deadline = context.args[2] if len(context.args) > 2 else None
    
    # ذخیره هدف
    goals_data = load_data("goals.json", {})
    if user_id not in goals_data:
        goals_data[user_id] = []
    
    goals_data[user_id].append({
        "name": goal_name,
        "target": target,
        "saved": 0,
        "deadline": deadline,
        "created": datetime.now().isoformat()
    })
    
    save_data("goals.json", goals_data)
    
    await update.message.reply_text(
        f"✅ هدف جدید ثبت شد:\n"
        f"🎯 نام: {goal_name}\n"
        f"💰 مبلغ هدف: {target:,} تومان\n"
        f"📅 مهلت: {deadline if deadline else 'ندارد'}"
    )

# /compare - مقایسه دوره‌ها
async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = [e for e in load_data(EXPENSES_FILE, []) if e["user_id"] == user_id]
    
    if not expenses:
        await update.message.reply_text("📊 داده‌ای برای مقایسه وجود ندارد.")
        return
    
    # گروه‌بندی بر اساس ماه
    monthly_totals = defaultdict(int)
    for exp in expenses:
        year_month = exp["date"][:7]  # YYYY-MM
        monthly_totals[year_month] += exp["amount"]
    
    # مرتب سازی و انتخاب ۶ ماه اخیر
    sorted_months = sorted(monthly_totals.keys(), reverse=True)[:6]
    
    response = "📈 **مقایسه ماه‌های اخیر**\n\n"
    
    if len(sorted_months) >= 2:
        current = monthly_totals[sorted_months[0]]
        previous = monthly_totals[sorted_months[1]]
        change = ((current - previous) / previous * 100) if previous > 0 else 0
        
        response += f"📊 تغییرات نسبت به ماه قبل:\n"
        response += f"• این ماه: {current:,} تومان\n"
        response += f"• ماه قبل: {previous:,} تومان\n"
        response += f"• تغییر: {change:+.1f}%\n\n"
    
    response += "📅 جزئیات ۶ ماه اخیر:\n"
    for month in sorted_months:
        response += f"• {month}: {monthly_totals[month]:,} تومان\n"
    
    await update.message.reply_text(response)

# ========== 🔄 هندلرهای اینلاین ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "register":
        await query.edit_message_text(
            "📝 **ثبت نام**\n\n"
            "لطفاً رمز عبور دلخواه خود را وارد کنید:"
        )
        context.user_data["awaiting_password"] = True
    
    elif data == "login":
        await query.edit_message_text(
            "🔐 **ورود**\n\n"
            "لطفاً رمز عبور خود را وارد کنید:"
        )
        context.user_data["awaiting_password_login"] = True

# ========== 🎯 تابع اصلی ==========
def main():
    app = Application.builder().token(TOKEN).build()
    
    # اضافه کردن هندلرهای اصلی
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_expense))
    app.add_handler(CommandHandler("budget", budget))
    app.add_handler(CommandHandler("income", income))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("export", export_data))
    app.add_handler(CommandHandler("family", family))
    app.add_handler(CommandHandler("reminder", reminder))
    app.add_handler(CommandHandler("goal", goal))
    app.add_handler(CommandHandler("compare", compare))
    
    # هندلرهای قدیمی (حفظ سازگاری)
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("month", month))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("week", week))
    
    # هندلرهای اینلاین
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # هندلر پیام‌های متنی
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_add))
    
    # تنظیم Job Queue برای هشدارهای خودکار
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(send_daily_report, time=datetime.time(hour=21, minute=0))
    
    print("🤖 ربات مدیریت هزینه‌های پیشرفته اجرا شد...")
    print("🔐 سیستم امنیتی فعال")
    print("💰 سیستم بودجه‌بندی فعال")
    print("🏷️ دسته‌بندی هوشمند فعال")
    print("📊 گزارش‌گیری گرافیکی فعال")
    print("👥 سیستم خانوادگی فعال")
    
    app.run_polling()

# ========== 🎯 توابع کمکی ==========
def parse_amount(amount_str):
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

async def quick_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی رمز عبور
    user_id = str(update.effective_user.id)
    
    if context.user_data.get("awaiting_password"):
        password = update.message.text.strip()
        if len(password) < 4:
            await update.message.reply_text("❌ رمز عبور باید حداقل ۴ کاراکتر باشد.")
            return
        
        if security.register_user(user_id, password):
            await update.message.reply_text(
                "✅ ثبت نام با موفقیت انجام شد!\n\n"
                "از حالا می‌توانید از ربات استفاده کنید.\n\n"
                "دستورات:\n"
                "/add - ثبت هزینه\n"
                "/budget - مدیریت بودجه\n"
                "/income - ثبت درآمد\n"
                "/stats - آمار پیشرفته"
            )
            context.user_data.pop("awaiting_password", None)
        return
    
    if context.user_data.get("awaiting_password_login"):
        password = update.message.text.strip()
        if security.authenticate(user_id, password):
            await update.message.reply_text("✅ ورود موفقیت‌آمیز بود!")
            context.user_data.pop("awaiting_password_login", None)
        else:
            await update.message.reply_text("❌ رمز عبور اشتباه است.")
        return
    
    # ثبت سریع هزینه
    text = update.message.text.strip()
    numbers = re.findall(r'[\d,]+', text)
    
    if not numbers:
        return
    
    amount = parse_amount(numbers[0])
    if not amount:
        return
    
    description = re.sub(r'[\d,]+', '', text).strip() or "بدون توضیح"
    
    # استفاده از تابع add_expense
    context.args = [numbers[0], description]
    await add_expense(update, context)

# ========== 🎯 توابع قدیمی (برای سازگاری) ==========
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = [e for e in load_data(EXPENSES_FILE, []) if e["user_id"] == user_id]
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

async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = [e for e in load_data(EXPENSES_FILE, []) if e["user_id"] == user_id]
    month_key = datetime.now().strftime("%Y-%m")
    
    month_list = [e for e in expenses if e["date"].startswith(month_key)]
    
    if not month_list:
        await update.message.reply_text(f"هیچ هزینه‌ای برای ماه {month_key} ثبت نشده 📅")
        return
    
    categories = {}
    for e in month_list:
        category = e.get("category", smart_category.detect_category(e["description"]))
        if category not in categories:
            categories[category] = 0
        categories[category] += e["amount"]
    
    total = sum(e["amount"] for e in month_list)
    avg = total / len(month_list)
    
    text = f"📊 *هزینه‌های ماه {month_key}*\n\n"
    
    for e in month_list[-15:]:
        text += f"• {e['amount']:,} تومان - {e['description']} ({e['date']})\n"
    
    text += f"\n💰 *جمع ماه: {total:,} تومان*\n"
    text += f"📈 میانگین هر خرید: {avg:,.0f} تومان\n"
    text += f"📝 تعداد خریدها: {len(month_list)}\n"
    
    text += chart_gen.generate_category_chart_text(categories)
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = [e for e in load_data(EXPENSES_FILE, []) if e["user_id"] == user_id]
    
    if not expenses:
        await update.message.reply_text("هنوز هیچ هزینه‌ای ثبت نکردی! 💰")
        return
    
    total = sum(e["amount"] for e in expenses)
    avg = total / len(expenses)
    
    dates = [datetime.strptime(e["date"], "%Y-%m-%d") for e in expenses]
    oldest = min(dates).strftime("%Y-%m-%d")
    newest = max(dates).strftime("%Y-%m-%d")
    
    text = "💰 *گزارش کلی هزینه‌ها*\n\n"
    text += f"📅 از {oldest} تا {newest}\n"
    text += f"📝 تعداد کل: {len(expenses)}\n"
    text += f"💰 مجموع کل: {total:,} تومان\n"
    text += f"📊 میانگین هر خرید: {avg:,.0f} تومان\n"
    
    if len(expenses) > 0:
        max_exp = max(expenses, key=lambda x: x["amount"])
        min_exp = min(expenses, key=lambda x: x["amount"])
        
        text += f"\n🏆 *رکوردها:*\n"
        text += f"• بیشترین: {max_exp['amount']:,} تومان ({max_exp['description']})\n"
        text += f"• کمترین: {min_exp['amount']:,} تومان ({min_exp['description']})"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = load_data(EXPENSES_FILE, [])
    
    remaining = [e for e in expenses if e.get("user_id") != user_id]
    deleted_count = len(expenses) - len(remaining)
    
    save_data(EXPENSES_FILE, remaining)
    
    await update.message.reply_text(f"✅ {deleted_count} هزینه پاک شد!")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً کلمه جستجو رو وارد کن:\n`/search قهوه`", parse_mode="Markdown")
        return
    
    user_id = str(update.effective_user.id)
    expenses = [e for e in load_data(EXPENSES_FILE, []) if e["user_id"] == user_id]
    
    keyword = " ".join(context.args).lower()
    results = [e for e in expenses if keyword in e["description"].lower()]
    
    if not results:
        await update.message.reply_text(f"نتیجه‌ای برای '{keyword}' پیدا نشد 🔍")
        return
    
    total = sum(e["amount"] for e in results)
    
    text = f"🔍 *نتایج جستجو برای '{keyword}'*\n\n"
    
    for i, e in enumerate(results[-10:], 1):
        text += f"{i}. {e['amount']:,} تومان - {e['description']} ({e['date']})\n"
    
    text += f"\n💰 مجموع: {total:,} تومان\n"
    text += f"📝 تعداد: {len(results)} مورد"
    
    if len(results) > 10:
        text += f"\n\n📌 فقط ۱۰ مورد آخر نمایش داده شد"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    expenses = [e for e in load_data(EXPENSES_FILE, []) if e["user_id"] == user_id]
    
    week_ago = datetime.now() - timedelta(days=7)
    week_list = []
    
    for e in expenses:
        exp_date = datetime.strptime(e["date"], "%Y-%m-%d")
        if exp_date >= week_ago:
            week_list.append(e)
    
    if not week_list:
        await update.message.reply_text("هفته گذشته هیچ هزینه‌ای ثبت نکردی! 💰")
        return
    
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

if __name__ == "__main__":
    main()